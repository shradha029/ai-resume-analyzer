"""Generate synthetic sample resumes into data/samples (run from the project root)."""
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))

from tests.pdf_factory import INTERN_RESUME, STUDENT_RESUME, image_only_pdf, make_pdf  # noqa: E402
from tests.samples import JD_BACKEND, JD_INCOMPLETE, JD_ML, JD_UNFAMILIAR  # noqa: E402

out = root / "data" / "samples"
out.mkdir(parents=True, exist_ok=True)
(out / "resume_student_no_experience.pdf").write_bytes(make_pdf(STUDENT_RESUME))
(out / "resume_with_internship.pdf").write_bytes(make_pdf(INTERN_RESUME))
(out / "scanned_like_should_be_rejected.pdf").write_bytes(image_only_pdf())
for name, text in [("jd_backend_developer", JD_BACKEND), ("jd_ml_engineer", JD_ML),
                   ("jd_unfamiliar_skills", JD_UNFAMILIAR), ("jd_incomplete", JD_INCOMPLETE)]:
    (out / f"{name}.txt").write_text(text, encoding="utf-8")
print("Samples written to", out)
