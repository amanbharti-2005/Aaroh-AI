"""
app/routers/report_generate.py
 
Actually calls Report generation and saves it, using the Report
model/table. This is what the frontend's "Re-analyze" button on the
Project Health page should hit.
 
Separate file from app/routers/report.py (which only does plain CRUD)
so nothing there gets overwritten — this sits alongside it.
"""
 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
 
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.rag.report_generator import generate_project_report
from app.models.project import Project
from app.models.report import Report
 
router = APIRouter(prefix="/api/reports", tags=["report-generation"])
 
 
@router.post("/generate/{project_id}")
def generate_report_for_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generates the Project Health scores and saves them.

    repo_id is derived from project_id rather than passed in: repo_ingest.py
    indexes each repo under str(project_id), so they're always the same value.
    """
    repo_id = str(project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        result = generate_project_report(repo_id)
    except RuntimeError as e:
        # Missing GROQ_API_KEY — surface as "unavailable", not a 500.
        raise HTTPException(status_code=503, detail=str(e))
 
    # Report model has all 7 score columns — save every one of them.
    # (Previously only 4 were persisted here; code_quality_score,
    # security_score, and performance_score were computed by
    # generate_project_report() and returned to the frontend, but
    # silently dropped on save — so they'd disappear on the next
    # page load even though they briefly showed up after generating.)
    new_report = Report(
        project_id=project_id,
        architecture_score=result.get("architecture_score"),
        scalability_score=result.get("scalability_score"),
        documentation_score=result.get("documentation_score"),
        deployment_readiness_score=result.get("deployment_readiness_score"),
        code_quality_score=result.get("code_quality_score"),
        security_score=result.get("security_score"),
        performance_score=result.get("performance_score"),
        ai_commentary=result.get("ai_commentary"),
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
 
    return {
        "id": new_report.id,
        "project_id": project_id,
        **result,
        "generated_at": new_report.generated_at,
    }
 