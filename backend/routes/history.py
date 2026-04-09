import re
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Project

router = APIRouter(prefix="/api", tags=["history"])


class ProjectSummary(BaseModel):
    id: int
    name: str
    source_type: str | None
    repo_url: str | None
    created_at: str
    has_module_analysis: bool
    has_risk_map: bool

    class Config:
        from_attributes = True


class ProjectDetail(BaseModel):
    id: int
    name: str
    source_type: str | None
    repo_url: str | None
    code_context: str | None
    analysis_module: str
    analysis_risk: str
    created_at: str

    class Config:
        from_attributes = True


class SaveProjectRequest(BaseModel):
    user_id: int
    name: str
    source_type: str | None = None
    repo_url: str | None = None
    code_context: str | None = None
    analysis_module: str = ""
    analysis_risk: str = ""


@router.get("/history", response_model=list[ProjectSummary])
def get_history(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get all projects for a user, ordered by most recent."""
    projects = (
        db.query(Project)
        .filter_by(user_id=user_id)
        .order_by(Project.created_at.desc())
        .all()
    )
    return [
        ProjectSummary(
            id=p.id,
            name=p.name,
            source_type=p.source_type,
            repo_url=p.repo_url,
            created_at=p.created_at.strftime("%Y-%m-%d %H:%M"),
            has_module_analysis=bool((p.analysis_module or "").strip()),
            has_risk_map=bool((p.analysis_risk or "").strip()),
        )
        for p in projects
    ]


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Load a specific project with legacy <<<SEP>>> split handling."""
    p = db.query(Project).filter_by(id=project_id).first()
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    mod_text = (p.analysis_module or "").strip()
    risk_text = (p.analysis_risk or "").strip()

    # Fix legacy saves where analysis was stored combined
    combined_blob = ""
    if risk_text and "<<<SEP>>>" in risk_text:
        combined_blob = risk_text
    elif mod_text and "<<<SEP>>>" in mod_text:
        combined_blob = mod_text
    elif mod_text and not risk_text and "RISK MAP" in mod_text.upper():
        combined_blob = mod_text
    elif risk_text and not mod_text and "MODULE ANALYSIS" in risk_text.upper():
        combined_blob = risk_text

    if combined_blob:
        if "<<<SEP>>>" in combined_blob:
            p1, p2 = combined_blob.split("<<<SEP>>>", 1)
            mod_text, risk_text = p1.strip(), p2.strip()
        else:
            split_match = re.split(
                r'(?:\n##\s*(?:(?:2\.)?\s*RISK MAP).*|\n#\s*(?:(?:2\.)?\s*RISK MAP).*)',
                combined_blob, 1, flags=re.IGNORECASE,
            )
            if len(split_match) == 2:
                mod_text = split_match[0].strip()
                risk_text = "## RISK MAP\n" + split_match[1].strip()

        # Persist the fix
        try:
            p.analysis_module = mod_text
            p.analysis_risk = risk_text
            db.add(p)
            db.commit()
        except Exception:
            pass

    return ProjectDetail(
        id=p.id,
        name=p.name,
        source_type=p.source_type,
        repo_url=p.repo_url,
        code_context=p.code_context,
        analysis_module=mod_text,
        analysis_risk=risk_text,
        created_at=p.created_at.strftime("%Y-%m-%d %H:%M"),
    )


class SaveResponse(BaseModel):
    success: bool
    message: str
    project_id: int | None = None


@router.post("/projects", response_model=SaveResponse)
def save_project(req: SaveProjectRequest, db: Session = Depends(get_db)):
    """Save a new project."""
    try:
        new_p = Project(
            user_id=req.user_id,
            name=req.name,
            source_type=req.source_type,
            repo_url=req.repo_url,
            code_context=req.code_context,
            analysis_module=req.analysis_module,
            analysis_risk=req.analysis_risk,
        )
        db.add(new_p)
        db.commit()
        return SaveResponse(
            success=True, message="Project saved successfully!", project_id=new_p.id
        )
    except Exception as e:
        db.rollback()
        return SaveResponse(success=False, message=f"Save failed: {e}")
