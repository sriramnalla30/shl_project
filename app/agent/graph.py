"""
LangGraph StateGraph definition — wires all nodes with conditional edges.
"""
from __future__ import annotations

import logging

from langgraph.graph import StateGraph, START, END
from app.agent.state import AgentState
from app.agent.nodes import (
    guardrail, router, slot_extractor, clarifier,
    retriever, reranker, comparator, composer, validator, refuse,
)

logger = logging.getLogger(__name__)


def _route_after_guardrail(s: AgentState) -> str:
    return "refuse" if not s.get("in_scope", True) else "router"


def _route_after_router(s: AgentState) -> str:
    mapping = {
        "refuse": "refuse",
        "clarify": "slot_extractor",
        "extract": "slot_extractor",
        "compare": "comparator",
        "recommend": "slot_extractor",
    }
    intent = s.get("intent", "extract")
    return mapping.get(intent, "slot_extractor")


def _route_after_extract(s: AgentState) -> str:
    intent = s.get("intent", "")
    slots = s.get("slots")

    # New: if extractor flagged the query as over-broad, clarify first
    if s.get("__force_clarify_broad") and s.get("turn", 0) < 3:
        return "clarifier"

    if intent == "compare":
        return "comparator"
    if intent == "clarify" or (
        slots and not slots.is_sufficient() and s.get("turn", 0) < 5
    ):
        return "clarifier"
    return "retriever"


def _route_after_validate(s: AgentState) -> str:
    errors = s.get("validation_errors", [])
    if not errors:
        return END
    if s.get("retry_count", 0) >= 2:
        return "fallback_safe_reply"
    return "composer"


def build_graph():
    """Build and compile the LangGraph state machine."""
    g = StateGraph(AgentState)

    # Add all nodes
    g.add_node("guardrail", guardrail.run)
    g.add_node("router", router.run)
    g.add_node("slot_extractor", slot_extractor.run)
    g.add_node("clarifier", clarifier.run)
    g.add_node("retriever", retriever.run)
    g.add_node("reranker", reranker.run)
    g.add_node("comparator", comparator.run)
    g.add_node("composer", composer.run)
    g.add_node("validator", validator.run)
    g.add_node("refuse", refuse.run)
    g.add_node("fallback_safe_reply", composer.fallback)

    # Wire edges
    g.add_edge(START, "guardrail")

    g.add_conditional_edges("guardrail", _route_after_guardrail,
                            {"refuse": "refuse", "router": "router"})

    g.add_conditional_edges("router", _route_after_router, {
        "refuse": "refuse",
        "slot_extractor": "slot_extractor",
        "comparator": "comparator",
    })

    g.add_conditional_edges("slot_extractor", _route_after_extract, {
        "clarifier": "clarifier",
        "retriever": "retriever",
        "comparator": "comparator",
    })

    g.add_edge("clarifier", "composer")
    g.add_edge("retriever", "reranker")
    g.add_edge("reranker", "composer")
    g.add_edge("comparator", "composer")
    g.add_edge("refuse", "composer")
    g.add_edge("composer", "validator")

    g.add_conditional_edges("validator", _route_after_validate, {
        END: END,
        "composer": "composer",
        "fallback_safe_reply": "fallback_safe_reply",
    })

    g.add_edge("fallback_safe_reply", END)

    return g.compile()
