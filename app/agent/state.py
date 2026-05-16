"""
Agent state definitions — Slots model and AgentState TypedDict.
"""
from __future__ import annotations

from typing import Literal, Optional, TypedDict

from pydantic import BaseModel

from app.schemas import Message


class Slots(BaseModel):
    """Structured slots extracted from conversation history."""
    role: Optional[str] = None
    seniority: Optional[Literal["junior", "mid", "senior", "lead"]] = None
    duration_max_min: Optional[int] = None
    test_types_wanted: list[str] = []      # subset of {A,B,C,D,E,K,P,S}
    test_types_avoided: list[str] = []
    language: Optional[str] = None
    remote_required: Optional[bool] = None
    must_haves: list[str] = []
    must_avoids: list[str] = []

    def is_sufficient(self) -> bool:
        """Auditable rule mirrored in SKILL.md §4: role is the minimum."""
        return self.role is not None


class AgentState(TypedDict, total=False):
    """Full state passed between LangGraph nodes."""
    messages: list[Message]
    turn: int
    in_scope: bool
    intent: Optional[str]
    slots: Slots
    candidates: list[dict]       # post-retrieval
    shortlist: list[dict]        # post-rerank
    compare_pair: Optional[tuple[dict, dict]]
    draft: Optional[dict]        # composer output before validation
    validation_errors: list[str]
    retry_count: int
    final: Optional[dict]        # the response payload
    __force_clarify_broad: bool  # set by slot_extractor for over-broad JDs
    catalog_gap: Optional[str]   # set by reranker when a distinctive tech is missing
