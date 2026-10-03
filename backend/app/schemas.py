from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    thread_id: str = Field("default", max_length=100)


class Source(BaseModel):
    id: int
    kind: Literal["document", "web"]
    source: str
    page: int | None = None
    url: str | None = None
    snippet: str
    score: float | None = None


class ChatResponse(BaseModel):
    answer: str
    route: Literal["retrieve", "web_search", "clarify"]
    route_reason: str
    fell_back: bool
    sources: list[Source]


class DocumentInfo(BaseModel):
    filename: str
    pages: int
    chunks: int
