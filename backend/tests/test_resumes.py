from app.config import settings
from tests.pdf_factory import (INTERN_RESUME, STUDENT_RESUME, blank_pdf, encrypted_pdf, image_only_pdf, make_pdf)


def upload(client, auth, content, name="resume.pdf"):
    return client.post("/api/resumes/upload", files={"file": (name, content, "application/pdf")}, headers=auth)


def test_upload_requires_auth(client):
    r = client.post("/api/resumes/upload", files={"file": ("a.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 401


def test_upload_list_get_delete(client, auth, tmp_path):
    r = upload(client, auth, make_pdf(STUDENT_RESUME), "My Resume.pdf")
    assert r.status_code == 201
    body = r.json()
    assert body["original_filename"] == "My Resume.pdf" and body["page_count"] == 1 and body["status"] == "uploaded"
    rid = body["id"]
    files = list((tmp_path / "uploads").rglob("*.pdf"))
    assert len(files) == 1 and "My Resume" not in files[0].name       # stored under a random name

    assert len(client.get("/api/resumes", headers=auth).json()) == 1
    assert client.get(f"/api/resumes/{rid}", headers=auth).status_code == 200
    assert client.delete(f"/api/resumes/{rid}", headers=auth).status_code == 204
    assert list((tmp_path / "uploads").rglob("*.pdf")) == []           # file removed from disk
    assert client.get(f"/api/resumes/{rid}", headers=auth).status_code == 404


def test_reject_wrong_extension_and_fake_pdf(client, auth):
    assert upload(client, auth, b"hello", "notes.txt").status_code == 415
    assert upload(client, auth, b"this is not a pdf", "fake.pdf").status_code == 415
    assert upload(client, auth, b"", "empty.pdf").status_code == 400


def test_reject_too_large(client, auth, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    assert upload(client, auth, make_pdf(STUDENT_RESUME)).status_code == 413


def test_reject_blank_scanned_encrypted_corrupt(client, auth):
    assert upload(client, auth, blank_pdf()).status_code == 422
    r = upload(client, auth, image_only_pdf())
    assert r.status_code == 422 and "scanned" in r.json()["detail"].lower()
    r = upload(client, auth, encrypted_pdf())
    assert r.status_code == 422 and "password" in r.json()["detail"].lower()
    assert upload(client, auth, b"%PDF-1.4 garbage garbage garbage").status_code == 422
    assert client.get("/api/resumes", headers=auth).json() == []       # nothing stored


def test_user_isolation(client, auth, auth2):
    rid = upload(client, auth, make_pdf(STUDENT_RESUME)).json()["id"]
    assert client.get(f"/api/resumes/{rid}", headers=auth2).status_code == 404
    assert client.post(f"/api/resumes/{rid}/extract", headers=auth2).status_code == 404
    assert client.delete(f"/api/resumes/{rid}", headers=auth2).status_code == 404
    assert client.get("/api/resumes", headers=auth2).json() == []


def test_extract_and_review_flow(client, auth):
    rid = upload(client, auth, make_pdf(INTERN_RESUME)).json()["id"]
    assert client.get(f"/api/resumes/{rid}/extracted", headers=auth).status_code == 404   # not yet

    r = client.post(f"/api/resumes/{rid}/extract", headers=auth)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["personal"]["full_name"] == "Aarav Sharma"
    assert data["experience"][0]["type"] == "internship"
    assert client.get(f"/api/resumes/{rid}", headers=auth).json()["status"] == "extracted"

    # user corrects an extraction error
    data["personal"]["full_name"] = "Aarav K. Sharma"
    r = client.put(f"/api/resumes/{rid}/extracted", json=data, headers=auth)
    assert r.status_code == 200 and r.json()["is_user_edited"] is True
    got = client.get(f"/api/resumes/{rid}/extracted", headers=auth).json()
    assert got["data"]["personal"]["full_name"] == "Aarav K. Sharma"

    # invalid edit is rejected
    data["education"][0]["cgpa"] = 500
    assert client.put(f"/api/resumes/{rid}/extracted", json=data, headers=auth).status_code == 422
