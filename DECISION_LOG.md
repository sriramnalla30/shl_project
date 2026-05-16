# Decision Log

## D-001: Catalog Schema Adaptation
**Date**: 2026-05-15
**Decision**: Adapt code to the actual `shl_product_catalog.json` schema rather than the spec.
**Rationale**: The raw catalog has different field names (`link` vs `url`, `keys` vs `test_type`, etc.) and types. The catalog is truth; the spec is a design doc.
**Impact**: `scripts/build_indexes.py` normalizes at build time. Runtime code uses the normalized schema.

## D-002: 377 Records (not 366)
**Date**: 2026-05-15
**Decision**: Accept 377 records in the catalog.
**Rationale**: The spec mentions ~366 but the actual scraped catalog has 377. No records removed.

## D-003: Groq-Only LLM Strategy
**Date**: 2026-05-15
**Decision**: Use Groq Llama 3.3 70B (main) + Llama 3.1 8B (cheap/fallback). Gemini is optional.
**Rationale**: User provided only Groq API key. Both models are free-tier compatible. The 8B model handles cheap calls (guardrail, router, clarifier) while 70B handles heavy calls (slot extraction, reranking, composing).

## D-004: Brace Escaping in Prompt Templates
**Date**: 2026-05-15
**Decision**: Escape `{` and `}` in SKILL.md content before injecting into prompt templates.
**Rationale**: SKILL.md contains JSON examples with braces that break Python `.format()` when injected via `<<SKILL>>` marker. Escaping to `{{`/`}}` prevents KeyError.

## D-005: Router Turn-1 Logic
**Date**: 2026-05-15
**Decision**: On turn 1, only default to "clarify" if the message is very short (<15 chars). Otherwise, run slot extraction first.
**Rationale**: Users often provide detailed first messages (e.g., "I need a personality test for a senior software engineer"). The router should not short-circuit to clarification when there's enough info to extract.

## D-006: Validator Fallback Strategy
**Date**: 2026-05-15
**Decision**: After 2 failed validation attempts, return a safe canned response rather than crashing.
**Rationale**: 100% schema compliance is a hard requirement. The fallback always passes validation.

## D-007: Fix Infinite Validator→Composer Loop (C1)
**Date**: 2026-05-16
**File(s)**: `app/agent/nodes/composer.py`
**Change**: Increment `retry_count` on the clarify/refuse/compare pass-through branch.
**Reason**: Without increment, a failed validation on these paths caused an infinite loop until FastAPI timeout.
**Impact**: No `/chat` request can hang indefinitely. Loop terminates after 2 retries via existing fallback.

## D-008: Rewrite Replay Harness with Simulated User (C2)
**Date**: 2026-05-16
**File(s)**: `eval/replay.py`, `eval/traces/*.json`
**Change**: Replaced pre-recorded trace playback with LLM-driven simulated user pattern. Added Recall@10 computation and markdown report generation.
**Reason**: The official evaluator uses a sim-user that reacts to agent replies. Pre-recorded playback was not predictive of submission score.
**Impact**: Local Recall@10 numbers now match the evaluator's methodology. Created 10 persona-based traces.

## D-009: Comparator Failure Draft (C3)
**Date**: 2026-05-16
**File(s)**: `app/agent/nodes/comparator.py`
**Change**: When comparator LLM fails, produce a coherent error draft instead of setting `intent=refuse` with no draft.
**Reason**: Empty draft on refuse path caused composer to fall through to recommend with empty shortlist, giving a non-sequitur "tell me about the role" reply to a compare question.
**Impact**: Compare failures now get a sensible error message.

## D-010: Latency Probe Cap to 30s (C4)
**Date**: 2026-05-16
**File(s)**: `eval/probes/test_probes.py`
**Change**: Tightened latency probe from 45s to 30s per the spec requirement.
**Reason**: The take-home spec mandates 30s per call. A 45s cap hid spec violations.
**Impact**: Probe 12 now enforces the actual spec limit.

## D-011: Strengthen Probes 7 and 8 (M5)
**Date**: 2026-05-16
**File(s)**: `eval/probes/test_probes.py`
**Change**: Probe 7 now asserts non-empty recommendations with P-type results. Probe 8 asserts recommendations exist after multi-turn refinement with P or B type checks.
**Reason**: Original probes were vacuously true — P7 passed on zero recs, P8 only checked reply non-empty.
**Impact**: These probes now catch real regressions in slot extraction and multi-turn refinement.

## D-012: Drop Hallucinated Recommendations (M6)
**Date**: 2026-05-16
**File(s)**: `app/agent/nodes/composer.py`
**Change**: `_ensure_exact_recs` now drops items not found in the shortlist instead of passing them through.
**Reason**: Hallucinated names burn the retry budget when the validator catches them. Pre-filtering reduces retry pressure.
**Impact**: Fewer validator retries, more reliable first-pass responses.

## D-013: Dockerfile Fail-Fast Guard (M7)
**Date**: 2026-05-16
**File(s)**: `Dockerfile`, `README.md`
**Change**: Added `RUN test -f data/url_allowlist.txt` guard in Dockerfile. Updated README with explicit docker-build prerequisite.
**Reason**: Fresh clone + `docker build` would fail silently. Now fails fast with a clear error message.
**Impact**: No ambiguous Docker build failures.

## D-014: URL Allowlist Fail-Fast at Startup (M8)
**Date**: 2026-05-16
**File(s)**: `app/main.py`
**Change**: Raise `RuntimeError` if URL allowlist is empty or missing during lifespan startup.
**Reason**: Empty allowlist silently degrades all recommendations — every URL fails validation, every request falls back to canned reply, Recall@10 drops to 0%.
**Impact**: Server refuses to start without valid data, giving a clear error message.
