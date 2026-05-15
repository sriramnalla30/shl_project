"""
Comparator node — catalog-grounded side-by-side comparison.
"""
from __future__ import annotations

import json
import logging
import re

from app.agent.state import AgentState
from app.agent import llm

logger = logging.getLogger(__name__)
_catalog: list[dict] = []


def set_catalog(catalog: list[dict]) -> None:
    global _catalog
    _catalog = catalog


def resolve_name(name: str) -> dict | None:
    """Resolve user-provided name to catalog record via fuzzy match."""
    nl = name.lower().strip()
    for rec in _catalog:
        if rec["name"].lower() == nl:
            return rec
    for rec in _catalog:
        if nl in rec["name"].lower() or rec["name"].lower() in nl:
            return rec
    tokens = set(nl.split())
    best, best_rec = 0, None
    for rec in _catalog:
        overlap = len(tokens & set(rec["name"].lower().split()))
        if overlap > best and overlap >= max(1, len(tokens) // 2):
            best, best_rec = overlap, rec
    return best_rec


def _extract_pair(text: str) -> tuple[str, str] | None:
    patterns = [
        r"(?:compare|difference between|diff between)\s+(.+?)\s+(?:and|vs\.?|versus)\s+(.+?)[\?\.]?$",
        r"(.+?)\s+(?:vs\.?|versus)\s+(.+?)[\?\.]?$",
        r"(?:what'?s the )?difference between\s+(.+?)\s+and\s+(.+?)[\?\.]?$",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            return m.group(1).strip().strip('"\''), m.group(2).strip().strip('"\'')
    return None


async def run(state: AgentState) -> dict:
    last_user = ""
    for m in reversed(state.get("messages", [])):
        if m.role == "user":
            last_user = m.content
            break

    pair = _extract_pair(last_user)
    if not pair:
        return {"compare_pair": None, "intent": "clarify"}

    rec_a = resolve_name(pair[0])
    rec_b = resolve_name(pair[1])

    if not rec_a or not rec_b:
        missing = [n for n, r in [(pair[0], rec_a), (pair[1], rec_b)] if not r]
        draft = {
            "reply": f"I couldn't find {', '.join(missing)} in the catalog. Could you check the name(s)?",
            "recommendations": [],
            "end_of_conversation": False,
        }
        return {"compare_pair": None, "draft": draft, "retry_count": 0}

    try:
        prompt_template = llm.load_prompt("comparator")
        prompt = prompt_template.format(
            record_a_json=json.dumps(rec_a, indent=2, default=str),
            record_b_json=json.dumps(rec_b, indent=2, default=str),
        )
        comparison = await llm.call_main(prompt, max_tokens=512, temperature=0.2)
        recs = [{"name": r["name"], "url": r["url"], "test_type": r.get("test_type", "")} for r in [rec_a, rec_b]]
        draft = {"reply": comparison.strip(), "recommendations": recs, "end_of_conversation": False}
        return {"compare_pair": (rec_a, rec_b), "draft": draft, "retry_count": 0}
    except Exception as e:
        logger.warning("Comparator LLM failed (%s)", e)
        return {"compare_pair": None, "intent": "refuse"}
