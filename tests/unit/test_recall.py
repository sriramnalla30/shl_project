from eval.recall import recall_at_k, mean_recall_at_k


def test_perfect_recall():
    pred = ["https://x/a", "https://x/b"]
    gt = ["https://x/a", "https://x/b"]
    assert recall_at_k(pred, gt) == 1.0


def test_partial_recall():
    pred = ["https://x/a", "https://x/c"]
    gt = ["https://x/a", "https://x/b"]
    assert recall_at_k(pred, gt) == 0.5


def test_trailing_slash_normalization():
    assert recall_at_k(["https://x/a/"], ["https://x/a"]) == 1.0


def test_mean_recall():
    assert mean_recall_at_k([(["a"], ["a"]), (["x"], ["a", "b"])]) == 0.5
