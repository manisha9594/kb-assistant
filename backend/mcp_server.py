"""MCP server exposing the knowledge base as tools for any MCP client
(Claude Desktop, Claude Code, Cursor, or your own agents).

Run:  python mcp_server.py          (stdio transport)
"""
from mcp.server import MCPServer

from app import ingest
from app.agent.graph import run_agent

mcp = MCPServer(
    name="company-knowledge-base",
    instructions=(
        "Search and query the company's internal documents. Use search_documents for raw "
        "passages with citations, or ask_knowledge_base for a complete cited answer."
    ),
)


@mcp.tool()
def list_documents() -> list[dict]:
    """List every document in the knowledge base with its page and chunk counts."""
    return ingest.list_documents()


@mcp.tool()
def search_documents(query: str, k: int = 5) -> list[dict]:
    """Semantic search over the company documents.

    Returns the most relevant passages with source file, page, and relevance score.
    """
    return [
        {"source": r["source"], "page": r["page"] or None, "score": r["score"], "text": r["text"]}
        for r in ingest.search(query, k=k)
    ]


@mcp.tool()
def ask_knowledge_base(question: str) -> dict:
    """Ask a question and get a complete answer with numbered citations.

    The agent decides whether to use the documents, the web, or ask for clarification.
    """
    result = run_agent(question, thread_id="mcp")
    return {
        "answer": result["answer"],
        "route": result["route"],
        "sources": [
            {"id": s["id"], "source": s["source"], "page": s["page"], "url": s["url"]}
            for s in result["sources"]
        ],
    }


if __name__ == "__main__":
    mcp.run("stdio")
