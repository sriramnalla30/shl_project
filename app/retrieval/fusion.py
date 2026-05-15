"""
Reciprocal Rank Fusion — combines BM25 and dense retrieval results.
Pure function, parameter-free.
"""
from __future__ import annotations


def rrf(ranked_lists: list[list[tuple[int, float]]], k: int = 60) -> list[tuple[int, float]]:
    """
    Reciprocal Rank Fusion over multiple ranked result lists.

    Each input list is [(catalog_id, score), ...] sorted by score descending.
    Returns fused list sorted by RRF score descending.

    RRF score for doc d = sum over lists of 1 / (k + rank_in_list)
    """
    scores: dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _original_score) in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)

    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return fused
