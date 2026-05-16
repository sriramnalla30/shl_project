from app.schemas import ChatRequest, ChatResponse, Recommendation
import pytest


def test_chat_response_max_10_recs():
    recs = [Recommendation(name=f"n{i}", url="https://x", test_type="K") for i in range(10)]
    ChatResponse(reply="ok", recommendations=recs)  # should pass
    with pytest.raises(Exception):
        ChatResponse(reply="ok", recommendations=recs + [recs[0]])


def test_chat_request_requires_messages():
    with pytest.raises(Exception):
        ChatRequest(messages=[])
