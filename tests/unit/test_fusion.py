from app.retrieval.fusion import rrf


def test_rrf_basic():
    bm = [(1, 0.9), (2, 0.5), (3, 0.1)]
    de = [(2, 0.8), (1, 0.6), (4, 0.2)]
    fused = rrf([bm, de], k=60)
    ids = [doc_id for doc_id, _ in fused]
    assert 1 in ids and 2 in ids
    assert ids[0] in (1, 2)  # one of the top-shared docs wins
