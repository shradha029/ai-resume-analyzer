import pytest

from app.ml.training import train_role_classifier as trc
from app.services import role_classifier
from tests.ml_data import make_df
from tests.pdf_factory import STUDENT_RESUME, make_pdf
from tests.samples import JD_BACKEND


@pytest.fixture()
def untrained(tmp_path, monkeypatch):
    monkeypatch.setattr(role_classifier, "MODEL_PATH", tmp_path / "none.joblib")
    monkeypatch.setattr(role_classifier, "METRICS_PATH", tmp_path / "none.json")
    role_classifier.reset_cache()
    yield
    role_classifier.reset_cache()


@pytest.fixture()
def with_model(tmp_path, monkeypatch):
    trc.train(make_df(40), cv=3, model_dir=tmp_path, source="synthetic-test")
    monkeypatch.setattr(role_classifier, "MODEL_PATH", tmp_path / "role_classifier.joblib")
    monkeypatch.setattr(role_classifier, "METRICS_PATH", tmp_path / "role_classifier_metrics.json")
    role_classifier.reset_cache()
    yield
    role_classifier.reset_cache()


def test_ml_info_requires_login(client):
    assert client.get("/api/ml/info").status_code == 401


def test_ml_info_untrained_does_not_invent_metrics(client, auth, untrained):
    r = client.get("/api/ml/info", headers=auth).json()["role_classifier"]
    assert r["trained"] is False and r["metrics"] is None


def test_job_analysis_has_no_category_when_untrained(client, auth, untrained):
    j = client.post("/api/jobs/analyze", json={"target_role": "Dev", "job_description": JD_BACKEND}, headers=auth).json()
    assert j["parsed"]["predicted_category"] is None


def test_trained_model_is_used_end_to_end(client, auth, with_model):
    info = client.get("/api/ml/info", headers=auth).json()["role_classifier"]
    assert info["trained"] and info["metrics"]["dataset"]["source_file"] == "synthetic-test"
    jd = "We need a developer. " + "java spring hibernate maven junit microservices backend servlet " * 3
    job = client.post("/api/jobs/analyze", json={"target_role": "Developer", "job_description": jd}, headers=auth).json()
    assert job["parsed"]["predicted_category"]["label"] == "Java Developer"

    rid = client.post("/api/resumes/upload", files={"file": ("r.pdf", make_pdf(STUDENT_RESUME), "application/pdf")}, headers=auth).json()["id"]
    client.post(f"/api/resumes/{rid}/extract", headers=auth)
    a = client.post("/api/analysis/create", json={"resume_id": rid, "job_id": job["id"]}, headers=auth).json()
    assert a["details"]["job_category"]["label"] == "Java Developer"
