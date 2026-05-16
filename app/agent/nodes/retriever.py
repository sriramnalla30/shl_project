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
    """Build a synthesized query from structured slots + user messages."""
    user_msgs = []
    for m in reversed(messages):
        if m.role == "user":
            user_msgs.append(m.content)
            if len(user_msgs) >= 3:
                break
    user_msgs.reverse()

    parts = []
    if slots.role:
        parts.append(f"role: {slots.role}")
    if slots.seniority:
        seniority_terms = {
            "senior": "senior leadership executive director",
            "lead": "lead principal senior",
            "mid": "mid-level experienced",
            "junior": "junior entry-level graduate",
        }
        parts.append(f"seniority: {seniority_terms.get(slots.seniority, slots.seniority)}")
    if slots.must_haves:
        parts.append("skills: " + ", ".join(slots.must_haves))
    if slots.test_types_wanted:
        type_map = {"A": "aptitude ability reasoning", "B": "situational judgment",
                     "C": "competency", "D": "development 360",
                     "E": "assessment exercise", "K": "knowledge skills technical",
                     "P": "personality behavior OPQ", "S": "simulation"}
        type_terms = " ".join(type_map.get(t, t) for t in slots.test_types_wanted)
        parts.append(f"test types: {type_terms}")
    for msg in user_msgs:
        parts.append(f"user: {msg}")
    return " | ".join(parts) if parts else (user_msgs[0] if user_msgs else "")


async def run(state: AgentState) -> dict:
    slots: Slots = state.get("slots", Slots())
    messages = state.get("messages", [])
    query = render_query(slots, messages)
    logger.info("Retriever query: %s", query[:120])

    # Hybrid retrieval
    bm = bm25_topk(query, k=50)
    de = dense_topk(query, k=50)
    fused = rrf([bm, de], k=100)[:50]

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
