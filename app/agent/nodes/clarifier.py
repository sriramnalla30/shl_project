"""
Clarifier node — generates exactly one focused question for the highest-value missing slot.
Slot selection is rule-based (mirrors SKILL §6); phrasing is LLM.
"""
from __future__ import annotations

import logging

from app.agent.state import AgentState, Slots
from app.agent import llm

logger = logging.getLogger(__name__)

# Priority order from SKILL §6
SLOT_PRIORITY = [
    ("role", "role", "What role are you hiring for?"),
    ("seniority", "seniority", "What seniority level — junior, mid, senior, or lead?"),
    ("test_types_wanted", "test_types_wanted", "Are you looking primarily for skills tests, personality, reasoning, or a mix?"),
    ("duration_max_min", "duration_max_min", "Is there a time budget per candidate (e.g. under 30 minutes)?"),
    ("must_haves", "must_haves", "Any specific skills or competencies you want covered?"),
]


def _pick_target_slot(slots: Slots) -> tuple[str, str]:
    """Pick the highest-priority missing slot. Returns (slot_name, fallback_question)."""
    for slot_name, attr_name, fallback in SLOT_PRIORITY:
        val = getattr(slots, attr_name)
        if val is None or val == [] or val == "":
            return slot_name, fallback
    return "role", "What role are you hiring for?"


async def run(state: AgentState) -> dict:
    slots: Slots = state.get("slots", Slots())
    target_slot, fallback_q = _pick_target_slot(slots)

    try:
        prompt_template = llm.load_prompt("clarifier")
        prompt = prompt_template.format(
            target_slot=target_slot,
            slots_json=slots.model_dump_json(indent=2),
        )
        question = await llm.call_cheap(prompt, max_tokens=80, temperature=0.3)
        question = question.strip().strip('"').strip("'")

        if not question or len(question) < 5:
            question = fallback_q

        logger.info("Clarifier: asking about '%s' → %s", target_slot, question)

        draft = {
            "reply": question,
            "recommendations": [],
            "end_of_conversation": False,
        }
        return {"draft": draft, "retry_count": 0}
    except Exception as e:
        logger.warning("Clarifier failed (%s), using fallback question", e)
        draft = {
            "reply": fallback_q,
            "recommendations": [],
            "end_of_conversation": False,
        }
        return {"draft": draft, "retry_count": 0}
