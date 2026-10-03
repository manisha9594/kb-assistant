"""Web search via the Tavily API, used when the knowledge base can't answer."""
import httpx

from app.config import get_settings
from app.providers import is_fake


def search_web(query: str) -> list[dict]:
    s = get_settings()
    if is_fake():
        return [{
            "kind": "web",
            "source": "Example web result",
            "url": "https://example.com/result",
            "text": f"Simulated web result for: {query}",
        }]
    if not s.tavily_api_key:
        return []
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": s.tavily_api_key, "query": query, "max_results": s.web_results},
        timeout=20,
    )
    resp.raise_for_status()
    return [
        {"kind": "web", "source": r.get("title") or r["url"], "url": r["url"], "text": r.get("content", "")}
        for r in resp.json().get("results", [])
    ]
