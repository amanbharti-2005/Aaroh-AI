"""
app/core/rag/engineering_rag.py

Engineering RAG: static knowledge base of software engineering best
practices (architecture patterns, tech stacks, deployment, etc).

Two entry points:
- ingest_knowledge_base()          -> run manually / on startup to (re)build the index
- retrieve_engineering_knowledge() -> called by the router (and eventually the
                                       Planner Agent) to fetch relevant chunks
"""
from __future__ import annotations

import os

from app.core.rag.embeddings import get_embeddings

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_BASE_DIR = os.path.join(_THIS_DIR, "knowledge_base")
CHROMA_DB_DIR = os.path.join(_THIS_DIR, "chroma_db", "engineering")
COLLECTION_NAME = "engineering_rag"

_vector_store = None


def ingest_knowledge_base():
    """Rebuild the vector store from every .md file in knowledge_base/.
    Run this manually whenever you add/change docs:
        python -m app.core.rag.engineering_rag
    """
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma

    from app.core.rag.embedding_retry import EMBED_BATCH_SIZE, retry_embedding_call

    loader = DirectoryLoader(
        KNOWLEDGE_BASE_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    if not docs:
        print(f"No .md files found in {KNOWLEDGE_BASE_DIR}")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DB_DIR,
    )

    @retry_embedding_call
    def _add_documents_batch(batch):
        store.add_documents(batch)

    # Submitted in Gemini-batch-sized groups, each independently retried, so
    # a 429 on one group doesn't throw away embeddings already persisted for
    # earlier groups (see embedding_retry.py for why).
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        _add_documents_batch(chunks[start : start + EMBED_BATCH_SIZE])

    print(f"Ingested {len(docs)} docs / {len(chunks)} chunks into {CHROMA_DB_DIR}")


def _get_vector_store():
    global _vector_store
    if _vector_store is None:
        from langchain_community.vectorstores import Chroma

        _vector_store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=get_embeddings(),
            persist_directory=CHROMA_DB_DIR,
        )
    return _vector_store


def retrieve_engineering_knowledge(query: str, top_k: int = 4) -> list[dict]:
    """
    THIS is the function the router (and eventually the Planner Agent /
    LangGraph tool) calls. Keep this signature stable once agreed with
    your teammate.

    Returns a list of {"content": str, "source": str, "score": float}.
    Empty list if nothing relevant found — caller should handle that
    gracefully rather than erroring.
    """
    store = _get_vector_store()
    results = store.similarity_search_with_relevance_scores(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "score": round(score, 3),
        }
        for doc, score in results
    ]


if __name__ == "__main__":
    ingest_knowledge_base()