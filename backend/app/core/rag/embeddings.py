import os

# Current GA text embedding model for langchain-google-genai 2.1.12 (see the
# GoogleGenerativeAIEmbeddings docstring in that package). Replaced local
# sentence-transformers/torch, which OOM-crashed on Render's 512MB free tier
# the first time anything actually called get_embeddings().
EMBEDDING_MODEL_NAME = "gemini-embedding-001"

_embeddings = None


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        _embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            google_api_key=os.environ.get("GEMINI_API_KEY"),
        )
    return _embeddings
