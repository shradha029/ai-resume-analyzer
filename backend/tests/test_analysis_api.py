from tests.pdf_factory import STUDENT_RESUME, make_pdf
from tests.samples import JD_BACKEND


def setup_resume(client, auth, extract=True):
    rid = client.post("/api/resumes/upload", files={"file": ("r.pdf", make_pdf(STUDENT_RESUME), "application/pdf")},
                      headers=auth).json()["id"]
    if extract:
        client.post(f"/api/resumes/{rid}/extract", headers=auth)
    return rid


def make_job(client, auth, text=JD_BACKEND, role="Backend Developer"):
    return client.post("/api/jobs/analyze", json={"target_role": role, "job_description": text}, headers=auth)


def test_roles_and_custom_role(client, auth):
    roles = client.get("/api/jobs/roles", headers=auth).json()
    assert "Data Scientist" in roles and "Java Developer" in roles
    r = make_job(client, auth, role="Quantum Plumber")                       # any custom title is accepted
    assert r.status_code == 201 and r.json()["target_role"] == "Quantum Plumber"
    assert any(s["name"] == "Python" for s in r.json()["parsed"]["skills"])


def test_job_validation(client, auth):
    assert make_job(client, auth, text="too short").status_code == 422
    assert make_job(client, auth, role="").status_code == 422
    assert client.post("/api/jobs/analyze", json={"target_role": "x", "job_description": JD_BACKEND}).status_code == 401


def test_full_flow(client, auth):
    rid = setup_resume(client, auth)
    jid = make_job(client, auth).json()["id"]
    r = client.post("/api/analysis/create", json={"resume_id": rid, "job_id": jid}, headers=auth)
    assert r.status_code == 201
    a = r.json()
    assert 0 <= a["match_score"] <= 100 and 0 <= a["skill_coverage_score"] <= a["skill_match_score"] <= 100
    assert a["method"] in ("rules+tfidf", "rules+tfidf+semantic")
    assert {m["status"] for m in a["skill_matches"]} >= {"matched", "partial", "missing"}
    assert a["gaps"] and set(a["component_scores"]) == {"skills", "experience", "education", "projects", "certifications"}

    aid = a["id"]
    assert client.get(f"/api/analysis/{aid}", headers=auth).json()["match_score"] == a["match_score"]
    assert len(client.get(f"/api/analysis/{aid}/gaps", headers=auth).json()) == len(a["gaps"])
    hist = client.get("/api/analysis/history", headers=auth).json()
    assert len(hist) == 1 and hist[0]["resume_filename"] == "r.pdf"
    assert client.delete(f"/api/analysis/{aid}", headers=auth).status_code == 204
    assert client.get("/api/analysis/history", headers=auth).json() == []


def test_requires_extraction_and_ownership(client, auth, auth2):
    rid = setup_resume(client, auth, extract=False)
    jid = make_job(client, auth).json()["id"]
    assert client.post("/api/analysis/create", json={"resume_id": rid, "job_id": jid}, headers=auth).status_code == 409
    client.post(f"/api/resumes/{rid}/extract", headers=auth)
    aid = client.post("/api/analysis/create", json={"resume_id": rid, "job_id": jid}, headers=auth).json()["id"]
    assert client.get(f"/api/analysis/{aid}", headers=auth2).status_code == 404
    assert client.post("/api/analysis/create", json={"resume_id": rid, "job_id": jid}, headers=auth2).status_code == 404
    assert client.get(f"/api/jobs/{jid}", headers=auth2).status_code == 404


def test_custom_weights_via_api_and_bad_weights(client, auth):
    rid, jid = setup_resume(client, auth), make_job(client, auth).json()["id"]
    ok = client.post("/api/analysis/create", headers=auth,
                     json={"resume_id": rid, "job_id": jid, "weights": {"skills": 1, "experience": 0, "education": 0,
                                                                         "projects": 0, "certifications": 0}})
    assert ok.status_code == 201 and ok.json()["match_score"] == ok.json()["skill_match_score"]
    bad = client.post("/api/analysis/create", headers=auth,
                      json={"resume_id": rid, "job_id": jid, "weights": {"skills": -2}})
    assert bad.status_code == 422


def test_deleting_resume_removes_its_analyses(client, auth):
    rid, jid = setup_resume(client, auth), make_job(client, auth).json()["id"]
    client.post("/api/analysis/create", json={"resume_id": rid, "job_id": jid}, headers=auth)
    assert client.delete(f"/api/resumes/{rid}", headers=auth).status_code == 204
    assert client.get("/api/analysis/history", headers=auth).json() == []
