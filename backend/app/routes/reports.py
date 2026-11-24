import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import AnalysisReport, User
from app.routes.analysis import ensure_phase4, get_owned, to_out
from app.schemas.analysis import RecommendationOut
from app.services import gemini_service
from app.services.report_service import build_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/{analysis_id}/download")
def download_report(analysis_id: int, ai: bool = False, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    """Generate and download the PDF report (add ?ai=true to include an optional Gemini summary)."""
    a = get_owned(db, analysis_id, user)
    ensure_phase4(db, a)
    out = to_out(a).model_dump()
    recs = [RecommendationOut.model_validate(r).model_dump() for r in a.recommendations]
    summary = gemini_service.explain(out, recs)[0] if ai else None
    pdf = build_report(out, a.resume.extracted.data, a.job.parsed, recs, summary)

    folder = Path(settings.UPLOAD_DIR) / "reports" / str(user.id)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"analysis_{a.id}.pdf"
    path.write_bytes(pdf)
    if a.reports:
        a.reports[0].file_size = len(pdf)
    else:
        a.reports = [AnalysisReport(file_path=str(path), file_size=len(pdf))]
    db.commit()
    return FileResponse(path, media_type="application/pdf", filename=f"resume-analysis-{a.id}.pdf")
