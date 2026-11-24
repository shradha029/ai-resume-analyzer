import pytest

from app.services.quality import has_metric, profile_readiness, score_resume_quality, starts_with_action_verb
from app.services.resume_parser import parse_resume
from tests.pdf_factory import STUDENT_RESUME


def quality(text, pages=1):
    return score_resume_quality(parse_resume(text), text, pages)


def test_well_formed_resume_scores_high_and_components_sum_to_total():
    q = quality(STUDENT_RESUME)
    assert q["score"] >= 85
    assert sum(c["score"] for c in q["components"].values()) == pytest.approx(q["score"], abs=0.2)
    assert sum(c["max"] for c in q["components"].values()) == 100
    assert {c["max"] for c in q["components"].values()} == {20, 25, 15, 10}   # documented weights
    assert any("not a prediction" in n for n in q["notes"])


def test_weak_resume_scores_low_with_advice():
    q = quality("Jane Doe\nSkills\nPython")
    assert q["score"] < 40
    advice = [r["advice"] for c in q["components"].values() for r in c["rules"] if r["advice"]]
    assert len(advice) >= 8


def test_no_projects_or_experience_gives_zero_for_descriptions():
    q = quality("Jane Doe\njane@example.com\nSkills\nPython, SQL, Git")
    assert q["components"]["descriptions"]["score"] == 0
    assert q["components"]["achievements"]["score"] == 0


def test_metrics_component_hand_calculation():
    two_of_four = ("Jane Doe\nProjects\nApp One\n- Built a tool used by 500 users\n- Improved speed by 40%\n"
                   "- Wrote clear documentation for the tool\n- Added unit tests to the project code base\n")
    assert quality(two_of_four)["components"]["achievements"]["score"] == 15.0          # 50% >= 30% -> full
    one_of_five = two_of_four + "- Presented the work to the class\n"
    one_of_five = one_of_five.replace("- Improved speed by 40%\n", "- Improved the speed of the tool\n")
    assert quality(one_of_five)["components"]["achievements"]["score"] == pytest.approx(10.0, abs=0.1)  # 20%/30%*15


def test_helpers():
    assert has_metric("Reduced latency by 30%") and has_metric("Built for 50 users") and has_metric("Solved 300+ problems")
    assert not has_metric("Worked there in 2024") and not has_metric("Built a web app")
    assert starts_with_action_verb("Developed a REST API") and starts_with_action_verb("Built a thing")
    assert not starts_with_action_verb("Responsible for the API") and not starts_with_action_verb("")


def test_long_resume_penalised_on_formatting():
    ok, long = quality(STUDENT_RESUME, pages=1), quality(STUDENT_RESUME, pages=4)
    assert long["components"]["formatting"]["score"] < ok["components"]["formatting"]["score"]


def test_profile_readiness_formula():
    assert profile_readiness(80, 60, 40)["score"] == 61.0                  # 0.30*80 + 0.45*60 + 0.25*40
    assert profile_readiness(80, 60, None)["score"] == 68.0                # weights re-normalised
    assert profile_readiness(None, None, None)["score"] is None
