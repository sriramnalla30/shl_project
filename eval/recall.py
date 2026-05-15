"""
Recall@K computation — compares recommended URLs against ground-truth URLs.
"""
from __future__ import annotations


def recall_at_k(predicted_urls: list[str], ground_truth_urls: list[str], k: int = 10) -> float:
    """
    Compute Recall@K: fraction of ground-truth URLs present in top-K predictions.

    Args:
        predicted_urls: List of predicted URLs (order matters for top-K truncation)
        ground_truth_urls: List of ground-truth URLs
        k: Cutoff for predictions

    Returns:
        Recall score between 0.0 and 1.0
    """
    if not ground_truth_urls:
        return 1.0  # No ground truth = vacuously correct

    pred_set = set(url.rstrip("/") for url in predicted_urls[:k])
    gt_set = set(url.rstrip("/") for url in ground_truth_urls)

    if not gt_set:
        return 1.0

    hits = len(pred_set & gt_set)
    return hits / len(gt_set)


def mean_recall_at_k(results: list[tuple[list[str], list[str]]], k: int = 10) -> float:
    """
    Compute mean Recall@K across multiple query results.

    Args:
        results: List of (predicted_urls, ground_truth_urls) tuples
        k: Cutoff

    Returns:
        Mean recall score
    """
    if not results:
        return 0.0
    scores = [recall_at_k(pred, gt, k) for pred, gt in results]
    return sum(scores) / len(scores)
