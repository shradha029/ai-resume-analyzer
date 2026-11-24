from app.services.resume_parser import parse_resume
from app.services.skill_catalog import find_skills
from tests.pdf_factory import INTERN_RESUME, STUDENT_RESUME


def skill_names(d):
    return {s["name"] for s in d["skills"]}


def test_personal_info():
    p = parse_resume(STUDENT_RESUME)["personal"]
    assert p["full_name"] == "Aarav Sharma"
    assert p["email"] == "aarav.sharma@example.com"
    assert p["phone"] == "+91 98765 43210"
    assert p["linkedin"] == "linkedin.com/in/aarav-sharma-demo"
    assert p["github"] == "github.com/aaravsharma-demo"
    assert p["portfolio"] == "https://aarav-demo.dev"


def test_education():
    edu = parse_resume(STUDENT_RESUME)["education"]
    assert len(edu) == 2
    assert edu[0]["degree"].startswith("B.Tech")
    assert edu[0]["institution"] == "Example Institute of Technology"
    assert edu[0]["graduation_year"] == 2025
    assert edu[0]["cgpa"] == 8.1 and edu[0]["cgpa_scale"] == 10
    assert "DBMS" in edu[0]["coursework"]
    assert edu[1]["percentage"] == 92.4


def test_skills_with_evidence():
    d = parse_resume(STUDENT_RESUME)
    names = skill_names(d)
    for s in ["Python", "C++", "React", "Node.js", "Express.js", "Scikit-learn", "MySQL", "Docker", "OpenCV", "REST API"]:
        assert s in names, s
    by = {s["name"]: s for s in d["skills"]}
    assert by["Docker"]["found_in"] == ["skills"]          # listed but never demonstrated
    assert "projects" in by["OpenCV"]["found_in"]


def test_student_has_no_experience():
    d = parse_resume(STUDENT_RESUME)
    assert d["experience"] == []                            # projects must NOT become experience
    assert len(d["projects"]) == 2
    assert any("experience" in w.lower() for w in d["warnings"])


def test_projects_details():
    p = parse_resume(STUDENT_RESUME)["projects"][0]
    assert p["title"] == "Smart Attendance System"
    assert {"OpenCV", "Flask", "MySQL", "REST API"} <= set(p["technologies"])
    assert "50 images per minute" in p["description"]


def test_internship_is_separate_from_projects():
    d = parse_resume(INTERN_RESUME)
    assert len(d["experience"]) == 1
    e = d["experience"][0]
    assert e["type"] == "internship"
    assert e["title"] == "Software Development Intern"
    assert e["organization"] == "Demo Tech Pvt. Ltd."
    assert e["duration"] == "Jun 2024 - Aug 2024"
    assert {"FastAPI", "PostgreSQL"} <= set(e["technologies"])
    assert len(d["projects"]) == 2


def test_certifications():
    c = parse_resume(STUDENT_RESUME)["certifications"]
    assert c[0] == {"name": "Machine Learning Specialization", "issuer": "Coursera", "date": "2023"}
    assert c[1]["issuer"] == "University of Michigan" and c[1]["date"] == "2022"


def test_different_terminology_maps_to_canonical_skills():
    text = "Skills\nReactJS, RESTful services, scikit learn, Node, postgres, Amazon Web Services, k8s"
    names = skill_names(parse_resume("Jane Doe\n" + text))
    assert {"React", "REST API", "Scikit-learn", "Node.js", "PostgreSQL", "AWS", "Kubernetes"} <= names


def test_ambiguous_words_not_matched_in_prose():
    assert "Go" not in find_skills("I wanted to Go home and express interest in R&D")
    assert "Express.js" not in find_skills("I express my thanks")
    assert {"Go", "R", "C"} <= set(find_skills("Languages: C, R, Go", skills_section=True))
    assert "Java" not in find_skills("JavaScript only")


def test_missing_sections_produce_warnings_not_inventions():
    d = parse_resume("Some Person\nsome text without any structure at all, nothing useful here")
    assert d["experience"] == [] and d["education"] == [] and d["projects"] == []
    assert d["skills"] == []
    assert d["warnings"]
