"""
Request/Response Pydantic models — the contract between client and server.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class Message(BaseModel):
    """A single conversation message."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Incoming chat request — full conversation history."""
    messages: list[Message] = Field(..., min_length=1, max_length=50)


class Recommendation(BaseModel):
    """A single recommended assessment."""
    name: str
    url: str  # Using str instead of HttpUrl for byte-identical comparison
    test_type: str


class ChatResponse(BaseModel):
    """The agent's response."""
    reply: str
    recommendations: list[Recommendation] = Field(default_factory=list, max_length=10)
    end_of_conversation: bool = False
