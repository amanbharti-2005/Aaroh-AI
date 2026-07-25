"""
app/routers/roadmap_generate.py

Generates a roadmap for a project that already has an ingested repository,
then persists the milestones to the Roadmap table.

This is what the frontend's Upload Project page calls as step 3 for GitHub
and ZIP uploads (ENDPOINTS.roadmap.generate -> POST /api/roadmap/generate/{id}),
and what the Roadmap page's retry path should hit. The router was referenced
from main.py but the module never existed, which is what broke the ASGI app
load in commit add3654 — it was removed there rather than implemented.

Separate from routers/roadmap.py (plain CRUD) and routers/agents.py
(idea-based analysis for text/voice projects), which both stay untouched.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.agents.graph import run_project_analysis
from app.models.project import Project
from app.models.roadmap import Roadmap

router = APIRouter(prefix="/api/roadmap", tags=["roadmap-generation"])


@router.post("/generate/{project_id}")
def generate_roadmap(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # For a repo upload there's usually no typed-out idea description, so fall
    # back to the title plus whatever source was given. run_project_analysis()
    # grounds itself in Engineering RAG either way.
    description = project.idea_description or (
        f"Repository at {project.github_url}" if project.github_url
        else f"Uploaded codebase {project.zip_filename or project.title}"
    )

    try:
        result = run_project_analysis(
            project_id=project.id,
            title=project.title,
            idea_description=description,
            input_type=project.input_type,
        )
    except RuntimeError as e:
        # _get_model() raises RuntimeError when GROQ_API_KEY is missing —
        # surface that as a clear 503 rather than a generic 500.
        raise HTTPException(status_code=503, detail=str(e))

    # Regenerating replaces the previous roadmap rather than appending a
    # second copy of every milestone.
    db.query(Roadmap).filter(Roadmap.project_id == project_id).delete()

    milestones = result.get("milestones") or []
    for i, m in enumerate(milestones, start=1):
        db.add(Roadmap(
            project_id=project_id,
            milestone_title=m["title"],
            milestone_description=m.get("description"),
            order_index=m.get("order", i),
        ))

    db.commit()

    return {
        "status": "success",
        "project_id": project_id,
        "milestones_created": len(milestones),
    }
