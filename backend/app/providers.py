"""Factories for the LLM, embeddings, and vector store.

Swapping OpenAI for Azure OpenAI, Bedrock, or Ollama only requires changing this file.
"""
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import get_settings

FAKE_ANSWER = "Based on the documents, here is the answer [1]."


def is_fake() -> bool:
    return get_settings().llm_provider == "fake"


@lru_cache
def get_embeddings() -> Embeddings:
    s = get_settings()
    if is_fake():
        return DeterministicFakeEmbedding(size=256)
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(model=s.embedding_model, api_key=s.openai_api_key)


@lru_cache
def get_llm() -> BaseChatModel:
    s = get_settings()
    if is_fake():
        return FakeListChatModel(responses=[FAKE_ANSWER])
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=s.chat_model, temperature=0, api_key=s.openai_api_key, streaming=True)


@lru_cache
def get_vectorstore() -> Chroma:
    s = get_settings()
    return Chroma(
        collection_name=s.collection_name,
        embedding_function=get_embeddings(),
        persist_directory=s.chroma_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )
