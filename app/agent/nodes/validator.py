"""
Validator node — schema check + URL allowlist + size check.
No LLM. Loops back to Composer with feedback on failure.
"""
from __future__ import annotations

import logging

from app.agent.state import AgentState
from app.schemas import ChatResponse

logger = logging.getLogger(__name__)

_url_allowlist: frozenset[str] = frozenset()


def set_url_allowlist(allowlist: frozenset[str]) -> None:
    global _url_allowlist
    _url_allowlist = allowlist


async def run(state: AgentState) -> dict:
    draft = state.get("draft")
    if draft is None:
        return {"validation_errors": ["no draft"], "final": None}

    errors: list[str] = []

    # 1. Pydantic shape check
    try:
        resp = ChatResponse(**draft)
    except Exception as e:
        logger.warning("Validator: schema fail — %s", e)
        return {"validation_errors": [f"schema: {e}"], "final": None}

    # 2. URL allowlist check
    for r in resp.recommendations:
        url = str(r.url).rstrip("/")
        url_slash = url + "/"
        if url not in _url_allowlist and url_slash not in _url_allowlist:
            errors.append(f"off_catalog_url: {r.url}")

    # 3. Size rule
    intent = state.get("intent", "")
    if intent == "recommend" and resp.recommendations:
        if not (1 <= len(resp.recommendations) <= 10):
            errors.append(f"size: recommend must return 1-10 items, got {len(resp.recommendations)}")
    if intent in ("clarify", "refuse") and resp.recommendations:
        errors.append("size: clarify/refuse turn must return zero items")

    # 4. end_of_conversation consistency
    if resp.recommendations and not resp.end_of_conversation and intent == "recommend":
        # Auto-fix: set end_of_conversation to true
        draft["end_of_conversation"] = True

    if errors:
        logger.warning("Validator: %d errors — %s", len(errors), errors)
        return {"validation_errors": errors, "final": None}

    logger.info("Validator: all checks passed")
    return {"validation_errors": [], "final": resp.model_dump()}
