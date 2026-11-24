import pytest

from app.services.jd_analyzer import analyze_job
from app.services.matcher import (CREDIT, DEFAULT_WEIGHTS, duration_months, normalise_weights, run_analysis)
from app.services.resume_parser import parse_resume
from tests.pdf_factory import INTERN_RESUME, STUDENT_RESUME
from tests.samples import JD_BACKEND, JD_INCOMPLETE, JD_ML, JD_UNFAMILIAR


def analyse(resume_text, jd, role="Role", weights=None, embedder=None):
    return run_analysis(parse_resume(resume_text), resume_text, analyze_job(jd, role), jd, weights, embedder)


def status(res):
    return {m["skill"]: m["status"] for m in res["skill_matches"]}


def test_skill_statuses_for_student_vs_backend_jd():
    res = analyse(STUDENT_RESUME, JD_BACKEND)
    st = status(res)
    assert st["Python"] == "matched" and st["REST API"] == "matched"
    assert st["Django"] == "partial" and st["FastAPI"] == "partial"    # related: Flask
    assert st["PostgreSQL"] == "partial"                                # related: MySQL
    assert st["SQL"] == "partial" and st["Docker"] == "partial"         # listed only
    assert st["JWT"] == "missing" and st["AWS"] == "missing"


def test_scores_match_hand_calculation():
    res = analyse(STUDENT_RESUME, JD_BACKEND)
    credit = {m["skill"]: m["credit"] for m in res["skill_matches"]}
    weight = {m["skill"]: m["weight"] for m in res["skill_matches"]}
    expected = sum(weight[k] * credit[k] for k in weight) / sum(weight.values()) * 100
    assert res["skill_match_score"] == pytest.approx(expected, abs=0.06)
    demo = sum(weight[m["skill"]] for m in res["skill_matches"] if m["demonstrated"]) / sum(weight.values()) * 100
    assert res["skill_coverage_score"] == pytest.approx(demo, abs=0.06)
    assert res["skill_coverage_score"] < res["skill_match_score"]       # coverage is the stricter measure

    c = res["component_scores"]
    final = sum(c[k]["weight_effective"] * c[k]["score"] for k in c if c[k]["score"] is not None)
    assert res["match_score"] == pytest.approx(final, abs=0.1)
    assert sum(c[k]["weight_effective"] for k in c) == pytest.approx(1.0, abs=0.001)
    assert c["skills"]["weight_configured"] == pytest.approx(DEFAULT_WEIGHTS["skills"], abs=0.001)


def test_student_with_no_experience_is_not_penalised_for_entry_level_job():
    res = analyse(STUDENT_RESUME, JD_BACKEND)
    assert res["component_scores"]["experience"]["score"] == 100.0


def test_experience_gap_when_years_required():
    res = analyse(STUDENT_RESUME, JD_ML)
    assert res["component_scores"]["experience"]["score"] == 0.0
    assert any(g["gap_type"] == "experience" and g["severity"] == "high" for g in res["gaps"])


def test_internship_counts_half_towards_years():
    res = analyse(INTERN_RESUME, JD_ML)
    info = res["details"]["experience"]
    assert info["internship_months"] == 3 and info["employment_months"] == 0
    assert info["equivalent_years"] == pytest.approx(0.12, abs=0.01)
    assert res["component_scores"]["experience"]["score"] == pytest.approx(6.2, abs=0.2)


def test_education_level_and_field():
    ok = analyse(STUDENT_RESUME, JD_BACKEND)
    assert ok["component_scores"]["education"]["score"] == 100.0
    low = analyse(STUDENT_RESUME, JD_ML)                                 # master's required, bachelor's held
    assert low["component_scores"]["education"]["score"] == pytest.approx(65.0, abs=0.1)   # 0.7*50 + 0.3*100


def test_different_terminology_recognised():
    resume = "Jane Doe\nSkills\nReactJS, RESTful services, scikit learn, postgres\nProjects\nShop API | Flask\n- Built RESTful services"
    jd = "Frontend Developer\nRequirements:\n- Experience with React and REST APIs\n- Knowledge of PostgreSQL and Scikit-learn"
    st = status(analyse(resume, jd))
    assert all(v in ("matched", "partial") for v in st.values()) and "missing" not in st.values()


def test_implied_skill_counts_but_below_full_credit():
    resume = "Jane Doe\nSkills\nMySQL\nProjects\nBlog\n- Stored posts in MySQL"
    res = analyse(resume, "Developer\nRequirements:\n- Strong SQL knowledge")
    m = res["skill_matches"][0]
    assert m["skill"] == "SQL" and m["status"] == "matched" and m["credit"] == CREDIT["implied_demo"]


def test_unfamiliar_skills_text_search_and_no_embedder_note():
    resume = "Jane Doe\nSkills\nPython\nProjects\nJob Queue\n- Used Celery with Redis for background tasks"
    res = analyse(resume, JD_UNFAMILIAR)
    st = status(res)
    assert st["Celery"] == "matched" and st["Kafka"] == "missing"
    assert res["method"] == "rules+tfidf"
    assert "Semantic check unavailable" in next(m for m in res["skill_matches"] if m["skill"] == "Kafka")["explanation"]


class FakeEmbedder:
    """Deterministic stand-in used only in tests (the real one needs a model download)."""
    def similarities(self, query, texts):
        return [0.8 if ("vision" in query.lower() and "face" in t.lower()) else 0.1 for t in texts]


def test_semantic_path_gives_partial_credit_and_changes_method():
    res = analyse(STUDENT_RESUME, JD_UNFAMILIAR, embedder=FakeEmbedder())
    m = next(x for x in res["skill_matches"] if x["skill"] == "Machine Vision")
    assert m["status"] == "partial" and 0 < m["credit"] <= CREDIT["semantic_max"]
    assert res["method"] == "rules+tfidf+semantic" and res["semantic_similarity"] is not None
    assert next(x for x in res["skill_matches"] if x["skill"] == "Kafka")["status"] == "missing"


def test_unknown_components_are_excluded_not_zeroed():
    res = analyse(STUDENT_RESUME, JD_INCOMPLETE)
    c = res["component_scores"]
    assert c["skills"]["status"] == "unknown" and c["experience"]["status"] == "unknown"
    assert c["education"]["status"] == "unknown"
    assert res["skill_match_score"] is None and res["skill_coverage_score"] is None
    assert res["match_score"] is None or 0 <= res["match_score"] <= 100


def test_resume_without_projects_leaves_project_score_unknown():
    resume = "Jane Doe\nSkills\nPython, SQL"
    res = analyse(resume, JD_BACKEND)
    assert res["component_scores"]["projects"]["status"] == "unknown"
    assert res["component_scores"]["education"]["status"] == "unknown"   # no education on resume


def test_custom_weights():
    base = analyse(STUDENT_RESUME, JD_BACKEND)
    skills_only = analyse(STUDENT_RESUME, JD_BACKEND, weights={"skills": 1, "experience": 0, "education": 0,
                                                               "projects": 0, "certifications": 0})
    assert skills_only["match_score"] == pytest.approx(skills_only["skill_match_score"], abs=0.1)
    assert skills_only["match_score"] != base["match_score"]
    with pytest.raises(ValueError):
        normalise_weights({"skills": -1})
    with pytest.raises(ValueError):
        normalise_weights({"nonsense": 1})
    with pytest.raises(ValueError):
        normalise_weights({k: 0 for k in DEFAULT_WEIGHTS})


def test_gaps_sorted_and_additional_skills():
    res = analyse(STUDENT_RESUME, JD_BACKEND)
    sev = [g["severity"] for g in res["gaps"]]
    assert sev == sorted(sev, key=["high", "medium", "low"].index)
    assert "Missing mandatory skill: JWT" in [g["title"] for g in res["gaps"]]
    assert "React" in res["additional_skills"] and "Python" not in res["additional_skills"]


def test_duration_parsing():
    assert duration_months("Jun 2024 - Aug 2024") == 3
    assert duration_months("Jun–Aug 2024") == 3
    assert duration_months("06/2023 - 08/2023") == 3
    assert duration_months("2022 - 2023") == 24
    assert duration_months("gibberish") is None
