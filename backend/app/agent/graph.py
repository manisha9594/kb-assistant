"""LangGraph agent: condense -> route -> (retrieve | web_search | clarify) -> generate.

            +--> retrieve --(no relevant chunks & web enabled)--> web_search --+
condense -> route --> web_search ----------------------------------------------+--> generate
            +--> clarify --> END
"""
from functools import lru_cache

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import AgentState
from app.config import get_settings


def _after_route(state: AgentState) -> str:
    return state["route"]


def _after_retrieve(state: AgentState) -> str:
    if not state.get("sources") and get_settings().web_enabled:
        return "web_search"
    return "generate"


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("condense", nodes.condense)
    g.add_node("route", nodes.route)
    g.add_node("retrieve", nodes.retrieve)
    g.add_node("web_search", nodes.web_search)
    g.add_node("clarify", nodes.clarify)
    g.add_node("generate", nodes.generate)

    g.add_edge(START, "condense")
    g.add_edge("condense", "route")
    g.add_conditional_edges("route", _after_route, ["retrieve", "web_search", "clarify"])
    g.add_conditional_edges("retrieve", _after_retrieve, ["web_search", "generate"])
    g.add_edge("web_search", "generate")
    g.add_edge("clarify", END)
    g.add_edge("generate", END)
    # MemorySaver keeps conversations in memory per thread_id.
    # For production, swap in langgraph's Postgres or Redis checkpointer.
    return g.compile(checkpointer=checkpointer or MemorySaver())


@lru_cache
def get_graph():
    return build_graph()


def run_agent(question: str, thread_id: str = "default") -> dict:
    """Run the agent to completion. Used by the JSON endpoint, evals, and the MCP server."""
    config = {"configurable": {"thread_id": thread_id}}
    state = get_graph().invoke({"messages": [HumanMessage(content=question)]}, config)
    return {
        "answer": state["messages"][-1].content,
        "route": state["route"],
        "route_reason": state.get("route_reason", ""),
        "fell_back": state.get("fell_back", False),
        "sources": public_sources(state.get("sources", [])),
    }


def public_sources(sources: list[dict]) -> list[dict]:
    return [
        {
            "id": s["id"],
            "kind": s["kind"],
            "source": s["source"],
            "page": s.get("page") or None,
            "url": s.get("url"),
            "snippet": s["text"][:400],
            "score": s.get("score"),
        }
        for s in sources
    ]
