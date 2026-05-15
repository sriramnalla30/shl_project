"""
Retriever node — BM25 + Dense + RRF fusion + hard filters.
No LLM. Pure deterministic retrieval.
"""
from __future__ import annotations

import logging

from app.agent.state import AgentState, Slots
from app.retrieval.bm25 import bm25_topk
from app.retrieval.dense import dense_topk
from app.retrieval.fusion import rrf
from app.retrieval.filters import apply_hard_filters

logger = logging.getLogger(__name__)

# Module-level catalog reference (set at startup)
_catalog: list[dict] = []


def set_catalog(catalog: list[dict]) -> None:
    """Set the catalog reference. Called once at startup."""
    global _catalog
    _catalog = catalog


def render_query(slots: Slots, messages: list) -> str:
    """Build a synthesized query from structured slots + last user message."""
    last_user = ""
    for m in reversed(messages):
        if m.role == "user":
            last_user = m.content
            break

    parts = []
    if slots.role:
        parts.append(f"role: {slots.role}")
    if slots.seniority:
        parts.append(f"seniority: {slots.seniority}")
    if slots.must_haves:
        parts.append("skills: " + ", ".join(slots.must_haves))
    if slots.test_types_wanted:
        type_map = {"A": "aptitude ability reasoning", "B": "situational judgment",
                     "C": "competency", "D": "development 360",
                     "E": "assessment exercise", "K": "knowledge skills technical",
                     "P": "personality behavior", "S": "simulation"}
        type_terms = " ".join(type_map.get(t, t) for t in slots.test_types_wanted)
        parts.append(f"test types: {type_terms}")
    if last_user:
        parts.append(f"recent: {last_user}")
    return " | ".join(parts) if parts else last_user


async def run(state: AgentState) -> dict:
    slots: Slots = state.get("slots", Slots())
    messages = state.get("messages", [])
    query = render_query(slots, messages)
    logger.info("Retriever query: %s", query[:120])

    # Hybrid retrieval
    bm = bm25_topk(query, k=30)
    de = dense_topk(query, k=30)
    fused = rrf([bm, de], k=60)[:30]

    # Hydrate with catalog records
    candidates = []
    for doc_id, score in fused:
        if 0 <= doc_id < len(_catalog):
            rec = {**_catalog[doc_id], "retrieval_score": score}
            candidates.append(rec)

    # Apply hard filters from slots
    filtered = apply_hard_filters(
        candidates,
        test_types_wanted=slots.test_types_wanted if slots.test_types_wanted else None,
        duration_max_min=slots.duration_max_min,
    )

    logger.info("Retriever: %d fused → %d filtered candidates", len(candidates), len(filtered))
    return {"candidates": filtered}
