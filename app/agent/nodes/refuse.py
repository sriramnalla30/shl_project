"""
Refuse node — canned refusal templates. No LLM unless we want varied phrasing.
"""
from __future__ import annotations

import logging
import random

from app.agent.state import AgentState

logger = logging.getLogger(__name__)

REFUSAL_TEMPLATES = [
    "I can only help with selecting SHL Individual Test Solutions — happy to suggest assessments if you can tell me about the role you're hiring for.",
    "That's outside my scope. I specialize in recommending SHL assessment tests. What role are you looking to assess?",
    "I'm not able to help with that, but I can recommend SHL assessments for any role. What position are you hiring for?",
]


async def run(state: AgentState) -> dict:
    reply = random.choice(REFUSAL_TEMPLATES)
    logger.info("Refuse: delivering refusal")
    draft = {
        "reply": reply,
        "recommendations": [],
        "end_of_conversation": False,
    }
    return {"draft": draft, "retry_count": 0}
