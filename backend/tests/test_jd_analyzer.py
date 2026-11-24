from app.services.jd_analyzer import analyze_job
from tests.samples import JD_BACKEND, JD_INCOMPLETE, JD_ML, JD_UNFAMILIAR


def by_name(job):
    return {s["name"]: s for s in job["skills"]}


def test_backend_jd_levels():
    job = analyze_job(JD_BACKEND, "Backend Developer")
    s = by_name(job)
    for name in ["Python", "FastAPI", "Django", "PostgreSQL", "SQL", "REST API", "JWT"]:
        assert s[name]["level"] == "mandatory", name
    for name in ["Docker", "AWS", "CI/CD"]:
        assert s[name]["level"] == "preferred", name
    assert s["Python"]["weight"] > s["Docker"]["weight"]          # mandatory weighs more than preferred
    assert not any(x["name"] in ("CI", "CD pipelines") for x in job["skills"])


def test_backend_jd_experience_education_soft():
    job = analyze_job(JD_BACKEND, "Backend Developer")
    assert job["experience"]["min_years"] == 0 and job["experience"]["entry_level"]
    assert job["experience"]["internship_preferred"] and not job["experience"]["internship_required"]
    assert job["education"]["required_level"] == 2
    assert job["education"]["fields"] == ["Computer Science"]
    assert {"Communication", "Problem Solving"} <= set(job["soft_skills"])
    assert "logistics" in job["domains"]


def test_ml_jd_years_and_masters():
    job = analyze_job(JD_ML, "Machine Learning Engineer")
    assert job["experience"]["min_years"] == 2
    assert job["education"]["required_level"] == 3
    s = by_name(job)
    assert s["Machine Learning"]["level"] == "mandatory" or "Scikit-learn" in s
    assert s["AWS"]["level"] == "preferred" and s["Docker"]["level"] in ("preferred", "optional")


def test_unfamiliar_skills_are_kept_as_custom():
    s = by_name(analyze_job(JD_UNFAMILIAR, "Platform Engineer"))
    for name in ["Kafka", "RabbitMQ", "Celery", "Machine Vision"]:
        assert s[name]["custom"] is True, name
    assert s["Python"]["custom"] is False


def test_incomplete_jd_reports_warnings_not_invented_requirements():
    job = analyze_job(JD_INCOMPLETE, "Developer")
    assert job["skills"] == []
    assert job["experience"]["min_years"] is None
    assert job["education"]["required_level"] is None
    assert len(job["warnings"]) >= 3
