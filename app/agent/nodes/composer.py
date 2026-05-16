"""
Composer node — renders the final reply. Receives structured input only.
"""
from __future__ import annotations

import json
import logging

from app.agent.state import AgentState, Slots
from app.agent import llm

logger = logging.getLogger(__name__)


def _build_shortlist_table(shortlist: list[dict]) -> str:
    lines = []
    for i, item in enumerate(shortlist, 1):
        lines.append(f"{i}. {item['name']} | {item.get('url','')} | {item.get('test_type','')} | "
                     f"duration={item.get('duration_minutes','N/A')} | reason={item.get('reason','')}")
    return "\n".join(lines)


async def run(state: AgentState) -> dict:
    intent = state.get("intent", "clarify")
    feedback = state.get("validation_errors") or []

    # Clarify/refuse drafts are already built by their nodes
    if intent in ("clarify", "refuse", "compare") and state.get("draft"):
        return {"draft": state["draft"], "retry_count": state.get("retry_count", 0) + 1}

    # Recommend path
    slots: Slots = state.get("slots", Slots())
    shortlist = state.get("shortlist", [])

    if not shortlist:
        return await fallback(state)

    feedback_block = ""
    if feedback:
        feedback_block = "PREVIOUS ATTEMPT FAILED. Fix these issues:\n" + "\n".join(f"- {e}" for e in feedback)

    try:
        prompt_template = llm.load_prompt("composer")
        prompt = prompt_template.format(
            slots_json=slots.model_dump_json(indent=2),
            shortlist_table=_build_shortlist_table(shortlist),
            feedback_block=feedback_block,
        )
        raw = await llm.call_main(prompt, max_tokens=2048, temperature=0.1)
        draft = llm.extract_json_from_text(raw)

        if not isinstance(draft, dict) or "reply" not in draft:
            logger.warning("Composer: invalid JSON, building from shortlist directly")
            draft = _build_direct_draft(shortlist, slots)

        # Ensure recommendations use exact catalog data
        if "recommendations" in draft and shortlist:
            draft["recommendations"] = _ensure_exact_recs(draft["recommendations"], shortlist)

        if "end_of_conversation" not in draft:
            draft["end_of_conversation"] = True

        return {"draft": draft, "retry_count": state.get("retry_count", 0) + 1}
    except Exception as e:
        logger.warning("Composer failed (%s), using direct build", e)
        return {"draft": _build_direct_draft(shortlist, slots),
                "retry_count": state.get("retry_count", 0) + 1}


def _ensure_exact_recs(recs: list, shortlist: list[dict]) -> list[dict]:
    """Ensure recommendations use exact names/URLs from catalog."""
    name_map = {item["name"].lower(): item for item in shortlist}
    result = []
    for r in recs:
        if isinstance(r, dict):
            name = r.get("name", "")
            if name.lower() in name_map:
                item = name_map[name.lower()]
                result.append({"name": item["name"], "url": item["url"],
                               "test_type": item.get("test_type", "")})
            else:
                result.append(r)
    return result if result else [{"name": s["name"], "url": s["url"],
                                    "test_type": s.get("test_type", "")} for s in shortlist[:10]]


def _build_direct_draft(shortlist: list[dict], slots: Slots) -> dict:
    """Build a draft directly from shortlist without LLM."""
    recs = [{"name": s["name"], "url": s["url"], "test_type": s.get("test_type", "")}
            for s in shortlist[:10]]
    role = slots.role or "the role"
    return {
        "reply": f"Based on your requirements for {role}, I've selected {len(recs)} assessments that best match your needs.",
        "recommendations": recs,
        "end_of_conversation": True,
    }


async def fallback(state: AgentState) -> dict:
    """Degraded mode — passes schema, never hallucinates."""
    return {"draft": {
        "reply": "Could you tell me a bit more about the role you're hiring for?",
        "recommendations": [],
        "end_of_conversation": False,
    }, "final": None, "retry_count": 0, "validation_errors": []}
