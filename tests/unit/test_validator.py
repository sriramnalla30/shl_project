import pytest
from app.agent.nodes.validator import set_url_allowlist, run


@pytest.mark.asyncio
async def test_validator_rejects_off_catalog_url():
    set_url_allowlist(frozenset(["https://www.shl.com/legit"]))
    state = {
        "intent": "recommend",
        "draft": {
            "reply": "ok",
            "recommendations": [{"name": "x", "url": "https://evil.com/x", "test_type": "K"}],
            "end_of_conversation": True,
        },
        "retry_count": 0,
    }
    result = await run(state)
    assert result["validation_errors"]
    assert any("off_catalog_url" in e for e in result["validation_errors"])


@pytest.mark.asyncio
async def test_validator_accepts_valid_draft():
    set_url_allowlist(frozenset(["https://www.shl.com/legit"]))
    state = {
        "intent": "recommend",
        "draft": {
            "reply": "ok",
            "recommendations": [{"name": "x", "url": "https://www.shl.com/legit", "test_type": "K"}],
            "end_of_conversation": True,
        },
        "retry_count": 0,
    }
    result = await run(state)
    assert result["validation_errors"] == []
