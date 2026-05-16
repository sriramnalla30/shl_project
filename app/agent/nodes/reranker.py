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
    """Format candidates as a compact table for the LLM prompt.
    Capped at 25 candidates × 60-char descriptions to fit Gemini Flash context
    efficiently and reduce per-call token consumption ~3x. Foundational
    injection earlier in the pipeline guarantees key items are near the top."""
    MAX_CANDIDATES = 25
    DESC_CHARS = 60
    lines = ["id | name | test_type | dur | summary"]
    lines.append("---|------|-----------|-----|--------")
    for c in candidates[:MAX_CANDIDATES]:
        desc = (c.get("description", "") or "")[:DESC_CHARS]
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
        # Reranker goes to Gemini first (separate quota pool from Groq, avoids
        # rate-limit cascades that pushed chat latency past 30s). Falls back to
        # Groq via call_json if Gemini fails.
        try:
            raw = await llm._gemini_call_with_rotation(
                prompt=prompt,
                system="",
                max_tokens=2048,
                temperature=0.1,
                timeout=20.0,
            )
            ranked = llm.extract_json_from_text(raw)
            if ranked is None:
                logger.warning("Reranker: Gemini returned unparseable JSON, falling back to Groq")
                ranked = await llm.call_json(prompt, max_tokens=2048)
        except Exception as gem_err:
            logger.warning("Reranker: Gemini call failed (%s), falling back to Groq", gem_err)
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
        # Hydrate from candidates — accept multiple id field names + coerce strings
        by_id = {c["id"]: c for c in candidates}
        shortlist = []
        for r in ranked:
            if not isinstance(r, dict):
                continue
            # LLM may use "catalog_id", "id", or "position"
            cid = r.get("catalog_id")
            if cid is None:
                cid = r.get("id")
            if cid is None and isinstance(r.get("position"), int):
                cid = r["position"]
            # Coerce numeric strings to int
            if isinstance(cid, str) and cid.isdigit():
                cid = int(cid)
            if cid is not None and cid in by_id:
                item = {**by_id[cid], "reason": r.get("reason", "")}
                shortlist.append(item)
            if len(shortlist) >= 10:
                break

        # Fallback if reranker returned nothing valid
        if not shortlist:
            logger.warning("Reranker: no valid items in ranked output, using top candidates")
            shortlist = candidates[:8]

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
        logger.warning("Reranker failed (%s), using top-8 candidates as fallback", e)
        return {"shortlist": candidates[:8], "catalog_gap": None}