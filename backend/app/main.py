import os

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

app = FastAPI(title="Aaroh AI Backend")

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
    o.strip() for o in os.environ.get("FRONTEND_ORIGINS", "").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

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