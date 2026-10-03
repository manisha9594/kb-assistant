import pytest


@pytest.fixture(autouse=True, scope="session")
def offline(tmp_path_factory):
    """Fake LLM, embeddings, and web search, plus a throwaway vector store."""
    mp = pytest.MonkeyPatch()
    mp.setenv("LLM_PROVIDER", "fake")
    mp.setenv("CHROMA_DIR", str(tmp_path_factory.mktemp("chroma")))
    mp.setenv("MIN_RELEVANCE", "-1")  # fake embeddings produce arbitrary scores
    yield
    mp.undo()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture
def indexed(client):
    from pathlib import Path

    samples = Path(__file__).parents[2] / "samples"
    for f in samples.iterdir():
        assert client.post("/api/documents", files={"file": (f.name, f.read_bytes())}).status_code == 201
    yield
    for f in samples.iterdir():
        client.delete(f"/api/documents/{f.name}")
