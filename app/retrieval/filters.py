"""
Hard filters — test-type whitelist, duration cap, etc.
Applied after fusion, before LLM reranker.
Pure functions.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def apply_hard_filters(
    candidates: list[dict],
    test_types_wanted: list[str] | None = None,
    duration_max_min: int | None = None,
) -> list[dict]:
    """
    Filter candidate catalog records based on hard constraints from slots.

    Args:
        candidates: List of catalog records (dicts with id, test_type_codes, duration_minutes, etc.)
        test_types_wanted: If non-empty, keep only candidates whose test_type_codes
                           intersect with wanted types.
        duration_max_min: If set, exclude candidates whose duration exceeds this.

    Returns:
        Filtered list of candidates.
    """
    filtered = candidates

    # Test-type whitelist filter
    if test_types_wanted:
        wanted_set = set(test_types_wanted)
        filtered = [
            c for c in filtered
            if set(c.get("test_type_codes", c.get("test_type", "").split())).intersection(wanted_set)
        ]
        logger.debug("After test_type filter: %d candidates", len(filtered))

    # Duration cap filter
    if duration_max_min is not None:
        filtered = [
            c for c in filtered
            if c.get("duration_minutes") is None or c["duration_minutes"] <= duration_max_min
        ]
        logger.debug("After duration filter: %d candidates", len(filtered))

    # If filters removed everything, fall back to unfiltered
    # (better to return something for the reranker than nothing)
    if not filtered and candidates:
        logger.warning("Hard filters removed all candidates; falling back to unfiltered")
        return candidates

    return filtered
