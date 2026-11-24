import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import JobDescription, User
from app.schemas.analysis import JobAnalyzeRequest, JobOut
from app.services import role_classifier
from app.services.jd_analyzer import PREDEFINED_ROLES, analyze_job
from app.services.report_service import remove_report_files

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


def _out(j: JobDescription) -> JobOut:
    return JobOut(id=j.id, target_role=j.target_role, parsed=j.parsed, created_at=j.created_at)


@router.get("/roles", response_model=list[str])
def roles(user: User = Depends(get_current_user)):
    """Predefined roles. Any custom role title is also accepted by /analyze."""
    return PREDEFINED_ROLES


@router.post("/analyze", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def analyze(data: JobAnalyzeRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    parsed = analyze_job(data.job_description, data.target_role)
    parsed["predicted_category"] = role_classifier.predict(data.job_description)   # None until a model is trained
    job = JobDescription(user_id=user.id, target_role=data.target_role, text=data.job_description, parsed=parsed)
    db.add(job)
    db.commit()
    db.refresh(job)
    return _out(job)


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(JobDescription).where(JobDescription.user_id == user.id)
                      .order_by(JobDescription.created_at.desc())).all()
    return [_out(j) for j in rows]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.scalar(select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id))
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job description not found")
    return _out(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.scalar(select(JobDescription).where(JobDescription.id == job_id, JobDescription.user_id == user.id))
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job description not found")
    remove_report_files(job.analyses)
    db.delete(job)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
