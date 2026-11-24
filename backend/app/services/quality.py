"""Resume Quality Score (0-100): transparent, rule-based, fully documented.

Component maxima (= weights): section completeness 20, skills presentation 20,
experience/project descriptions 25, quantifiable achievements 15, formatting/readability 10,
education & certification presentation 10. Total = sum of points (max 100).

This score measures how well the resume is structured and presented. It is NOT a prediction
of selection or hiring. Grammar is not checked (no grammar library is used).
"""
import re

ACTION_VERBS = {
    "built", "led", "wrote", "ran", "made", "drove", "developed", "designed", "implemented", "created", "managed",
    "optimized", "optimised", "reduced", "increased", "improved", "deployed", "integrated", "automated", "analyzed",
    "analysed", "engineered", "architected", "trained", "tested", "launched", "migrated", "collaborated", "delivered",
    "established", "achieved", "solved", "researched", "maintained", "configured", "streamlined", "processed",
    "stored", "exposed", "secured", "containerized", "evaluated", "visualized", "applied", "organized", "organised",
    "won", "finalist", "ranked", "secured", "participated", "contributed", "presented", "mentored", "coordinated",
}
_YEAR = re.compile(r"(?:19|20)\d{2}")
_METRIC = re.compile(r"\d+(?:\.\d+)?\s?%|\b\d{2,}\b|\d\s?[xk+]\b|\b\d+\s?(?:users|requests|records|images|hours|seconds|ms|students|members)\b", re.I)
DEMO = {"projects", "experience", "certifications"}


def has_metric(text: str) -> bool:
    return bool(_METRIC.search(_YEAR.sub("", text)))


def starts_with_action_verb(text: str) -> bool:
    w = re.sub(r"[^a-z\-]", "", text.strip().split(" ")[0].lower()) if text.strip() else ""
    return bool(w) and (w in ACTION_VERBS or (len(w) > 4 and w.endswith("ed")))


def _bullets(data: dict) -> list[str]:
    out = []
    for p in data["projects"]:
        out += [b for b in p["description"].split("\n") if b.strip()]
    for e in data["experience"]:
        out += e["responsibilities"]
    return out


def _rule(rule_id, label, points, mx, detail, advice=None):
    points = round(points, 2)
    return {"id": rule_id, "rule": label, "points": points, "max": mx, "detail": detail,
            "advice": advice if points < mx * 0.999 else None}


def _completeness(d):
    p, sec = d["personal"], d["sections_detected"]
    rules = [
        _rule("contact_name", "Name present", 2 if p["full_name"] else 0, 2, "Name detected" if p["full_name"] else "Name not found",
              "Put your full name at the top of the resume in plain text."),
        _rule("contact_email", "Email present", 2 if p["email"] else 0, 2, "Email detected" if p["email"] else "Email not found",
              "Add a professional email address in the header."),
        _rule("contact_phone", "Phone present", 1 if p["phone"] else 0, 1, "Phone detected" if p["phone"] else "Phone not found",
              "Add a phone number in the header."),
        _rule("contact_links", "LinkedIn or GitHub link", 1 if (p["linkedin"] or p["github"]) else 0, 1,
              "Profile link found" if (p["linkedin"] or p["github"]) else "No LinkedIn/GitHub link",
              "Add your GitHub and/or LinkedIn URL so recruiters can see your work."),
        _rule("sec_education", "Education section", 4 if d["education"] else 0, 4, f"{len(d['education'])} education entr(ies)",
              "Add an Education section with degree, college and year."),
        _rule("sec_skills", "Skills section", 4 if "skills" in sec else 0, 4, "Skills section found" if "skills" in sec else "No Skills section",
              "Add a clearly titled 'Technical Skills' section."),
        _rule("sec_work", "Projects or experience", 4 if (d["projects"] or d["experience"]) else 0, 4,
              f"{len(d['projects'])} project(s), {len(d['experience'])} experience entr(ies)",
              "Add at least 2 projects (or internships) with descriptions."),
        _rule("sec_extra", "Certifications or achievements", 2 if (d["certifications"] or d["achievements"]) else 0, 2,
              "Found" if (d["certifications"] or d["achievements"]) else "None found",
              "Add relevant certifications or achievements, if you have them."),
    ]
    return rules


def _skills(d):
    skills = d["skills"]
    n = len(skills)
    cats = len({s["category"] for s in skills})
    demo = sum(1 for s in skills if set(s["found_in"]) & DEMO)
    ratio = demo / n if n else 0
    return [
        _rule("skills_count", "Number of recognised skills (8+ = full)", min(n / 8, 1) * 8, 8, f"{n} skills recognised",
              "List more of the technologies you genuinely know (aim for 8+ relevant skills)."),
        _rule("skills_variety", "Variety of skill categories (4+ = full)", min(cats / 4, 1) * 5, 5, f"{cats} categories",
              "Group skills by type (languages, frameworks, databases, tools) and cover more than one category."),
        _rule("skills_section", "Dedicated Skills section", 4 if "skills" in d["sections_detected"] else 0, 4,
              "Present" if "skills" in d["sections_detected"] else "Missing",
              "Create a dedicated skills section so ATS tools can read it."),
        _rule("skills_evidence", "Skills shown in projects/experience (50%+ = full)", min(ratio / 0.5, 1) * 3, 3,
              f"{demo} of {n} skills appear in a project, experience or certification ({ratio:.0%})",
              "Mention your key skills inside project/experience bullets, not only in the skills list."),
    ]


def _descriptions(d):
    items = []
    for p in d["projects"]:
        items.append((p["title"], [b for b in p["description"].split("\n") if b.strip()], bool(p["technologies"])))
    for e in d["experience"]:
        items.append((e["title"] or e["organization"] or "Experience", e["responsibilities"], bool(e["technologies"])))
    if not items:
        return [_rule("desc_none", "Project/experience descriptions", 0, 25, "No projects or experience to evaluate",
                      "Add projects or internships with 2-3 descriptive bullets each.")]
    qs, weak = [], []
    for title, bullets, tech in items:
        nb = len(bullets)
        words = [len(b.split()) for b in bullets]
        length_ok = sum(1 for w in words if 8 <= w <= 35) / nb if nb else 0
        verbs = sum(1 for b in bullets if starts_with_action_verb(b)) / nb if nb else 0
        q = 0.3 * min(nb / 2, 1) + 0.25 * length_ok + 0.25 * verbs + 0.2 * (1 if tech else 0)
        qs.append(q)
        if q < 0.6:
            weak.append(title)
    avg = sum(qs) / len(qs)
    detail = f"Average item quality {avg:.0%} over {len(items)} item(s)"
    if weak:
        detail += f"; weaker items: {', '.join(weak[:3])}"
    return [_rule("desc_quality", "Description quality (2+ bullets, 8-35 words, action verb, technologies named)", avg * 25, 25, detail,
                  "For each project/internship write 2-3 bullets that start with an action verb, name the technologies "
                  "and explain what you built and why.")]


def _metrics(d):
    bullets = _bullets(d) + d["achievements"]
    if not bullets:
        return [_rule("metrics", "Quantifiable achievements", 0, 15, "No bullets to evaluate",
                      "Add bullets that include real, verifiable numbers (users, accuracy, speed, size).")]
    with_m = sum(1 for b in bullets if has_metric(b))
    r = with_m / len(bullets)
    return [_rule("metrics", "Bullets with measurable results (30%+ = full)", min(r / 0.3, 1) * 15, 15,
                  f"{with_m} of {len(bullets)} bullets contain numbers/metrics ({r:.0%})",
                  "Where true, add measurable outcomes to bullets (e.g. accuracy, response time, users, data size). "
                  "Only use numbers you can verify.")]


def _formatting(d, raw_text, pages):
    words = len(raw_text.split())
    bullets = _bullets(d)
    avg_len = sum(len(b.split()) for b in bullets) / len(bullets) if bullets else 0
    dup = len({b.lower() for b in bullets}) != len(bullets)
    headings = len(d["sections_detected"])
    return [
        _rule("fmt_pages", "Length: 1-2 pages", 3 if pages <= 2 else 1.5 if pages == 3 else 0, 3, f"{pages} page(s)",
              "Keep the resume to 1-2 pages."),
        _rule("fmt_words", "Word count 200-900", 3 if 200 <= words <= 900 else 1.5 if (120 <= words < 200 or 900 < words <= 1200) else 0, 3,
              f"{words} words", "Aim for roughly 300-700 words: enough detail, but concise."),
        _rule("fmt_headings", "Clear section headings (4+ recognised)", 2 if headings >= 4 else 1 if headings == 3 else 0, 2,
              f"{headings} standard headings recognised", "Use standard headings (Education, Skills, Projects, Experience, Certifications)."),
        _rule("fmt_consistency", "No duplicate bullets", 0 if dup else 1, 1, "Duplicate bullets found" if dup else "No duplicates",
              "Remove repeated bullet points."),
        _rule("fmt_readability", "Readable bullet length (avg 30 words or fewer)", 1 if avg_len <= 30 else 0, 1,
              f"Average bullet length {avg_len:.0f} words", "Shorten long bullets to one or two lines."),
    ]


def _education(d):
    rules = []
    edu = max(d["education"], key=lambda e: sum(bool(e[k]) for k in ("degree", "institution", "graduation_year"))) if d["education"] else None
    for key, label, advice in [("degree", "Degree stated", "State your degree and branch clearly."),
                               ("institution", "College/university stated", "Add your college/university name."),
                               ("graduation_year", "Graduation year stated", "Add your (expected) graduation year.")]:
        ok = bool(edu and edu[key])
        rules.append(_rule(f"edu_{key}", label, 2 if ok else 0, 2, "Present" if ok else "Missing", advice))
    ok = bool(edu and (edu["cgpa"] is not None or edu["percentage"] is not None))
    rules.append(_rule("edu_score", "CGPA or percentage stated", 2 if ok else 0, 2, "Present" if ok else "Missing",
                       "Add your CGPA/percentage if you are comfortable sharing it."))
    certs = d["certifications"]
    if certs:
        r = sum(1 for c in certs if c["issuer"] or c["date"]) / len(certs)
        rules.append(_rule("cert_detail", "Certifications list issuer/date", 2 * r, 2, f"{r:.0%} of certifications have issuer or date",
                           "For each certification add the issuing organisation and the year."))
    else:
        rules.append(_rule("cert_detail", "Certifications list issuer/date", 0, 2, "No certifications listed (optional)",
                           "If you have completed relevant courses/certifications, list them with issuer and year."))
    return rules


def score_resume_quality(data: dict, raw_text: str, page_count: int) -> dict:
    spec = [
        ("section_completeness", "Section completeness", 20, _completeness(data)),
        ("skills_presentation", "Skills presentation", 20, _skills(data)),
        ("descriptions", "Experience and project descriptions", 25, _descriptions(data)),
        ("achievements", "Quantifiable achievements", 15, _metrics(data)),
        ("formatting", "Formatting and readability", 10, _formatting(data, raw_text, page_count)),
        ("education_certs", "Education and certification presentation", 10, _education(data)),
    ]
    comps, total = {}, 0.0
    for key, label, mx, rules in spec:
        pts = round(min(mx, sum(r["points"] for r in rules)), 1)
        total += pts
        comps[key] = {"label": label, "score": pts, "max": mx, "percent": round(pts / mx * 100, 1), "rules": rules}
    return {"score": round(total, 1), "components": comps,
            "notes": ["Rule-based presentation score; not a prediction of selection or hiring.",
                      "Grammar and spelling are not checked in this version."]}


READINESS_WEIGHTS = {"quality": 0.30, "match": 0.45, "coverage": 0.25}


def profile_readiness(quality: float | None, match: float | None, coverage: float | None) -> dict:
    """Heuristic summary: 0.30 Quality + 0.45 Match + 0.25 Coverage (weights re-normalised over known values).
    Not a probability of selection."""
    vals = {"quality": quality, "match": match, "coverage": coverage}
    known = {k: v for k, v in vals.items() if v is not None}
    if not known:
        return {"score": None, "weights": {}}
    tw = sum(READINESS_WEIGHTS[k] for k in known)
    w = {k: READINESS_WEIGHTS[k] / tw for k in known}
    return {"score": round(sum(w[k] * known[k] for k in known), 1), "weights": {k: round(v, 3) for k, v in w.items()}}
