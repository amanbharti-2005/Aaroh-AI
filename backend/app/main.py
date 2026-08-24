import logging
import os
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine, Base
from app.core.security import get_current_user
# Imported for their side effect only: each module registers its table on
# Base.metadata, which create_all() below needs in order to create them.
from app.models import user, project, repo, report, roadmap, chat_message  # noqa: F401
from app.routers import architecture, analytics, project_analysis
#from app.routers import pdf_report
from app.routers import repo_intel_analysis, agents, roadmap_generate

from app.routers import (
    project as project_router,
    auth as auth_router,
    repo as repo_router,
    report as report_router,
    roadmap as roadmap_router,
    roadmap_alias,
    health_alias,
    stubs,
    rag,
    mentor,
    repository_rag,
    repo_ingest,
    report_generate,
)

logger = logging.getLogger("aaroh.startup")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logger.exception("Failed to initialize database schema at startup")
    yield


app = FastAPI(title="Aaroh AI Backend", lifespan=lifespan)

# Origins allowed to call this API from a browser. Local dev ports are always
# allowed; the deployed frontend's URL is added via the FRONTEND_ORIGINS env
# var (comma-separated) so it can change without a code edit. On Render set:
#     FRONTEND_ORIGINS = https://your-app.vercel.app
# "*" can't be combined with allow_credentials=True — browsers reject that
# pairing for credentialed requests — so real origins must be listed.
_default_origins = [
    "http://localhost:5173",   # Vite's default dev port
    "http://127.0.0.1:5173",
    "http://localhost:5174",   # Vite's fallback when 5173 is taken
    "http://127.0.0.1:5174",
]
_extra_origins = [
    o.strip().rstrip("/")
    for o in os.environ.get("FRONTEND_ORIGINS", "").split(",")
    if o.strip()
]


def _vercel_preview_regex(origins: list[str]) -> str | None:
    """
    Vercel gives every preview deployment of a project its own URL
    (project-slug-<hash>-<team>.vercel.app), distinct from the stable
    production URL in FRONTEND_ORIGINS. Auto-allow those too, derived from
    the production origin's slug, so preview deploys aren't CORS-blocked.
    """
    for origin in origins:
        if ".vercel.app" not in origin:
            continue
        host = origin.split("://", 1)[-1]
        slug = host.split(".vercel.app")[0]
        if not slug:
            continue
        escaped = re.escape(slug)
        return rf"^https://({escaped}|{escaped}-[a-z0-9-]+)\.vercel\.app$"
    return None


_frontend_origin_regex = os.environ.get("FRONTEND_ORIGIN_REGEX") or _vercel_preview_regex(
    _extra_origins
)

print(
    f"[CORS] exact origins: {_default_origins + _extra_origins} | "
    f"regex: {_frontend_origin_regex}"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_origin_regex=_frontend_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(project_router.router)
app.include_router(auth_router.router)
app.include_router(repo_router.router)
app.include_router(report_router.router)
app.include_router(roadmap_router.router)
app.include_router(roadmap_alias.router)
app.include_router(health_alias.router)
app.include_router(stubs.router)
app.include_router(rag.router)
app.include_router(mentor.router)
app.include_router(repository_rag.router)
app.include_router(repo_ingest.router)
app.include_router(report_generate.router)
app.include_router(architecture.router)
app.include_router(analytics.router)
app.include_router(project_analysis.router)
#app.include_router(pdf_report.router)
app.include_router(repo_intel_analysis.router)
app.include_router(agents.router)
app.include_router(roadmap_generate.router)


@app.get("/")
def root():
    return {"message": "Aaroh AI Backend is running. Visit /docs for API documentation."}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/db-check")
def db_check():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"database": "connected"}


@app.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {"uid": current_user["uid"], "email": current_user.get("email")}