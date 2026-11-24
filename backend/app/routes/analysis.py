import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import JobDescription, Recommendation, Resume, ResumeAnalysis, SkillGap, SkillMatch, User
from app.schemas.analysis import (AnalysisCreateRequest, AnalysisOut, AnalysisSummary, GapOut, RecommendationOut,
                                  RecommendationsOut)
from app.services import embedding_service, gemini_service
from app.services.matcher import normalise_weights, run_analysis
from app.services.quality import profile_readiness, score_resume_quality
from app.services.recommender import build_recommendations
from app.services.report_service import remove_report_files

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analysis", tags=["Analysis"])

_MATCH_FIELDS = ("skill", "category", "level", "weight", "status", "credit", "custom", "demonstrated", "evidence", "explanation")


def _result_dict(a: ResumeAnalysis) -> dict:
    return {"skill_matches": [{k: getattr(m, k) for k in _MATCH_FIELDS} for m in a.skill_matches],
            "gaps": [{"gap_type": g.gap_type, "severity": g.severity, "title": g.title, "description": g.description}
                     for g in a.skill_gaps]}


def _attach_recs(a: ResumeAnalysis, recs: list[dict]) -> None:
    a.recommendations = [Recommendation(**r) for r in recs]


def ensure_phase4(db: Session, a: ResumeAnalysis) -> None:
    """Fill quality score, readiness and recommendations for analyses created before they existed."""
    changed = False
    if "quality" not in a.details:
        ex = a.resume.extracted
        q = score_resume_quality(ex.data, ex.raw_text, a.resume.page_count)
        ready = profile_readiness(q["score"], a.match_score, a.skill_coverage_score)
        a.details = {**a.details, "quality": q, "profile_readiness": ready}
        changed = True
    if not a.recommendations:
        _attach_recs(a, build_recommendations(_result_dict(a), a.details["quality"], a.job.parsed))
        changed = True
    if changed:
        db.commit()
        db.refresh(a)


def to_out(a: ResumeAnalysis) -> AnalysisOut:
    q = a.details.get("quality")
    return AnalysisOut(
        id=a.id, resume_id=a.resume_id, job_id=a.job_id, target_role=a.target_role,
        match_score=a.match_score, skill_match_score=a.skill_match_score,
        skill_coverage_score=a.skill_coverage_score, component_scores=a.component_scores,
        skill_matches=a.skill_matches, gaps=a.skill_gaps, additional_skills=a.additional_skills,
        tfidf_similarity=a.tfidf_similarity, semantic_similarity=a.semantic_similarity,
        method=a.method, details=a.details,
        resume_quality_score=q["score"] if q else None,
        profile_readiness_score=(a.details.get("profile_readiness") or {}).get("score"),
        quality=q, created_at=a.created_at)


def get_owned(db: Session, analysis_id: int, user: User) -> ResumeAnalysis:
    a = db.scalar(select(ResumeAnalysis).where(ResumeAnalysis.id == analysis_id, ResumeAnalysis.user_id == user.id))
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return a


@router.post("/create", response_model=AnalysisOut, status_code=status.HTTP_201_CREATED)
def create_analysis(data: AnalysisCreateRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = db.scalar(select(Resume).where(Resume.id == data.resume_id, Resume.user_id == user.id))
    job = db.scalar(select(JobDescription).where(JobDescription.id == data.job_id, JobDescription.user_id == user.id))
    if not resume or not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume or job description not found")
    if not resume.extracted:
        raise HTTPException(status.HTTP_409_CONFLICT, "Extract the resume first (POST /api/resumes/{id}/extract).")
    ex = resume.extracted
    try:
        normalise_weights(data.weights)
        result = run_analysis(ex.data, ex.raw_text, job.parsed, job.text, data.weights, embedding_service.get_embedder())
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    quality = score_resume_quality(ex.data, ex.raw_text, resume.page_count)
    ready = profile_readiness(quality["score"], result["match_score"], result["skill_coverage_score"])
    a = ResumeAnalysis(
        user_id=user.id, resume_id=resume.id, job_id=job.id, target_role=job.target_role,
        match_score=result["match_score"], skill_match_score=result["skill_match_score"],
        skill_coverage_score=result["skill_coverage_score"], tfidf_similarity=result["tfidf_similarity"],
        semantic_similarity=result["semantic_similarity"], method=result["method"],
        component_scores=result["component_scores"], additional_skills=result["additional_skills"],
        details={**result["details"], "quality": quality, "profile_readiness": ready,
                 "job_category": job.parsed.get("predicted_category")})
    a.skill_matches = [SkillMatch(**{k: m[k] for k in _MATCH_FIELDS}) for m in result["skill_matches"]]
    a.skill_gaps = [SkillGap(**g) for g in result["gaps"]]
    _attach_recs(a, build_recommendations(result, quality, job.parsed))
    db.add(a)
    db.commit()
    db.refresh(a)
    logger.info("Analysis created: id=%s user=%s", a.id, user.id)
    return to_out(a)


@router.get("/history", response_model=list[AnalysisSummary])
def history(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.scalars(select(ResumeAnalysis).where(ResumeAnalysis.user_id == user.id)
                      .order_by(ResumeAnalysis.created_at.desc())).all()
    return [AnalysisSummary(id=a.id, resume_id=a.resume_id, resume_filename=a.resume.original_filename,
                            target_role=a.target_role, match_score=a.match_score,
                            skill_coverage_score=a.skill_coverage_score, created_at=a.created_at) for a in rows]


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = get_owned(db, analysis_id, user)
    ensure_phase4(db, a)
    return to_out(a)


@router.get("/{analysis_id}/gaps", response_model=list[GapOut])
def get_gaps(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_owned(db, analysis_id, user).skill_gaps


@router.get("/{analysis_id}/recommendations", response_model=RecommendationsOut)
def get_recommendations(analysis_id: int, ai: bool = False, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Rule-based recommendations; add ?ai=true for an optional Gemini explanation (if configured)."""
    a = get_owned(db, analysis_id, user)
    ensure_phase4(db, a)
    recs = [RecommendationOut.model_validate(r) for r in a.recommendations]
    summary, st = (None, "not_requested")
    if ai:
        summary, st = gemini_service.explain(to_out(a).model_dump(), [r.model_dump() for r in recs])
    return RecommendationsOut(recommendations=recs, ai_summary=summary, ai_status=st)


@router.delete("/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    a = get_owned(db, analysis_id, user)
    remove_report_files([a])
    db.delete(a)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
