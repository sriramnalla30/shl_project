"""
Router node — classifies the user's latest turn into an intent.
Turn-budget aware: forces recommend from turn 5 onward.
"""
from __future__ import annotations

import json
import logging

from app.agent.state import AgentState, Slots
from app.agent import llm

logger = logging.getLogger(__name__)

VALID_INTENTS = {"clarify", "extract", "compare", "recommend", "refuse"}


def _format_messages_compact(state: AgentState) -> str:
    lines = []
    for m in state.get("messages", []):
        lines.append(f"{m.role}: {m.content}")
    return "\n".join(lines)


async def run(state: AgentState) -> dict:
    turn = state.get("turn", 0)
    slots: Slots = state.get("slots", Slots())

    # On turn 1, extract slots first unless the message is trivially vague
    if turn <= 1:
        last_user = ""
        for m in reversed(state.get("messages", [])):
            if m.role == "user":
                last_user = m.content
                break
        if len(last_user.strip()) < 15:
            logger.info("Router: turn=%d, vague msg → clarify", turn)
            return {"intent": "clarify"}
        # Detailed first message → extract slots then decide
        logger.info("Router: turn=%d, detailed msg → extract", turn)
        return {"intent": "extract"}

    # Commit bias: once role is known, prefer recommend after turn 1
    if turn >= 2 and slots.role:
        logger.info("Router: turn=%d, role known → recommend (commit bias)", turn)
        return {"intent": "recommend"}

    # Last-resort commit: by turn 3, recommend even without role
    # (better to retrieve on partial info than return zero recs)
    if turn >= 3:
        logger.info("Router: turn=%d, late-turn force recommend", turn)
        return {"intent": "recommend"}
    # LLM classification
    try:
        prompt_template = llm.load_prompt("router")
        prompt = prompt_template.format(
            turn_count=turn,
            messages_compact=_format_messages_compact(state),
            slots_json=slots.model_dump_json(indent=2),
        )
        raw = await llm.call_cheap(prompt, max_tokens=10, temperature=0.0)
        intent = raw.strip().lower().strip('"').strip("'")

        # Validate
        if intent not in VALID_INTENTS:
            # Try to find a valid intent in the response
            for valid in VALID_INTENTS:
                if valid in intent:
                    intent = valid
                    break
            else:
                logger.warning("Router: invalid intent '%s', defaulting to extract", intent)
                intent = "extract"

        # Safety net: don't loop on clarify when we have role info
        if intent == "clarify" and slots.role and turn >= 2:
            logger.info("Router: overriding clarify→recommend (role known, turn=%d)", turn)
            intent = "recommend"

        logger.info("Router: intent=%s (turn=%d)", intent, turn)
        return {"intent": intent}
    except Exception as e:
        logger.warning("Router LLM failed (%s), defaulting to extract", e)
        return {"intent": "extract"}
