"""Graph nodes. Each takes the current state and returns the fields it updates."""
import re

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app import ingest
from app.agent import prompts
from app.agent.state import AgentState, RouteDecision
from app.config import get_settings
from app.providers import get_llm, is_fake
from app.websearch import search_web


def _latest_user_text(state: AgentState) -> str:
    return next(m.content for m in reversed(state["messages"]) if isinstance(m, HumanMessage))


def condense(state: AgentState) -> dict:
    """Turn follow-ups like 'what about contractors?' into standalone questions."""
    question = _latest_user_text(state)
    history = state["messages"][:-1][-6:]
    if not history or is_fake():
        return {"question": question}
    transcript = "\n".join(f"{m.type}: {m.content}" for m in history)
    rewritten = get_llm().invoke(prompts.CONDENSE.format(history=transcript, question=question))
    return {"question": rewritten.content.strip() or question}


_WEB_HINTS = re.compile(r"\b(latest|news|today|current|this (week|month|year)|stock price|weather)\b", re.I)


def _heuristic_route(question: str) -> RouteDecision:
    """Offline router used with the fake provider, so tests run without an API key."""
    if len(question.split()) < 3:
        return RouteDecision(route="clarify", reason="Question is too short to answer.",
                              clarifying_question="Could you add more detail about what you're looking for?")
    if _WEB_HINTS.search(question):
        return RouteDecision(route="web_search", reason="Question asks for current public information.")
    return RouteDecision(route="retrieve", reason="Question is about company knowledge.")


def route(state: AgentState) -> dict:
    s = get_settings()
    question = state["question"]
    if is_fake():
        decision = _heuristic_route(question)
    else:
        docs = ", ".join(d["filename"] for d in ingest.list_documents()) or "none"
        router = get_llm().with_structured_output(RouteDecision)
        decision = router.invoke(
            prompts.ROUTER.format(documents=docs, web_enabled=s.web_enabled, question=question)
        )
    if decision.route == "web_search" and not s.web_enabled:
        decision = RouteDecision(route="retrieve", reason="Web search is disabled; using documents.")
    if decision.route == "clarify" and not decision.clarifying_question:
        decision.clarifying_question = "Could you be more specific about what you need?"
    return {
        "route": decision.route,
        "route_reason": decision.reason,
        "clarifying_question": decision.clarifying_question or "",
        "fell_back": False,
    }


def _numbered(items: list[dict]) -> list[dict]:
    return [{**item, "id": i} for i, item in enumerate(items, start=1)]


def retrieve(state: AgentState) -> dict:
    return {"sources": _numbered(ingest.search(state["question"]))}


def web_search(state: AgentState) -> dict:
    fell_back = state.get("route") == "retrieve"
    return {"sources": _numbered(search_web(state["question"])), "fell_back": fell_back}


def clarify(state: AgentState) -> dict:
    return {"messages": [AIMessage(content=state["clarifying_question"])], "sources": []}


def _format_context(sources: list[dict]) -> str:
    blocks = []
    for s in sources:
        where = s.get("url") or (f"page {s['page']}" if s.get("page") else "")
        blocks.append(f"[{s['id']}] {s['source']} {f'({where})' if where else ''}\n{s['text']}")
    return "\n\n".join(blocks)


def generate(state: AgentState) -> dict:
    sources = state.get("sources", [])
    if not sources:
        return {"messages": [AIMessage(content=(
            "I couldn't find that in the uploaded documents. Try rephrasing, "
            "or upload the document that covers this topic."
        ))]}
    web_note = (
        "\nNote: the company documents had no match, so these sources are web results. "
        "Say so briefly at the start of your answer.\n" if state.get("fell_back") else ""
    )
    system = prompts.ANSWER.format(context=_format_context(sources), web_note=web_note)
    history = [m for m in state["messages"][:-1] if m.type in ("human", "ai")][-6:]
    reply = get_llm().invoke(
        [SystemMessage(content=system), *history, HumanMessage(content=state["question"])]
    )
    # Return the model's own message (same id) so streaming clients don't receive it twice.
    return {"messages": [reply]}
