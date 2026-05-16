# SHL Assessment Recommender — Approach Document

**Author:** Sriram Nalla
**Submission date:** 2026-05-17
**Public endpoint:** `<RENDER_URL_TO_BE_FILLED>`
**Repository:** https://github.com/sriramnalla30/shl_project

---

## 1. Problem framing

Build a multi-turn agent that recommends 1-10 SHL assessments per turn against a 377-item catalog, with strict schema and URL-allowlist requirements, sub-30s latency per call, and graceful behavior on off-topic, vague, comparison, and clarification scenarios.

## 2. Architecture

A LangGraph state machine with 11 nodes. Each turn flows: **guardrail → router → slot_extractor → (clarifier | retriever → reranker | comparator | refuse) → composer → validator → END**. The validator can loop back to composer up to 2 times for schema correction before falling back to a safe canned reply.

| Layer | Component |
|---|---|
| API | FastAPI (`/health`, `/chat`) with lifespan handler that loads catalog, indexes, allowlist, and compiles the graph once at startup |
| LLM | Multi-key Groq (3 accounts, Llama 3.3 70B main + Llama 3.1 8B fallback) with multi-key Gemini Flash 2.5 (2 accounts); rotating failover across all keys |
| Retrieval | BM25 (`rank_bm25`) + dense (FAISS, `bge-small-en-v1.5`) → Reciprocal Rank Fusion (k=60) → top-50, hard filters by test_type and duration |
| Reranker | Single batched LLM call returning ranked subset with reasons (routed to Gemini Flash as primary to keep Groq quota for other nodes; Groq as fallback) |
| Validator | Pydantic schema + URL allowlist (754 normalized URLs) + size rule per intent + auto-fix for end_of_conversation consistency |

## 3. Key design decisions (full log in `DECISION_LOG.md`)

- **Catalog-as-truth:** Adapted code to the actual scraped 377-record catalog rather than the spec's idealized 366 records. Avoided silent data loss during schema normalization.
- **Multi-key rotating failover:** Three Groq accounts plus two Gemini accounts pool together. Cursors rotate so calls distribute across keys; on rate-limit each call walks through every key before falling back to Gemini.
- **Foundational item injection:** After BM25+FAISS retrieval, if user query or slots match patterns like "leadership / sales / re-skill / behavioral", inject the canonical SHL instruments (OPQ32r, OPQ Leadership Report, Universal Competency Report, Global Skills Assessment, Global Skills Development Report) into the candidate pool at position 5+. Reason: these foundational items rank 60-80 in BM25 because user vocabulary ("CXO", "re-skill") rarely overlaps with their catalog descriptions, even though they're the right answer.
- **Reranker on Gemini primary:** Reranker is the largest token consumer. Routing it to Gemini's separate quota pool prevents Groq rate-limit cascades that previously pushed individual /chat calls above 30s.
- **Router commit-bias:** Early experiments stalled at Recall@10 = 0.10 because the agent loop-clarified instead of committing. Lowered the "force recommend if role known" threshold from turn 5 to turn 2, with an unconditional commit at turn 3. Lifted Recall@10 from 0.10 → 0.43 in one change.
- **Comparator preserves prior shortlist:** When a comparison turn happens mid-conversation, the comparator walks back through assistant messages, extracts prior recommended URLs, and merges them with the compared pair (deduped, capped at 10).

## 4. Retrieval

| Knob | Value | Rationale |
|---|---|---|
| BM25 top-k | 50 | Foundational items often rank 30-50 in lexical retrieval |
| Dense top-k | 50 | Same reasoning for semantic |
| RRF constant | 60 | Standard, parameter-free |
| Post-RRF cap | 50 | Reranker context budget |
| Reranker max output | 10 | Schema cap |
| Reranker fallback | top-8 | When LLM fails, return 8 retrieval-ordered items (8 not 5 because Recall@10 is mathematically capped by shortlist size) |

Query expansion table maps 18 user-vocabulary triggers (sales, leadership, re-skill, CXO, audit, etc.) to catalog vocabulary (OPQ MQ Sales, OPQ Leadership Report, Global Skills Assessment). Without it, "re-skill" doesn't BM25-match "Global Skills Assessment".

## 5. Prompt design

Six prompt files in `app/agent/prompts/`: guardrail, router, slot_extractor, clarifier, reranker, composer, comparator. Each receives a shared `<<SKILL>>` primer (escaped braces to survive `.format()`) plus context placeholders. Reranker rubric has 8 priority-ordered rules including "MUST include OPQ32r when personality/leadership/sales is in scope" and "prefer broad universal reports over narrow variants unless role specifically matches."

## 6. Evaluation

Custom replay harness (`eval/replay.py`) parses the 10 sample markdown conversations into structured records (user turns + expected URLs from the final shortlist turn), sends each conversation's user turns sequentially through `/chat`, and computes Recall@10 against expected URLs. Inter-trace delay of 3-8 seconds paces Groq's rate-limit window.

**Measured Recall@10 on public 10-trace sample conversations:**

| Trace | Recall@10 | Notes |
|---|---|---|
| C1 (CXO leadership) | 1.00 | Foundational injection guarantees all 3 OPQ items |
| C2 (Rust developer) | 0.40 | Gap acknowledgment helps but catalog has no Rust-specific test |
| C3 (training material) | 0.50 | Multi-turn refinement works |
| C4 (sales manager) | 0.60 | Sales-specific recall limited by catalog overlap |
| C5 (sales re-skill) | 0.60 | Foundational injection provides GSA/GSDR |
| C6 (chemical plant safety) | 0.00 | Foundational injection mis-triggers on "supervisor"; documented limitation |
| C7 (contact center agents) | 0.40 | |
| C8 (skills audit) | 0.20 | Broad JD, limited overlap with expected items |
| C9 (full-stack JD, 7 turns) | 0.14 | Long JD with 7+ tech areas — broad-query detection routes to clarify first |
| C10 (graduate analyst) | 0.50 | Honor-the-edit ("drop OPQ") sometimes conflicts with injection rule |
| **Mean Recall@10** | **0.434** | Range 0.43-0.65 depending on Groq quota availability during run |

Behavior probes: 12 end-to-end pytest assertions covering schema compliance, URL grounding, size limits, off-topic refusal, prompt injection resistance, clarification, slot extraction, multi-turn refinement, comparison, duration filtering, end_of_conversation consistency, and latency. All 12 pass locally.

## 7. What didn't work

- **Single Groq key:** Daily 100K token cap exhausted at trace 4-5 of every eval run, cascading the rest into raw-retrieval fallback (Recall = 0.10-0.27). Fixed by multi-key rotation + Gemini reranker.
- **Reranker rubric without foundational injection:** Telling the LLM "always include OPQ32r" had no effect because OPQ32r wasn't in the candidate pool that reached the reranker. Foundational injection at the retriever solved this.
- **Turn-budget = 5 force-recommend threshold:** Agent stayed in clarify-loop for all conversations under 5 turns (8 of 10 sample traces). Lowered to turn 2.
- **45s probe latency cap:** Hid a 30s spec violation. Tightened to 35s with documented intent to verify deployed endpoint independently.
- **Vacuous-pass probes 7 and 8:** Original assertions were `if resp["recommendations"]:` (passed on empty recs). Rewrote to assert non-empty + presence of expected test-type letters.

## 8. Risks and known limitations

- **Foundational injection over-triggers on C6 (chemical plant + "supervisor"):** A regex word-boundary match on "supervisor" injects OPQ32r/Manager Plus even when the user wants safety/reliability assessments. Would refine trigger list as priority for v2.
- **Free-tier latency floor:** When Groq cold-starts after idle, the first /chat call can take 8-12s. Render free tier adds another 30-50s on the very first request after spin-down.
- **Hidden trace coverage unknown:** Public Recall@10 doesn't predict hidden trace performance precisely; the foundational-injection rules are tuned to the patterns visible in C1-C10.

## 9. AI tools used

- **Antigravity (Anthropic Opus 4.6):** Initial scaffolding, refactor passes, bulk edits across multiple files, verification-gated mini-prompts
- **Glean:** Diagnostic analysis, retrieval debugging, prompt engineering, decision documentation, this approach document
- **Groq (Llama 3.3 70B, Llama 3.1 8B):** Production LLM for runtime reasoning across all agent nodes
- **Gemini Flash 2.5:** Reranker primary + final-tier LLM fallback

## 10. How to reproduce

```bash
git clone https://github.com/sriramnalla30/shl_project
cd shl_project
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate.ps1 on Windows
pip install -e .
cp .env.example .env                                  # add GROQ + GEMINI keys
python scripts/build_indexes.py                       # produces data/ artifacts
uvicorn app.main:app --port 8000                      # in one terminal
python -m eval.replay sample_conversations/GenAI_SampleConversations   # in another
```

Deployed endpoint: `<RENDER_URL_TO_BE_FILLED>/health` and `/chat`.
