"""
Guardrail node — detects off-topic, prompt injection, legal/general queries.
No LLM call for clear-cut cases; cheap LLM for ambiguous.
"""
from __future__ import annotations

import logging
import re

from app.agent.state import AgentState
from app.agent import llm

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    re.compile(r"ignore (all|previous|the above) instructions", re.I),
    re.compile(r"you are now [a-z ]+", re.I),
    re.compile(r"reveal (your|the) (system )?prompt", re.I),
    re.compile(r"forget (your|all|everything)", re.I),
    re.compile(r"act as (a |an )?", re.I),
    re.compile(r"pretend (to be|you are)", re.I),
]

OFF_TOPIC_HINTS = (
    "salary", "lawsuit", "discrimination law", "visa", "immigration",
    "legal advice", "is it legal", "interview process",
    "how should i structure", "job solutions",
)


def _get_last_user(state: AgentState) -> str:
    messages = state.get("messages", [])
    for m in reversed(messages):
        if m.role == "user":
            return m.content
    return ""


async def run(state: AgentState) -> dict:
    last_user = _get_last_user(state)

    # Rule-based injection check
    if any(p.search(last_user) for p in INJECTION_PATTERNS):
        logger.info("Guardrail: injection detected")
        return {"in_scope": False}

    # Rule-based off-topic check
    lower = last_user.lower()
    if any(h in lower for h in OFF_TOPIC_HINTS):
        logger.info("Guardrail: off-topic hint detected")
        return {"in_scope": False}

    # Ambiguous → cheap LLM check
    try:
        prompt_template = llm.load_prompt("guardrail")
        prompt = prompt_template.format(last_user_message=last_user)
        verdict = await llm.call_cheap(prompt, max_tokens=10, temperature=0.0)
        verdict = verdict.strip().upper()
        in_scope = "OUT_OF_SCOPE" not in verdict
        logger.info("Guardrail LLM verdict: %s → in_scope=%s", verdict, in_scope)
        return {"in_scope": in_scope}
    except Exception as e:
        logger.warning("Guardrail LLM failed (%s), defaulting to in-scope", e)
        return {"in_scope": True}
