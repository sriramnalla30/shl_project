from app.retrieval.filters import apply_hard_filters


def test_test_type_filter():
    cands = [
        {"id": 1, "test_type_codes": ["K"], "duration_minutes": 10},
        {"id": 2, "test_type_codes": ["P"], "duration_minutes": 10},
    ]
    out = apply_hard_filters(cands, test_types_wanted=["P"], duration_max_min=None)
    assert [c["id"] for c in out] == [2]


def test_duration_filter():
    cands = [
        {"id": 1, "test_type_codes": ["K"], "duration_minutes": 60},
        {"id": 2, "test_type_codes": ["K"], "duration_minutes": 10},
    ]
    out = apply_hard_filters(cands, test_types_wanted=None, duration_max_min=20)
    assert [c["id"] for c in out] == [2]
