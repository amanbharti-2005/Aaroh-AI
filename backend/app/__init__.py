"""
Loads backend/.env as soon as anything under `app.` is imported.

app/core/rag/generate.py and web_rag.py read their keys from os.environ.
Those values only reached os.environ via app/core/config.py, which is
imported by app.core.database — so the FastAPI app was fine, but any script
or test that imported a RAG module directly (without touching the database
layer) saw no GROQ_API_KEY and failed with "GROQ_API_KEY is not set" despite
a perfectly good key sitting in backend/.env. Doing it here makes the env
available regardless of which module gets imported first.
"""

import os

from dotenv import load_dotenv

load_dotenv(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
)
