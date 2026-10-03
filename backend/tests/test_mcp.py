import mcp_server


def test_mcp_tools(indexed):
    assert {d["filename"] for d in mcp_server.list_documents()} >= {"employee_handbook.pdf"}
    hits = mcp_server.search_documents("multi-factor authentication", k=3)
    assert len(hits) == 3 and {"source", "page", "score", "text"} <= set(hits[0])
    result = mcp_server.ask_knowledge_base("What is the meal allowance when traveling?")
    assert result["route"] == "retrieve" and result["sources"]


async def test_mcp_registers_tools():
    tools = {t.name for t in await mcp_server.mcp.list_tools()}
    assert tools == {"list_documents", "search_documents", "ask_knowledge_base"}
