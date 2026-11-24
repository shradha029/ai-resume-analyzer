"""Resume-job matching engine: explainable weighted scoring.

Final score = sum(w_i * S_i) / sum(w_i) over the components that could be scored (0-100 each):
  skills 0.40, experience 0.20, education 0.15, projects 0.15, certifications 0.10  (configurable)
A component whose input information is missing is marked UNKNOWN and excluded (weights are
re-normalised over the known ones) - it is never silently treated as 0 or as 100.
"""
import re
from datetime import date

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.services.jd_analyzer import LEVEL_NAMES
from app.services.resume_parser import get_section_texts
from app.services.skill_catalog import find_skills

DEFAULT_WEIGHTS = {"skills": 0.40, "experience": 0.20, "education": 0.15, "projects": 0.15, "certifications": 0.10}

# Credit given to a required skill depending on the evidence found in the resume.
CREDIT = {
    "demonstrated": 1.0,      # exact skill used in a project / experience / certification
    "listed_only": 0.70,      # exact skill only listed in the Skills section
    "implied_demo": 0.85,     # a more specific skill that implies it is demonstrated (e.g. MySQL -> SQL)
    "implied_listed": 0.55,
    "related": 0.35,          # same family (e.g. Flask for Django)
    "semantic_max": 0.50,     # upper bound for semantic-only matches
}
SEMANTIC_THRESHOLD = 0.60     # initial value; to be calibrated with labelled pairs in Phase 6
INTERNSHIP_WEIGHT = 0.5       # internship months count at 50% towards "years of experience"
DEMO_SECTIONS = {"projects", "experience", "certifications"}

IMPLIES = {  # generic skill -> specific skills that imply it
    "Machine Learning": {"Scikit-learn", "TensorFlow", "PyTorch", "Keras", "XGBoost", "Deep Learning", "NLP", "Computer Vision"},
    "Deep Learning": {"TensorFlow", "PyTorch", "Keras"},
    "NLP": {"spaCy", "NLTK", "Hugging Face", "Sentence Transformers"},
    "SQL": {"MySQL", "PostgreSQL", "SQL Server", "SQLite", "Oracle"},
    "REST API": {"FastAPI", "Flask", "Django", "Express.js", "Spring Boot"},
    "Data Analysis": {"Pandas", "NumPy"},
    "Data Visualization": {"Matplotlib", "Seaborn", "Plotly", "Tableau", "Power BI", "Recharts"},
    "Git": {"GitHub"},
    "Web Development": {"React", "Angular", "Vue.js", "HTML", "CSS", "Node.js", "Django", "Flask"},
    "Generative AI": {"LangChain", "Hugging Face"},
}
RELATED_GROUPS = [
    {"Django", "Flask", "FastAPI", "Spring Boot", "Express.js", "Laravel"},
    {"React", "Angular", "Vue.js", "Next.js", "React Native"},
    {"MySQL", "PostgreSQL", "SQL Server", "SQLite", "Oracle"},
    {"MongoDB", "DynamoDB", "Redis", "Firebase"},
    {"TensorFlow", "PyTorch", "Keras"},
    {"AWS", "Azure", "GCP"},
    {"Java", "C#", "Kotlin"},
    {"Docker", "Kubernetes"},
    {"Matplotlib", "Seaborn", "Plotly"},
]

_MONTHS = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


# ---------- small helpers ----------
def _point(s: str, end: bool, fallback_year=None):
    if re.search(r"present|current|ongoing|now|till", s, re.I):
        t = date.today()
        return t.year, t.month
    m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*,?\s*((?:19|20)\d{2})?", s, re.I)
    if m:
        y = int(m.group(2)) if m.group(2) else fallback_year
        return (y, _MONTHS[m.group(1).lower()]) if y else None
    m = re.search(r"(\d{1,2})/((?:19|20)\d{2})", s)
    if m:
        return int(m.group(2)), int(m.group(1))
    m = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", s)
    if m:
        return int(m.group(1)), 12 if end else 1
    return None


def duration_months(d: str | None) -> int | None:
    if not d:
        return None
    parts = re.split(r"\s*(?:-|–|—|\bto\b)\s*", d, maxsplit=1)
    if len(parts) != 2:
        return None
    end = _point(parts[1], True)
    start = _point(parts[0], False, fallback_year=end[0] if end else None)
    if not start or not end:
        return None
    return max(1, (end[0] - start[0]) * 12 + (end[1] - start[1]) + 1)


def degree_level(text: str) -> int:
    if re.search(r"Ph\.?\s?D|Doctorate", text, re.I):
        return 4
    if re.search(r"Master|M\.?\s?Tech|\bMCA\b|M\.?\s?Sc|\bMBA\b|\bM\.?\s?E\b", text):
        return 3
    if re.search(r"Bachelor|B\.?\s?Tech|\bB\.?\s?E\b|\bBCA\b|B\.?\s?Sc|B\.?\s?Com|\bBBA\b", text):
        return 2
    if re.search(r"Diploma", text, re.I):
        return 1
    return 0


FIELD_TERMS = {
    "Computer Science": ["computer science", "computer engineering", "cse", "information technology", "software engineering"],
    "Information Technology": ["information technology", "computer science", "software engineering", "computer engineering"],
    "Software Engineering": ["software engineering", "computer science", "information technology", "computer engineering"],
    "Data Science": ["data science", "artificial intelligence", "machine learning", "computer science", "statistics"],
    "Artificial Intelligence": ["artificial intelligence", "machine learning", "data science", "computer science"],
    "Statistics": ["statistics", "mathematics", "data science"],
    "Mathematics": ["mathematics", "statistics", "data science"],
    "Electronics": ["electronics", "electrical", "communication"],
}


def _tfidf_sim(a: str, b: str) -> float:
    if not a.strip() or not b.strip():
        return 0.0
    try:
        m = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True).fit_transform([a, b])
        return float(cosine_similarity(m[0], m[1])[0, 0])
    except ValueError:  # empty vocabulary
        return 0.0


def _round(x, n=1):
    return None if x is None else round(x, n)


# ---------- skill matching ----------
def _evaluate_skill(req: dict, rskills: dict, sec_text: dict, evidence_pool: list[str], embedder) -> dict:
    name = req["name"]
    out = {"skill": name, "category": req["category"], "level": req["level"], "weight": req["weight"],
           "custom": req["custom"], "status": "missing", "credit": 0.0, "demonstrated": False,
           "in_projects": False, "evidence": [], "explanation": ""}

    if not req["custom"]:
        s = rskills.get(name)
        if s:
            places = [w for w in s["found_in"] if w in DEMO_SECTIONS]
            out["in_projects"] = "projects" in s["found_in"]
            if places:
                out.update(status="matched", credit=CREDIT["demonstrated"], demonstrated=True, evidence=places,
                           explanation=f"{name} is used in: {', '.join(places)}.")
            else:
                out.update(status="partial", credit=CREDIT["listed_only"], evidence=["skills"],
                           explanation=f"{name} is listed in the Skills section but no project, experience or certification "
                                       f"shows it being used. Add evidence of real use.")
            return out
        implying = [x for x in IMPLIES.get(name, set()) if x in rskills]
        if implying:
            best = max(implying, key=lambda x: bool(set(rskills[x]["found_in"]) & DEMO_SECTIONS))
            demo = bool(set(rskills[best]["found_in"]) & DEMO_SECTIONS)
            out.update(status="matched" if demo else "partial",
                       credit=CREDIT["implied_demo"] if demo else CREDIT["implied_listed"],
                       demonstrated=demo, in_projects="projects" in rskills[best]["found_in"],
                       evidence=[f"implied by {best}"],
                       explanation=f"{name} is implied by {best} ({'used in a project/experience' if demo else 'only listed'}). "
                                   f"{name} is not stated explicitly.")
            return out
        related = sorted({m for g in RELATED_GROUPS if name in g for m in g if m != name and m in rskills})
        if related:
            out.update(status="partial", credit=CREDIT["related"], evidence=[f"related: {', '.join(related)}"],
                       explanation=f"{name} is not on the resume, but related skill(s) {', '.join(related)} are. "
                                   f"Related experience helps but is not the same technology.")
            return out
        out["explanation"] = f"No evidence of {name} or a closely related skill was found in the resume."
        return out

    # custom (unfamiliar) skill: phrase search, then optional semantic check
    rx = re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.I)
    found = [sec for sec, txt in sec_text.items() if rx.search(txt)]
    if found:
        demo = [f for f in found if f in DEMO_SECTIONS]
        out["in_projects"] = "projects" in found
        if demo:
            out.update(status="matched", credit=CREDIT["demonstrated"], demonstrated=True, evidence=demo,
                       explanation=f"'{name}' appears in: {', '.join(demo)}.")
        else:
            out.update(status="partial", credit=CREDIT["listed_only"], evidence=found,
                       explanation=f"'{name}' is mentioned only in {', '.join(found)}; no demonstrated use.")
        return out
    if embedder and evidence_pool:
        sims = embedder.similarities(name, evidence_pool)
        best = max(range(len(sims)), key=sims.__getitem__)
        if sims[best] >= SEMANTIC_THRESHOLD:
            out.update(status="partial", credit=round(min(CREDIT["semantic_max"], sims[best] * 0.6), 2),
                       evidence=[f"semantic match ({sims[best]:.2f}): {evidence_pool[best][:90]}"],
                       explanation=f"No exact mention of '{name}', but similar content was found "
                                   f"(semantic similarity {sims[best]:.2f}).")
            return out
    out["explanation"] = f"'{name}' is not mentioned in the resume." + ("" if embedder else " (Semantic check unavailable.)")
    return out


# ---------- component scores ----------
def _skills_components(matches: list[dict]):
    total = sum(m["weight"] for m in matches)
    if not matches or total == 0:
        return None, None
    skill_match = sum(m["weight"] * m["credit"] for m in matches) / total * 100
    coverage = sum(m["weight"] for m in matches if m["demonstrated"]) / total * 100
    return skill_match, coverage


def _experience(resume: dict, job: dict):
    req = job["experience"]
    emp = sum(duration_months(e["duration"]) or 0 for e in resume["experience"] if e["type"] == "employment")
    intern = sum(duration_months(e["duration"]) or 0 for e in resume["experience"] if e["type"] == "internship")
    unparsed = [e for e in resume["experience"] if duration_months(e["duration"]) is None]
    eq_years = (emp + INTERNSHIP_WEIGHT * intern) / 12
    scores, notes = [], []
    info = {"employment_months": emp, "internship_months": intern, "equivalent_years": round(eq_years, 2),
            "required_min_years": req["min_years"], "entries": len(resume["experience"])}
    if req["min_years"] is not None:
        if req["min_years"] == 0:
            scores.append(100.0)
            notes.append("Entry-level role: no minimum experience required.")
        else:
            scores.append(min(1.0, eq_years / req["min_years"]) * 100)
            notes.append(f"Requires {req['min_years']}+ years; documented equivalent is {eq_years:.1f} years "
                         f"(internships count at {int(INTERNSHIP_WEIGHT * 100)}%).")
    if req["internship_required"]:
        has = bool(resume["experience"])
        scores.append(100.0 if has else 0.0)
        notes.append("Internship/work experience is required and " + ("found." if has else "not found on the resume."))
    if req["project_experience_mentioned"]:
        has = bool(resume["projects"])
        scores.append(100.0 if has else 0.0)
        notes.append("Project experience requested and " + ("projects are listed." if has else "no projects listed."))
    if unparsed:
        notes.append(f"{len(unparsed)} experience entr{'y' if len(unparsed) == 1 else 'ies'} had no readable dates and counted as 0 months.")
    return (sum(scores) / len(scores) if scores else None), notes, info


def _education(resume: dict, job: dict):
    req = job["education"]
    items = resume["education"]
    if req["required_level"] is None and not req["fields"]:
        return None, ["The job description states no education requirement."], {}
    if not items:
        return None, ["No education found on the resume; cannot compare."], {}
    best = max(items, key=lambda e: degree_level(e["degree"] or ""))
    level = degree_level(best["degree"] or "")
    year, now = best["graduation_year"], date.today().year
    pursuing = bool(year and year > now)
    notes, parts = [], []
    if req["required_level"] is not None:
        need = req["required_level"]
        lv = 100.0 if level >= need else (50.0 if level == need - 1 else 0.0)
        if pursuing and level >= need:
            lv = 90.0
            notes.append(f"Degree is in progress (expected {year}); counted at 90%.")
        notes.append(f"Requires {LEVEL_NAMES[need]} level; resume shows {LEVEL_NAMES[level]} level ({best['degree'] or 'n/a'}).")
        parts.append(("level", lv, 0.7 if req["fields"] else 1.0))
    if req["fields"]:
        txt = " ".join([best["degree"] or ""] + best["coursework"]).lower()
        ok = [f for f in req["fields"] if any(t in txt for t in FIELD_TERMS.get(f, [f.lower()]))]
        parts.append(("field", 100.0 if ok else 0.0, 0.3 if req["required_level"] is not None else 1.0))
        notes.append(f"Preferred field(s): {', '.join(req['fields'])}; " + ("match found." if ok else "no match in degree/coursework."))
    score = sum(s * w for _, s, w in parts) / sum(w for _, _, w in parts)
    if req["preferred_level"] is not None and level < req["preferred_level"]:
        notes.append(f"A {LEVEL_NAMES[req['preferred_level']]} degree is preferred (not scored).")
    return score, notes, {"resume_level": LEVEL_NAMES[level], "pursuing": pursuing}


def _certifications(resume: dict, job: dict, job_names: set[str]):
    certs = resume["certifications"]
    mentions = bool(re.search(r"certif", " ".join(job.get("keywords", [])) + " " + job.get("_text", ""), re.I))
    if not certs and not mentions:
        return None, ["No certifications on the resume and none requested; component not scored."], []
    relevant = []
    for c in certs:
        found = set(find_skills(f"{c['name']} {c['issuer'] or ''}", skills_section=True))
        implied = {g for g, specs in IMPLIES.items() if specs & found}
        if (found | implied) & job_names or any(n.lower() in c["name"].lower() for n in job_names):
            relevant.append(c["name"])
    score = 100.0 if len(relevant) >= 2 else 50.0 if len(relevant) == 1 else 0.0
    return score, [f"{len(relevant)} of {len(certs)} certification(s) relevant to the job's skills "
                   "(1 relevant = 50, 2 or more = 100)."], relevant


def _projects(resume: dict, matches: list[dict], job_text: str, embedder):
    projects = resume["projects"]
    if not projects or not matches:
        return None, ["No projects on the resume (or no job skills detected); component not scored."], []
    total = sum(m["weight"] for m in matches)
    score = sum(m["weight"] for m in matches if m["in_projects"]) / total * 100
    names = {m["skill"] for m in matches}
    weights = {m["skill"]: m["weight"] for m in matches}
    per = []
    for p in projects:
        overlap = [t for t in p["technologies"] if t in names]
        text = f"{p['title']}. {p['description']} {' '.join(p['technologies'])}"
        row = {"title": p["title"], "matching_skills": overlap,
               "skill_share": round(sum(weights[t] for t in overlap) / total, 3),
               "tfidf_similarity": round(_tfidf_sim(text, job_text), 3), "semantic_similarity": None}
        if embedder:
            row["semantic_similarity"] = round(embedder.similarities(job_text[:1500], [text])[0], 3)
        row["relevance"] = "high" if row["skill_share"] >= 0.4 else "medium" if row["skill_share"] >= 0.15 else "low"
        per.append(row)
    per.sort(key=lambda r: (-r["skill_share"], -r["tfidf_similarity"]))
    return score, ["Score = share (by weight) of job skills that appear in at least one project."], per


# ---------- gaps ----------
def _gaps(matches, exp_notes, exp_info, job, exp_score, edu_score, edu_notes, proj_score, cert_score, relevant_certs, resume):
    gaps = []
    sev = {"mandatory": "high", "preferred": "medium", "optional": "low"}
    for m in matches:
        if m["status"] == "missing":
            gaps.append({"gap_type": "missing_skill", "severity": sev[m["level"]],
                         "title": f"Missing {m['level']} skill: {m['skill']}", "description": m["explanation"]})
        elif m["status"] == "partial":
            gaps.append({"gap_type": "weak_evidence" if m["evidence"] and m["evidence"][0] in ("skills", "projects") else "partial_skill",
                         "severity": "medium" if m["level"] == "mandatory" else "low",
                         "title": f"Partially evidenced: {m['skill']}", "description": m["explanation"]})
    req = job["experience"]
    if req["min_years"] and exp_info["equivalent_years"] < req["min_years"]:
        gaps.append({"gap_type": "experience", "severity": "high", "title": "Experience below requirement",
                     "description": " ".join(exp_notes)})
    if req["internship_required"] and not resume["experience"]:
        gaps.append({"gap_type": "experience", "severity": "high", "title": "No internship/work experience documented",
                     "description": "The job requires internship or work experience and none was found on the resume."})
    elif req["internship_preferred"] and not resume["experience"]:
        gaps.append({"gap_type": "experience", "severity": "low", "title": "No internship documented (preferred)",
                     "description": "An internship is a plus for this role; none is listed."})
    if edu_score is not None and edu_score < 100:
        gaps.append({"gap_type": "qualification", "severity": "medium" if edu_score >= 50 else "high",
                     "title": "Education requirement not fully met", "description": " ".join(edu_notes)})
    if cert_score is not None and cert_score < 100:
        gaps.append({"gap_type": "certification", "severity": "low", "title": "Few relevant certifications",
                     "description": f"{len(relevant_certs)} relevant certification(s) found."})
    if proj_score is not None and proj_score < 50:
        gaps.append({"gap_type": "project_relevance", "severity": "medium", "title": "Weak project relevance",
                     "description": f"Only {proj_score:.0f}% of the job's weighted skills are demonstrated in your projects."})
    order = {"high": 0, "medium": 1, "low": 2}
    return sorted(gaps, key=lambda g: order[g["severity"]])


# ---------- main ----------
def normalise_weights(weights: dict | None) -> dict:
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        unknown = set(weights) - set(DEFAULT_WEIGHTS)
        if unknown:
            raise ValueError(f"Unknown weight keys: {sorted(unknown)}")
        w.update({k: float(v) for k, v in weights.items()})
    if any(v < 0 for v in w.values()) or sum(w.values()) <= 0:
        raise ValueError("Weights must be non-negative and not all zero.")
    t = sum(w.values())
    return {k: v / t for k, v in w.items()}


def run_analysis(resume: dict, raw_text: str, job: dict, job_text: str, weights: dict | None = None, embedder=None) -> dict:
    w = normalise_weights(weights)
    job = {**job, "_text": job_text}
    sec_text = get_section_texts(raw_text)
    rskills = {s["name"]: s for s in resume["skills"]}

    pool = [t.strip() for t in re.split(r"[,\n•]", sec_text["skills"]) if len(t.strip()) > 1]
    for p in resume["projects"]:
        pool += [f"{p['title']} ({', '.join(p['technologies'])})"] + [b for b in p["description"].split("\n") if b]
    for e in resume["experience"]:
        pool += e["responsibilities"]
    pool += [c["name"] for c in resume["certifications"]]

    matches = [_evaluate_skill(r, rskills, sec_text, pool, embedder) for r in job["skills"]]
    skill_match, coverage = _skills_components(matches)
    exp_score, exp_notes, exp_info = _experience(resume, job)
    edu_score, edu_notes, edu_info = _education(resume, job)
    job_names = {r["name"] for r in job["skills"]}
    cert_score, cert_notes, relevant = _certifications(resume, job, job_names)
    proj_score, proj_notes, proj_rows = _projects(resume, matches, job_text, embedder)

    raw = {"skills": skill_match, "experience": exp_score, "education": edu_score,
           "projects": proj_score, "certifications": cert_score}
    notes = {"skills": ["Weighted skill coverage with partial credit (see skill matches)."] if skill_match is not None
             else ["No skills detected in the job description; component not scored."],
             "experience": exp_notes, "education": edu_notes, "projects": proj_notes, "certifications": cert_notes}
    known = {k: v for k, v in raw.items() if v is not None}
    kw = sum(w[k] for k in known)
    effective = {k: (w[k] / kw if k in known and kw else 0.0) for k in w}
    final = sum(effective[k] * known[k] for k in known) if known else None

    components = {k: {"score": _round(raw[k]), "status": "scored" if raw[k] is not None else "unknown",
                      "weight_configured": round(w[k], 4), "weight_effective": round(effective[k], 4),
                      "notes": notes[k]} for k in w}
    resume_names = set(rskills)
    additional = sorted(resume_names - job_names - {x for g in IMPLIES for x in IMPLIES[g] if g in job_names})
    tfidf = _tfidf_sim(raw_text, job_text)
    semantic = None
    if embedder:
        semantic = round(embedder.similarities(job_text[:1500], [raw_text[:1500]])[0], 3)
    return {
        "match_score": _round(final),
        "skill_match_score": _round(skill_match),
        "skill_coverage_score": _round(coverage),
        "component_scores": components,
        "skill_matches": matches,
        "gaps": _gaps(matches, exp_notes, exp_info, job, exp_score, edu_score, edu_notes, proj_score,
                      cert_score, relevant, resume),
        "additional_skills": additional,
        "tfidf_similarity": round(tfidf, 3),
        "semantic_similarity": semantic,
        "method": "rules+tfidf+semantic" if embedder else "rules+tfidf",
        "details": {"experience": exp_info, "education": edu_info, "projects": proj_rows,
                    "relevant_certifications": relevant, "soft_skills_requested": job["soft_skills"],
                    "unknown_components": [k for k, v in raw.items() if v is None],
                    "warnings": job["warnings"]},
    }
