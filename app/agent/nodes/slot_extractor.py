"""
Slot Extractor node — re-parses the entire conversation into structured Slots.
Idempotent: handles user corrections by always re-deriving from full history.
"""
from __future__ import annotations

import logging

from app.agent.state import AgentState, Slots
from app.agent import llm

logger = logging.getLogger(__name__)


def _format_messages_compact(state: AgentState) -> str:
    lines = []
    for m in state.get("messages", []):
        lines.append(f"{m.role}: {m.content}")
    return "\n".join(lines)


async def run(state: AgentState) -> dict:
    try:
        prompt_template = llm.load_prompt("slot_extractor")
        prompt = prompt_template.format(
            messages_compact=_format_messages_compact(state),
        )
        slots_dict = await llm.call_json(prompt, max_tokens=512)

        if isinstance(slots_dict, dict):
            # Clean up any unexpected fields
            valid_fields = set(Slots.model_fields.keys())
            cleaned = {k: v for k, v in slots_dict.items() if k in valid_fields}
            slots = Slots(**cleaned)
        else:
            logger.warning("Slot extractor returned non-dict: %s", type(slots_dict))
            slots = state.get("slots", Slots())

        # Detect over-broad queries: many distinct technical areas in must_haves
        # triggers a clarification before recommend (C9 pattern)
        breadth = len(slots.must_haves) if slots.must_haves else 0
        force_broad = False
        if breadth >= 5 and slots.role:
            logger.info("Slot extractor: breadth=%d → forcing clarify on broad scope", breadth)
            force_broad = True

        logger.info("Slots extracted: role=%s, test_types=%s", slots.role, slots.test_types_wanted)
        return {"slots": slots, "__force_clarify_broad": force_broad}
    except Exception as e:
        logger.warning("Slot extractor failed (%s), keeping existing slots", e)
        return {"slots": state.get("slots", Slots())}
