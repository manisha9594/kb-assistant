from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

Route = Literal["retrieve", "web_search", "clarify"]


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]  # full conversation (persisted per thread)
    question: str          # standalone version of the latest user question
    route: Route
    route_reason: str
    clarifying_question: str
    sources: list[dict]    # retrieved chunks or web results, numbered for citation
    fell_back: bool        # True when retrieval found nothing and the agent searched the web


class RouteDecision(BaseModel):
    """Structured output the router LLM must return."""

    route: Route = Field(description="Where to look for the answer.")
    reason: str = Field(description="One short sentence explaining the choice.")
    clarifying_question: str | None = Field(
        default=None, description="Only when route is 'clarify': the question to ask the user."
    )
