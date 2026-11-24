from pathlib import Path

import pymupdf

from app.config import settings
from app.models import ResumeAnalysis
from tests.pdf_factory import STUDENT_RESUME, make_pdf
from tests.samples import JD_BACKEND


def make_analysis(client, auth):
    rid = client.post("/api/resumes/upload", files={"file": ("r.pdf", make_pdf(STUDENT_RESUME), "application/pdf")},
                      headers=auth).json()["id"]
    client.post(f"/api/resumes/{rid}/extract", headers=auth)
    jid = client.post("/api/jobs/analyze", json={"target_role": "Backend Developer", "job_description": JD_BACKEND},
                      headers=auth).json()["id"]
    r = client.post("/api/analysis/create", json={"resume_id": rid, "job_id": jid}, headers=auth)
    assert r.status_code == 201
    return rid, r.json()


def pdf_text(content: bytes) -> str:
    doc = pymupdf.open(stream=content, filetype="pdf")
    return "\n".join(p.get_text() for p in doc)


def test_analysis_includes_quality_readiness_and_recommendations(client, auth):
    _, a = make_analysis(client, auth)
    assert 0 <= a["resume_quality_score"] <= 100 and 0 <= a["profile_readiness_score"] <= 100
    assert a["quality"]["components"]["section_completeness"]["max"] == 20
    recs = client.get(f"/api/analysis/{a['id']}/recommendations", headers=auth).json()
    assert recs["ai_status"] == "not_requested" and recs["ai_summary"] is None
    assert any(r["title"] == "Learn JWT" for r in recs["recommendations"])


def test_ai_disabled_without_key(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    _, a = make_analysis(client, auth)
    r = client.get(f"/api/analysis/{a['id']}/recommendations?ai=true", headers=auth).json()
    assert r["ai_status"] == "disabled" and r["ai_summary"] is None and r["recommendations"]


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"candidates": [{"content": {"parts": [{"text": "Focus on JWT and Docker first."}]}}]}


def test_gemini_success_and_failure_are_handled(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
    _, a = make_analysis(client, auth)
    monkeypatch.setattr("app.services.gemini_service.httpx.post", lambda *a_, **k: FakeResponse())
    ok = client.get(f"/api/analysis/{a['id']}/recommendations?ai=true", headers=auth).json()
    assert ok["ai_status"] == "ok" and ok["ai_summary"] == "Focus on JWT and Docker first."

    def boom(*a_, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr("app.services.gemini_service.httpx.post", boom)
    bad = client.get(f"/api/analysis/{a['id']}/recommendations?ai=true", headers=auth).json()
    assert bad["ai_status"] == "error" and bad["recommendations"]           # core result unaffected


def test_gemini_prompt_contains_only_analysis_facts_and_guards():
    from app.services.gemini_service import build_prompt
    p = build_prompt({"target_role": "X", "resume_quality_score": 80, "match_score": 55, "skill_coverage_score": 30,
                      "gaps": [{"severity": "high", "title": "Missing JWT"}]}, [{"title": "Learn JWT", "action": "Do it"}])
    assert "Do NOT invent" in p and "Missing JWT" in p and "hired" in p


def test_pdf_report_download(client, auth):
    _, a = make_analysis(client, auth)
    r = client.get(f"/api/reports/{a['id']}/download", headers=auth)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    text = pdf_text(r.content)
    for needle in ["Resume Analysis Report", "Backend Developer", "Aarav Sharma", "Resume Quality Score",
                   "Resume-Job Match Score", "Skill Coverage Score", "Missing skills", "JWT",
                   "Personalized recommendations", "Scoring methodology and limitations", "not a probability"]:
        assert needle in text, needle
    assert list((Path(settings.UPLOAD_DIR) / "reports").rglob("*.pdf"))


def test_report_survives_unusual_characters(client, auth):
    rid, a = make_analysis(client, auth)
    data = client.get(f"/api/resumes/{rid}/extracted", headers=auth).json()["data"]
    data["personal"]["full_name"] = "Śhradha <b>&</b> – 日本"
    assert client.put(f"/api/resumes/{rid}/extracted", json=data, headers=auth).status_code == 200
    assert client.get(f"/api/reports/{a['id']}/download", headers=auth).status_code == 200


def test_report_access_control_and_cleanup(client, auth, auth2):
    rid, a = make_analysis(client, auth)
    assert client.get(f"/api/reports/{a['id']}/download").status_code == 401
    assert client.get(f"/api/reports/{a['id']}/download", headers=auth2).status_code == 404
    client.get(f"/api/reports/{a['id']}/download", headers=auth)
    reports = Path(settings.UPLOAD_DIR) / "reports"
    assert list(reports.rglob("*.pdf"))
    client.delete(f"/api/analysis/{a['id']}", headers=auth)
    assert not list(reports.rglob("*.pdf"))                                  # file removed with the analysis
    rid2, a2 = make_analysis(client, auth)
    client.get(f"/api/reports/{a2['id']}/download", headers=auth)
    assert list(reports.rglob("*.pdf"))
    client.delete(f"/api/resumes/{rid2}", headers=auth)
    assert not list(reports.rglob("*.pdf"))                                  # and with the resume


def test_phase3_analyses_are_upgraded_lazily(client, auth):
    _, a = make_analysis(client, auth)
    with client.session_factory() as db:                                      # simulate an analysis made before Phase 4
        row = db.get(ResumeAnalysis, a["id"])
        row.details = {k: v for k, v in row.details.items() if k not in ("quality", "profile_readiness")}
        row.recommendations = []
        db.commit()
    got = client.get(f"/api/analysis/{a['id']}", headers=auth).json()
    assert got["resume_quality_score"] is not None and got["profile_readiness_score"] is not None
    assert client.get(f"/api/analysis/{a['id']}/recommendations", headers=auth).json()["recommendations"]
