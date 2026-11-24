import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import ExtractedResumeData, Resume, User
from app.schemas.resume import ExtractedOut, ParsedResume, ResumeOut
from app.services.pdf_service import PdfProcessingError, extract_text
from app.services.report_service import remove_report_files
from app.services.resume_parser import parse_resume

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resumes", tags=["Resumes"])


def _user_dir(user_id: int) -> Path:
    d = Path(settings.UPLOAD_DIR) / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_owned(db: Session, resume_id: int, user: User) -> Resume:
    resume = db.scalar(select(Resume).where(Resume.id == resume_id, Resume.user_id == user.id))
    if not resume:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume not found")
    return resume


def _file_path(resume: Resume) -> Path:
    return Path(settings.UPLOAD_DIR) / str(resume.user_id) / resume.stored_filename


def _read_text(resume: Resume) -> tuple[str, int]:
    path = _file_path(resume)
    if not path.exists():
        raise HTTPException(status.HTTP_410_GONE, "The stored file is missing. Please upload the resume again.")
    try:
        return extract_text(path.read_bytes())
    except PdfProcessingError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))


@router.post("/upload", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    name = Path(file.filename or "").name
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF files are accepted.")
    content = file.file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"File too large. Maximum is {settings.MAX_UPLOAD_MB} MB.")
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The uploaded file is empty.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "The file content is not a valid PDF.")
    try:
        _, pages = extract_text(content)
    except PdfProcessingError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e))

    stored = f"{uuid.uuid4().hex}.pdf"  # never use the user-supplied name on disk
    (_user_dir(user.id) / stored).write_bytes(content)
    resume = Resume(user_id=user.id, original_filename=name[:255], stored_filename=stored,
                    file_size=len(content), page_count=pages)
    db.add(resume)
    db.commit()
    db.refresh(resume)
    logger.info("Resume uploaded: id=%s user=%s", resume.id, user.id)
    return resume


@router.get("", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Resume).where(Resume.user_id == user.id).order_by(Resume.uploaded_at.desc())).all()


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _get_owned(db, resume_id, user)


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = _get_owned(db, resume_id, user)
    remove_report_files(resume.analyses)
    _file_path(resume).unlink(missing_ok=True)
    db.delete(resume)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{resume_id}/extract", response_model=ExtractedOut)
def extract_resume(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = _get_owned(db, resume_id, user)
    text, _ = _read_text(resume)
    data = parse_resume(text)
    row = resume.extracted
    if row:
        row.data, row.raw_text, row.is_user_edited = data, text, False
    else:
        row = ExtractedResumeData(resume_id=resume.id, data=data, raw_text=text)
        db.add(row)
    resume.status = "extracted"
    db.commit()
    db.refresh(row)
    return ExtractedOut(resume_id=resume.id, data=row.data, is_user_edited=row.is_user_edited, updated_at=row.updated_at)


@router.get("/{resume_id}/extracted", response_model=ExtractedOut)
def get_extracted(resume_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = _get_owned(db, resume_id, user)
    row = resume.extracted
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume has not been extracted yet. Call /extract first.")
    return ExtractedOut(resume_id=resume.id, data=row.data, is_user_edited=row.is_user_edited, updated_at=row.updated_at)


@router.put("/{resume_id}/extracted", response_model=ExtractedOut)
def update_extracted(resume_id: int, data: ParsedResume, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Let the user review and correct extraction errors."""
    resume = _get_owned(db, resume_id, user)
    row = resume.extracted
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Resume has not been extracted yet. Call /extract first.")
    row.data, row.is_user_edited = data.model_dump(), True
    db.commit()
    db.refresh(row)
    return ExtractedOut(resume_id=resume.id, data=row.data, is_user_edited=True, updated_at=row.updated_at)
