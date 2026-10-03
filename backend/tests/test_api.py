import json


def parse_sse(raw: str) -> list[tuple[str, object]]:
    events = []
    for block in raw.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_chat_json(client, indexed):
    body = client.post("/api/chat", json={"message": "What is the hotel limit in Boston?"}).json()
    assert body["route"] == "retrieve" and body["sources"]


def test_chat_stream_event_order(client, indexed):
    with client.stream("POST", "/api/chat/stream",
                       json={"message": "What is the password length rule?", "thread_id": "s1"}) as r:
        events = parse_sse("".join(r.iter_text()))
    names = [e for e, _ in events]
    assert names[0] == "route" and names[1] == "sources" and names[-1] == "done"
    assert "token" in names
    answer = "".join(d for e, d in events if e == "token")
    assert "[1]" in answer


def test_chat_stream_clarify(client):
    with client.stream("POST", "/api/chat/stream", json={"message": "help", "thread_id": "s2"}) as r:
        events = parse_sse("".join(r.iter_text()))
    assert events[0][1]["route"] == "clarify"
    assert any(e == "token" for e, _ in events)
