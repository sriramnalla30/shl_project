"""
Reranker node — LLM-based reranking of candidates against slots.
One batched call, returns top 1-10 with reasons.
"""
from __future__ import annotations

import logging

from app.agent.state import AgentState, Slots
from app.agent import llm

logger = logging.getLogger(__name__)


def _build_candidates_table(candidates: list[dict]) -> str:
    """Format candidates as a compact table for the LLM prompt."""
    lines = ["id | name | test_type | duration_minutes | summary"]
    lines.append("---|------|-----------|-----------------|--------")
    for c in candidates:
        desc = (c.get("description", "") or "")[:120]
        lines.append(
            f"{c['id']} | {c['name']} | {c.get('test_type', '')} | "
            f"{c.get('duration_minutes', 'N/A')} | {desc}"
        )
    return "\n".join(lines)


async def run(state: AgentState) -> dict:
    slots: Slots = state.get("slots", Slots())
    candidates = state.get("candidates", [])

    if not candidates:
        logger.warning("Reranker: no candidates to rank")
        return {"shortlist": []}

    try:
        prompt_template = llm.load_prompt("reranker")
        prompt = prompt_template.format(
            slots_json=slots.model_dump_json(indent=2),
            candidates_table=_build_candidates_table(candidates),
        )
        ranked = await llm.call_json(prompt, max_tokens=2048)

        if isinstance(ranked, dict):
            # LLM sometimes wraps array in a dict like {"results": [...]}
            for v in ranked.values():
                if isinstance(v, list):
                    ranked = v
                    break
            else:
                logger.warning("Reranker: got dict with no list values, using top candidates")
                return {"shortlist": candidates[:8]}

        if not isinstance(ranked, list):
            logger.warning("Reranker: expected list, got %s", type(ranked))
            return {"shortlist": candidates[:8]}

        # Hydrate from candidates
        by_id = {c["id"]: c for c in candidates}
        shortlist = []
        for r in ranked:
            if not isinstance(r, dict):
                continue
            cid = r.get("catalog_id")
            if cid is not None and cid in by_id:
                item = {**by_id[cid], "reason": r.get("reason", "")}
                shortlist.append(item)
            if len(shortlist) >= 10:
                break

        # Fallback if reranker returned nothing valid
        if not shortlist:
            logger.warning("Reranker: no valid items in ranked output, using top candidates")
            shortlist = candidates[:5]

        # Gap detection: if the user's role/skills include a specific technology,
        # check whether ANY shortlist item's name contains that technology token.
        # If not, attach a gap marker that the composer will surface.
        gap_skill = None
        if slots.role or slots.must_haves:
            import re
            raw_text = " ".join([slots.role or ""] + (slots.must_haves or []))
            tokens = re.findall(r"\b[A-Z][a-zA-Z0-9+#.]{2,}\b", raw_text)
            # Known techs that exist in catalog — don't flag these
            known_in_catalog = {"java", "python", "sql", "aws", "docker", "spring",
                                "angular", "excel", "word", "linux", "networking",
                                "hipaa", "opq", "shl", "verify"}
            distinctive = [t for t in tokens if t.lower() not in known_in_catalog]
            for t in distinctive:
                if not any(t.lower() in s["name"].lower() for s in shortlist):
                    gap_skill = t
                    break

        logger.info("Reranker: %d → %d shortlisted, gap=%s", len(candidates), len(shortlist), gap_skill)
        return {"shortlist": shortlist, "catalog_gap": gap_skill}
    except Exception as e:
        logger.warning("Reranker failed (%s), using top-5 candidates as fallback", e)
        return {"shortlist": candidates[:5], "catalog_gap": None}
