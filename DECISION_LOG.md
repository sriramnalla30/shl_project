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
