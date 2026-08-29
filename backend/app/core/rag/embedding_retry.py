"""
app/core/rag/embedding_retry.py

Gemini's free tier caps embed_content at 100 requests/minute — and, borne
out by a real ingestion run, that 100 is metered per embedded text, not
per HTTP call: a single 100-item batch_embed_contents() call already uses
up the entire minute's allowance by itself. That means retrying a whole
multi-thousand-chunk add_texts()/from_documents() call from scratch never
converges — every retry restarts at chunk 1 and re-hits the wall at the
same point, since embed_documents() returns nothing on a failed call (no
partial progress to resume from).

So callers must also submit texts in groups no larger than Gemini's own
per-call batch cap (EMBED_BATCH_SIZE) and retry each group independently
— that way a group that succeeds is already persisted in Chroma before
the next one starts, and only the group that actually hit the 429 needs
to wait and retry, not the whole ingestion.

langchain_google_genai wraps every embedding error (whatever the real cause)
into a plain GoogleGenerativeAIError string, so there's no structured
exception type or retry_delay field to catch here — we match on the
message text instead, which is what the API actually gives us.
"""
from __future__ import annotations

import logging
import re

from tenacity import before_sleep_log, retry, retry_if_exception, stop_after_attempt

logger = logging.getLogger("aaroh.rag.embeddings")

# Gemini's own documented max for batch_embed_contents (see the docstring on
# GoogleGenerativeAIEmbeddings.embed_documents in langchain_google_genai) —
# also happens to be the free tier's per-minute request cap, so one group
# is one request and uses the whole minute's budget.
EMBED_BATCH_SIZE = 100

_MAX_ATTEMPTS = 5
_DEFAULT_WAIT_SECONDS = 30
_MAX_WAIT_SECONDS = 60

_RETRY_DELAY_RE = re.compile(r"retry_delay\s*\{\s*seconds:\s*(\d+)")


def _is_rate_limit_error(exc: BaseException) -> bool:
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "quota" in text.lower()


def _wait_seconds(retry_state) -> float:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if exc is not None:
        match = _RETRY_DELAY_RE.search(str(exc))
        if match:
            return float(match.group(1))
    # Gemini didn't hand us a retry_delay (or we couldn't parse it) — fall
    # back to exponential backoff starting at 30s, capped at 60s.
    return min(
        _MAX_WAIT_SECONDS,
        _DEFAULT_WAIT_SECONDS * (2 ** (retry_state.attempt_number - 1)),
    )


# Applied to the small per-group wrapper functions around
# store.add_documents() / vector_store.add_texts() in engineering_rag.py
# and repository_rag.py.
retry_embedding_call = retry(
    retry=retry_if_exception(_is_rate_limit_error),
    stop=stop_after_attempt(_MAX_ATTEMPTS),
    wait=_wait_seconds,
    reraise=True,
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
