"""
app/routers/architecture.py

Exposes the Architecture Agent over HTTP. Given a project_id, looks
up which repo_id it's tied to, generates the architecture graph, and
returns it for the frontend's diagram renderer.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.agents.architecture_agent import generate_architecture_graph
from app.models.project import Project
from app.models.repo import Repo

router = APIRouter(prefix="/api/architecture", tags=["architecture"])


@router.get("/{project_id}")
def get_architecture(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    repo = db.query(Repo).filter(Repo.project_id == project_id).first()
    if not repo:
        raise HTTPException(
            status_code=404,
            detail="No repository has been ingested for this project yet.",
        )

    # repo_ingest.py calls ingest_repository(local_path, project_id), so the
    # Repository RAG index for this project is keyed by the PROJECT id — not
    # the Repo table's primary key. Passing str(repo.id) here looked up a
    # collection that never exists, so this endpoint always returned an empty
    # graph. mentor.py already keys off str(project_id) the same way.
    graph = generate_architecture_graph(str(project_id))
    return graph