import json
import os
import re

from groq import Groq

from app.core.rag.engineering_rag import retrieve_engineering_knowledge
from app.core.rag.repository_rag import retrieve_repository_knowledge
from app.core.rag.web_rag import search_web

# Groq's free-tier daily token budget is PER MODEL
# (https://console.groq.com/docs/rate-limits):
#
#   llama-3.3-70b-versatile   100K tokens/day  — better prose
#   llama-3.1-8b-instant      500K tokens/day  — weaker, but 5x the budget
#
# So we split by what each caller actually needs. Chat answers are read by a
# human, so they get the 70b. The agents that only emit structured JSON from
# code we've already retrieved (architecture graph, health report, project
# analysis) get the 8b — they're where nearly all the token volume goes, and
# they don't benefit much from the bigger model. Separate buckets mean the
# two features can't starve each other.
CHAT_MODEL = "llama-3.3-70b-versatile"
STRUCTURED_MODEL = "llama-3.1-8b-instant"

MODEL_NAME = CHAT_MODEL  # default for callers that don't specify one


def _groq_api_key() -> str:
    """
    Read the key at call time, not import time. As a module-level constant
    this captured os.environ before app.core.config had a chance to load
    backend/.env, so a perfectly good key in .env still produced
    "GROQ_API_KEY is not set".
    """
    return os.environ.get("GROQ_API_KEY", "")

_models: dict = {}


class _GroqResponse:
    """Mimics Gemini's response.text shape so every ask_*() function
    below stays unchanged — they all just do response.text."""
    def __init__(self, text):
        self.text = text


class _GroqModel:
    """Mimics Gemini's model.generate_content(prompt) shape for the
    same reason — a drop-in replacement, not a rewrite."""
    def __init__(self, client, model_name, fallback_model=None):
        self.client = client
        self.model_name = model_name
        self.fallback_model = fallback_model

    def _complete(self, model, prompt):
        completion = self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return _GroqResponse(completion.choices[0].message.content)

    def generate_content(self, prompt):
        try:
            return self._complete(self.model_name, prompt)
        except Exception as e:
            # Daily budgets are per-model, so when the preferred model is out
            # of tokens the other one usually still has plenty. Retrying there
            # keeps the app answering (a bit less eloquently) instead of
            # failing outright — which matters because these limits are easy
            # to hit on the free tier.
            if self.fallback_model and _is_rate_limit(e):
                return self._complete(self.fallback_model, prompt)
            raise


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    return "rate_limit" in text or "429" in text or "413" in text


def _get_model(model_name: str = MODEL_NAME):
    """
    Returns a model wrapper for `model_name`, cached per name so each model
    reuses one client. Callers that produce structured JSON should pass
    STRUCTURED_MODEL; chat callers get CHAT_MODEL by default.
    """
    if model_name not in _models:
        api_key = _groq_api_key()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your backend/.env file:\n"
                "GROQ_API_KEY=your_key_here\n"
                "Get a free key at https://console.groq.com/keys"
            )
        client = Groq(api_key=api_key)
        fallback = STRUCTURED_MODEL if model_name == CHAT_MODEL else CHAT_MODEL
        _models[model_name] = _GroqModel(client, model_name, fallback_model=fallback)
    return _models[model_name]


def extract_json(text: str):
    """
    Pulls a JSON object out of an LLM response, or returns None.

    Every structured-output caller (architecture_agent, report_generator,
    agents/graph) used `re.sub(r"^```json\\s*|\\s*```$", "", text)`, which
    only handles a fence spelled exactly ```json. A plain ``` fence, or one
    sentence of preamble before the JSON, made json.loads() raise and the
    caller silently fall back to an empty graph / neutral 50-scores — so an
    intermittent formatting choice by the model looked to the user like
    "analysis found nothing" with no way to tell the difference.

    Strategy: strip any fence, try to parse; if that fails, fall back to the
    outermost {...} span in the text.
    """
    if not text:
        return None

    cleaned = text.strip()
    # Remove a leading ``` or ```json fence and any trailing fence.
    cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fall back to the widest {...} span — handles prose wrapped around JSON.
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


# --- Context size budget -----------------------------------------------
#
# retrieve_repository_knowledge() returns WHOLE FILES, not small chunks —
# that's the point of the parent-document design. Pasting them in verbatim
# meant a single chat message shipped ~32,000 tokens, and Groq's free tier
# caps at 12,000 tokens/minute, so every repo-backed question died with
# "413 Request too large" and surfaced in the UI as "Failed to fetch".
#
# report_generator.py already trimmed to 500 chars/file and
# architecture_agent.py to 800; only the chat paths sent untrimmed files.
# ~4 chars per token, so 18,000 chars ≈ 4.5k tokens of context, leaving
# room for the prompt scaffolding, the question, and the completion.
MAX_CHARS_PER_SOURCE = 2_500
MAX_CONTEXT_CHARS = 18_000


def _format_context(chunks: list[dict], label: str = "Source") -> str:
    """
    Renders retrieved chunks into prompt context, truncating each source and
    stopping once the total budget is spent. Truncation is marked inline so
    the model (and anyone reading logs) can tell content was cut rather than
    silently assuming it saw a whole file.
    """
    parts, used = [], 0

    for c in chunks:
        body = c.get("content", "") or ""
        if len(body) > MAX_CHARS_PER_SOURCE:
            body = body[:MAX_CHARS_PER_SOURCE] + "\n... [truncated]"

        entry = f"[{label}: {c.get('source', 'unknown')}]\n{body}"
        if used + len(entry) > MAX_CONTEXT_CHARS:
            remaining = MAX_CONTEXT_CHARS - used
            if remaining > 500:          # only include a partial if it's useful
                parts.append(entry[:remaining] + "\n... [truncated]")
            break

        parts.append(entry)
        used += len(entry)

    return "\n\n".join(parts)


def _build_prompt(question: str, chunks: list[dict]) -> str:
    if not chunks:
        context = "No specific engineering knowledge was found for this question."
    else:
        context = _format_context(chunks, "Source")

    return f"""You are Aaroh AI, a personalized AI project mentor for students and developers.

Answer the user's question using ONLY the retrieved engineering knowledge below.
If the retrieved knowledge doesn't cover the question, say so honestly instead
of making something up. Keep the tone encouraging and practical, like a
mentor talking to a student, not a textbook.

Retrieved knowledge:
{context}

User question: {question}

Your answer:"""


def ask_mentor(question: str, top_k: int = 4) -> dict:
    """
    THIS is the full RAG loop in one function: retrieve -> prompt -> generate.

    Returns:
        {
            "answer": "...",              # Gemini's generated response
            "sources": ["file1.md", ...], # which docs it drew from
            "chunks_used": [...]          # the raw chunks, for debugging/transparency
        }
    """
    chunks = retrieve_engineering_knowledge(question, top_k=top_k)
    prompt = _build_prompt(question, chunks)

    model = _get_model()
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "sources": list({c["source"] for c in chunks}),
        "chunks_used": chunks,
    }


def ask_about_repo(question: str, repo_id: str, top_k: int = 4) -> dict:
    """
    Same idea as ask_mentor(), but for questions about a user's
    uploaded code instead of general engineering knowledge.
    e.g. "explain this auth module", "review my backend"
    """
    chunks = retrieve_repository_knowledge(question, repo_id, top_k=top_k)

    if not chunks:
        context = "No relevant code was found in this repository for this question."
    else:
        context = _format_context(chunks, "File")

    prompt = f"""You are Aaroh AI, reviewing a student's uploaded codebase.

Answer the user's question using ONLY the code below. Reference specific
files and functions by name where relevant. If something looks like a
bug or bad practice, mention it constructively, like a mentor would.

Code from their repository:
{context}

User question: {question}

Your answer:"""

    model = _get_model()
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "sources": list({c["source"] for c in chunks}),
        "chunks_used": chunks,
    }


def ask_hybrid(question: str, repo_id: str | None = None, top_k: int = 3) -> dict:
    """
    THE full hybrid version matching the architecture diagram: pulls
    from BOTH Engineering RAG (general best practices) and Repository
    RAG (their actual code, if repo_id is given), merges both sets of
    context, and asks Gemini to answer using whichever is relevant.

    This is the simplest possible stand-in for what the Planner Agent
    will eventually do with smarter query reformulation — here it just
    sends the same question to both retrievers directly.
    """
    engineering_chunks = retrieve_engineering_knowledge(question, top_k=top_k)
    repo_chunks = retrieve_repository_knowledge(question, repo_id, top_k=top_k) if repo_id else []

    context_parts = []
    if engineering_chunks:
        context_parts.append(
            "General engineering knowledge:\n" + _format_context(engineering_chunks, "Source")
        )
    if repo_chunks:
        context_parts.append(
            "Code from their repository:\n" + _format_context(repo_chunks, "File")
        )

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant knowledge found."

    prompt = f"""You are Aaroh AI, a personalized AI project mentor.

Answer using ONLY the retrieved knowledge below — it may include general
engineering best practices, the user's own code, or both. Be specific
about which one you're drawing from when it matters.

Retrieved knowledge:
{context}

User question: {question}

Your answer:"""

    model = _get_model()
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "engineering_sources": list({c["source"] for c in engineering_chunks}),
        "repo_sources": list({c["source"] for c in repo_chunks}),
    }


# Below this local knowledge quality, fall back to web search instead
# of trusting a weak/irrelevant local match. Tune this after watching
# real scores — 0.35 is a reasonable starting point, not a proven number.
WEB_FALLBACK_SCORE_THRESHOLD = 0.35


def ask_mentor_smart(question: str, top_k: int = 4) -> dict:
    """
    Same as ask_mentor(), but falls back to a live web search when local
    Engineering RAG doesn't have good coverage for the question — instead
    of either failing or letting Gemini guess from its own training data.

    This is a SEPARATE function from ask_mentor() on purpose — it doesn't
    replace it. Your teammate's Planner Agent can call whichever one fits
    a given situation; nothing about ask_mentor()'s existing contract changes.

    Returns the same shape as ask_mentor(), plus "used_web": bool so the
    frontend can show something like "answered using web search" for
    transparency.
    """
    chunks = retrieve_engineering_knowledge(question, top_k=top_k)

    best_score = max((c["score"] for c in chunks), default=0)
    used_web = False

    if best_score < WEB_FALLBACK_SCORE_THRESHOLD:
        web_results = search_web(question, max_results=4)
        if web_results:
            used_web = True
            context = _format_context(
                [{"source": f"{r['title']} — {r['source']}", "content": r["content"]}
                 for r in web_results],
                "Source",
            )
            sources = [r["source"] for r in web_results]
        else:
            # Web search also came up empty (or no API key) — fall back
            # to whatever weak local chunks exist rather than nothing.
            context = _format_context(chunks, "Source") or "No relevant knowledge found locally or on the web."
            sources = [c["source"] for c in chunks]
    else:
        context = _format_context(chunks, "Source")
        sources = [c["source"] for c in chunks]

    prompt = f"""You are Aaroh AI, a personalized AI project mentor.

Answer the user's question using ONLY the retrieved knowledge below.
{"This knowledge came from a live web search, not your curated knowledge base — mention that naturally if relevant." if used_web else ""}
If the answer isn't covered, say so honestly.

Retrieved knowledge:
{context}

User question: {question}

Your answer:"""

    model = _get_model()
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "sources": list(set(sources)),
        "used_web": used_web,
    }


def ask_ui_ux_review(question: str, repo_id: str | None = None, top_k: int = 4) -> dict:
    """
    UI/UX-focused reviewer. Pulls UI/UX design guidance from Engineering
    RAG, and (if repo_id is given) the user's actual frontend code from
    Repository RAG, then asks for both written feedback AND a real,
    usable React + Tailwind code sample — not just a description.

    Same pattern as ask_hybrid(), just with a UI/UX-specific prompt.
    """
    guideline_chunks = retrieve_engineering_knowledge(question, top_k=top_k)
    code_chunks = retrieve_repository_knowledge(question, repo_id, top_k=top_k) if repo_id else []

    context_parts = []
    if guideline_chunks:
        context_parts.append(
            "UI/UX design guidelines:\n" + _format_context(guideline_chunks, "Source")
        )
    if code_chunks:
        context_parts.append(
            "User's current frontend code:\n" + _format_context(code_chunks, "File")
        )

    context = "\n\n---\n\n".join(context_parts) if context_parts else "No relevant guidelines or code found."

    prompt = f"""You are Aaroh AI, a UI/UX reviewer for student developers.

Using the guidelines and code below, give the user:
1. Specific, actionable UI/UX feedback (what to improve and why)
2. A real, working React + Tailwind CSS code sample they can use directly —
   not a description of what it should look like, actual working code in a
   code block.

If their own code was provided, base your suggestions on improving THAT
code specifically. If not, suggest a good example component for their
described use case.

Context:
{context}

User's request: {question}

Your response:"""

    model = _get_model()
    response = model.generate_content(prompt)

    return {
        "answer": response.text,
        "guideline_sources": list({c["source"] for c in guideline_chunks}),
        "code_sources": list({c["source"] for c in code_chunks}),
    }