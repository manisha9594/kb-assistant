"""FastAPI backend for the knowledge assistant."""
import json
import logging
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage

from app import ingest
from app.agent.graph import get_graph, public_sources, run_agent
from app.config import get_settings
from app.schemas import ChatRequest, ChatResponse, DocumentInfo

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("kb")

app = FastAPI(title="Knowledge Assistant", version="1.0.0",
              description="Chat with your company's documents. Answers cite their sources.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    s = get_settings()
    return {"status": "ok", "provider": s.llm_provider, "web_search": s.web_enabled}


@app.post("/api/documents", response_model=DocumentInfo, status_code=201)
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    limit = get_settings().max_upload_mb
    if len(data) > limit * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {limit} MB.")
    try:
        result = ingest.ingest(data, file.filename or "upload")
    except ingest.IngestionError as exc:
        raise HTTPException(422, str(exc)) from exc
    log.info("Indexed %s (%d chunks)", result["filename"], result["chunks"])
    return result


@app.get("/api/documents", response_model=list[DocumentInfo])
def documents():
    return ingest.list_documents()


@app.delete("/api/documents/{filename}")
def delete(filename: str):
    if not (removed := ingest.delete_document(filename)):
        raise HTTPException(404, f"'{filename}' is not indexed.")
    return {"filename": filename, "chunks_removed": removed}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return run_agent(req.message, req.thread_id)


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat/stream")
def chat_stream(req: ChatRequest):
    """SSE events: route -> sources -> token* -> done (or error)."""
    config = {"configurable": {"thread_id": req.thread_id}}
    inputs = {"messages": [HumanMessage(content=req.message)]}

    def events():
        try:
            for mode, chunk in get_graph().stream(inputs, config, stream_mode=["updates", "messages"]):
                if mode == "messages":
                    # Token chunks from the answering LLM, plus messages that nodes write
                    # directly (clarifying question, "not found" reply).
                    msg, meta = chunk
                    if meta.get("langgraph_node") in ("generate", "clarify") and msg.content:
                        yield _sse("token", msg.content)
                    continue
                for node, update in chunk.items():
                    if node == "route":
                        yield _sse("route", {"route": update["route"], "reason": update["route_reason"]})
                    elif node in ("retrieve", "web_search"):
                        yield _sse("sources", {"fell_back": update.get("fell_back", False),
                                               "sources": public_sources(update["sources"])})
            yield _sse("done", None)
        except Exception:
            log.exception("Chat failed")
            yield _sse("error", "Something went wrong while answering. Check the server logs.")

    return StreamingResponse(events(), media_type="text/event-stream")


# Serve the built React app (frontend/dist) when it exists, e.g. in Docker.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        return FileResponse(DIST / "index.html")
