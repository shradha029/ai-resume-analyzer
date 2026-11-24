from app.services.jd_analyzer import analyze_job
from app.services.matcher import run_analysis
from app.services.quality import score_resume_quality
from app.services.recommender import build_recommendations
from app.services.resume_parser import parse_resume
from tests.pdf_factory import STUDENT_RESUME
from tests.samples import JD_BACKEND


def recs_for(resume_text, jd=JD_BACKEND):
    data = parse_resume(resume_text)
    job = analyze_job(jd, "Backend Developer")
    result = run_analysis(data, resume_text, job, jd)
    return result, build_recommendations(result, score_resume_quality(data, resume_text, 1), job)


def test_recommendations_are_tied_to_gaps():
    result, recs = recs_for(STUDENT_RESUME)
    titles = [r["title"] for r in recs]
    assert "Learn JWT" in titles and "Learn AWS" in titles
    bridge = next(t for t in titles if t.startswith("Bridge from") and t.endswith("to Django"))
    assert "Flask" in bridge
    assert "Show real use of Docker" in titles
    assert not any(t in ("Learn Python", "Learn REST API") for t in titles)       # already matched
    status = {m["skill"]: m["status"] for m in result["skill_matches"]}
    for r in recs:
        if r["title"].startswith("Learn "):
            assert status[r["title"][6:]] == "missing"


def test_priorities_resources_and_reasons():
    _, recs = recs_for(STUDENT_RESUME)
    order = {"high": 0, "medium": 1, "low": 2}
    assert [order[r["priority"]] for r in recs] == sorted(order[r["priority"]] for r in recs)
    jwt = next(r for r in recs if r["title"] == "Learn JWT")
    assert jwt["priority"] == "high" and jwt["resources"] and jwt["resources"][0]["url"].startswith("https://")
    aws = next(r for r in recs if r["title"] == "Learn AWS")
    assert aws["priority"] == "medium"                                              # preferred skill
    assert all(r["reason"] and r["action"] for r in recs) and len(recs) <= 18


def test_no_invented_claims_wording():
    _, recs = recs_for(STUDENT_RESUME)
    docker = next(r for r in recs if r["title"] == "Show real use of Docker")
    assert "do not claim" in docker["action"].lower()


def test_unknown_skill_gets_generic_advice_without_fake_links():
    jd = "Platform Engineer\nRequirements:\n- Experience with Kafka and Celery\n- Strong Python knowledge"
    _, recs = recs_for(STUDENT_RESUME, jd)
    kafka = next(r for r in recs if r["title"] == "Learn Kafka")
    assert kafka["resources"] == []


def test_resume_quality_advice_appears_for_weak_resume():
    _, recs = recs_for("Jane Doe\nSkills\nPython")
    assert any(r["category"] == "resume_quality" for r in recs)
