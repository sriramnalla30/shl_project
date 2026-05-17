# SHL Conversational Assessment Recommender

A production-grade conversational AI agent that recommends SHL Individual Test Solutions through multi-turn dialogue with hiring managers.

## Architecture

```
<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/e2f69997-b2ae-4d80-ba31-969a8c66c03d" />

```

### Key Design Decisions

- **Hybrid Retrieval**: BM25 (keyword) + FAISS (dense, bge-small-en-v1.5) fused via Reciprocal Rank Fusion (k=60)
- **Validator-Loop Pattern**: Composer → Validator → retry (max 2) → safe fallback
- **Stateless Service**: Full conversation history sent each turn; no server-side sessions
- **LLM Strategy**: Groq Llama-3.3-70B (main), Llama-3.1-8B (cheap/fallback)
- **Strict Grounding**: Every URL checked against `data/url_allowlist.txt`

## Quick Start

```bash
# 1. Clone and setup
cd shl-recommender
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# 3. Build indexes (one-time)
python scripts/build_indexes.py

# 4. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API

### `GET /health`
Returns `{"status": "ok"}` when ready.

### `POST /chat`
```json
{
  "messages": [
    {"role": "user", "content": "I need a personality test for a senior engineer"}
  ]
}
```

Response:
```json
{
  "reply": "Based on your requirements...",
  "recommendations": [
    {
      "name": "Occupational Personality Questionnaire OPQ32r",
      "url": "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
      "test_type": "P"
    }
  ],
  "end_of_conversation": true
}
```

## Evaluation

```bash
# Start server first, then:
pytest eval/probes/test_probes.py -v
```

### Metrics Targets
| Metric | Target | Description |
|--------|--------|-------------|
| Mean Recall@10 | ≥ 0.75 | Fraction of ground-truth assessments in top-10 |
| Schema Compliance | 100% | Every response passes Pydantic validation |
| Behavior Probes | ≥ 11/12 | End-to-end behavior tests |
| Median Latency | < 8s | Per-turn response time |

## Docker

**Before `docker build`:** Run `python scripts/build_indexes.py` to generate the `data/` artifacts. The Docker image expects them to exist.

```bash
python scripts/build_indexes.py    # prerequisite — generates data/
docker build -t shl-recommender .
docker run -p 8000:8000 --env-file .env shl-recommender
```

## Project Structure

```
shl-recommender/
├── app/
│   ├── main.py              # FastAPI app + lifespan
│   ├── config.py             # Pydantic Settings
│   ├── schemas.py            # Request/Response models
│   ├── agent/
│   │   ├── graph.py          # LangGraph StateGraph wiring
│   │   ├── state.py          # Slots + AgentState
│   │   ├── llm.py            # Groq wrapper + prompt loading
│   │   ├── nodes/            # 9 node implementations
│   │   └── prompts/          # Prompt templates + SKILL.md
│   ├── retrieval/
│   │   ├── bm25.py           # BM25 retrieval
│   │   ├── dense.py          # FAISS + bge-small
│   │   ├── fusion.py         # Reciprocal Rank Fusion
│   │   └── filters.py        # Hard constraint filters
│   └── observability/
│       └── tracing.py        # LangSmith setup
├── data/                     # Built artifacts (not in git)
├── scripts/
│   ├── build_indexes.py      # Offline index builder
│   └── scrape_catalog.py     # Catalog scraper (stub)
├── eval/
│   ├── replay.py             # Stateless replay harness
│   ├── recall.py             # Recall@K metric
│   └── probes/
│       └── test_probes.py    # 12 behavior probes
├── Dockerfile
├── render.yaml
└── pyproject.toml
```

## Tech Stack

- **Orchestration**: LangGraph v1.0 (StateGraph)
- **API**: FastAPI + Pydantic v2
- **Retrieval**: rank_bm25 + FAISS + bge-small-en-v1.5
- **LLM**: Groq (Llama 3.3 70B / Llama 3.1 8B)
- **Deployment**: Docker → Render free tier
