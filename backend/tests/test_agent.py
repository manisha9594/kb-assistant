from app.agent.graph import run_agent


def test_retrieve_route_returns_cited_document_sources(indexed):
    result = run_agent("How many PTO days can I carry over?", thread_id="t1")
    assert result["route"] == "retrieve"
    assert result["sources"] and all(s["kind"] == "document" for s in result["sources"])
    assert "[1]" in result["answer"]


def test_web_route_for_current_events(indexed):
    result = run_agent("What is the latest news about AI regulation?", thread_id="t2")
    assert result["route"] == "web_search"
    assert result["sources"][0]["kind"] == "web"


def test_clarify_route_for_vague_question():
    result = run_agent("policy?", thread_id="t3")
    assert result["route"] == "clarify"
    assert result["sources"] == []
    assert result["answer"].endswith("?")


def test_falls_back_to_web_when_kb_is_empty():
    result = run_agent("What is the travel meal allowance?", thread_id="t4")
    assert result["route"] == "retrieve"
    assert result["fell_back"] is True
    assert result["sources"][0]["kind"] == "web"


def test_conversation_memory_persists_per_thread(indexed):
    from app.agent.graph import get_graph

    run_agent("How many PTO days do I get?", thread_id="mem")
    run_agent("And how many carry over?", thread_id="mem")
    state = get_graph().get_state({"configurable": {"thread_id": "mem"}}).values
    assert len(state["messages"]) == 4
