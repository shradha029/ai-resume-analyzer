"""Job-description analysis: skills (mandatory/preferred/optional), experience, education, soft skills.

Rule-based NLP: section/line cues + the shared skill dictionary. Skills that are not in the
dictionary are picked up from phrases like "experience with Kafka" and flagged custom=True.
"""
import re
from collections import Counter

from app.services.skill_catalog import find_skills

LEVEL_WEIGHT = {"mandatory": 1.0, "preferred": 0.6, "optional": 0.3}
_RANK = {"mandatory": 3, "preferred": 2, "optional": 1}

PREDEFINED_ROLES = [
    "Software Developer", "Frontend Developer", "Backend Developer", "Python Developer",
    "Full Stack Developer", "Data Analyst", "Data Scientist", "Machine Learning Engineer",
    "AI Engineer", "Java Developer",
]

_SEC_PREFERRED = re.compile(r"^(preferred|nice to have|good to have|bonus|desirable|added advantage|plus)\b", re.I)
_SEC_REQUIRED = re.compile(r"^(requirements?|required( skills| qualifications)?|must[- ]haves?|qualifications?|"
                           r"what you.ll need|skills required|who you are|key skills|technical skills|minimum qualifications)\b", re.I)
_SEC_OTHER = re.compile(r"^(responsibilities|what you.ll do|about|role|benefits|perks|company|job description)\b", re.I)
_CUE_PREFERRED = re.compile(r"\b(preferred|nice to have|good to have|bonus|a plus|is a plus|desirable|added advantage|advantage)\b", re.I)
_CUE_OPTIONAL = re.compile(r"\b(optional|exposure to|familiarity with|awareness of|basic knowledge of)\b", re.I)
_CUE_MANDATORY = re.compile(r"\b(must|required|mandatory|essential|strong|proficien\w+|minimum|hands-on|expertise|solid)\b", re.I)

_CUSTOM_TRIGGER = re.compile(
    r"(?:experience (?:with|in|using)|knowledge of|proficien\w+ (?:in|with)|familiarity with|expertise in|"
    r"hands-on (?:experience )?(?:with|in)|working knowledge of|understanding of|skills? in)\s+([^.;\n]+)", re.I)
_GENERIC_PHRASES = {"etc", "others", "similar", "related", "software", "development", "the", "a", "an",
                    "years", "year", "programming", "modern", "relevant", "tools", "technologies", "frameworks"}

SOFT_SKILLS = {
    "Communication": r"communicat\w+",
    "Problem Solving": r"problem[- ]solving|troubleshoot\w*",
    "Teamwork": r"team ?work|team player|collaborat\w+",
    "Leadership": r"leadership|lead a team|mentor\w*",
    "Analytical Thinking": r"analytical",
    "Critical Thinking": r"critical thinking",
    "Time Management": r"time management|meet(ing)? deadlines",
    "Adaptability": r"adaptab\w+|quick learner|fast learner|willingness to learn",
    "Ownership": r"ownership|self[- ]motivated",
}
DOMAINS = ["fintech", "banking", "healthcare", "e-commerce", "edtech", "telecom", "retail", "logistics",
           "cybersecurity", "gaming", "saas", "supply chain", "insurance"]
FIELDS = {
    "Computer Science": r"computer science|\bcse\b|computer engineering",
    "Information Technology": r"information technology",
    "Software Engineering": r"software engineering",
    "Data Science": r"data science",
    "Artificial Intelligence": r"artificial intelligence",
    "Statistics": r"statistics",
    "Mathematics": r"mathematics",
    "Electronics": r"electronics",
}
LEVEL_NAMES = {0: "school", 1: "diploma", 2: "bachelor", 3: "master", 4: "doctorate"}
_STOP = set("""a an the and or of to in for with on at by is are be as that this from your you we our will can
have has not but if their it its they them such other more also all any about into over per using use used work
working team role job candidate candidates strong good experience years year skills skill knowledge ability able
required requirements preferred plus must should looking join company""".split())


def _level_for_line(line: str, section: str) -> str:
    if _CUE_PREFERRED.search(line):
        return "preferred"
    if _CUE_OPTIONAL.search(line):
        return "optional"
    if _CUE_MANDATORY.search(line):
        return "mandatory"
    return "preferred" if section == "preferred" else "mandatory"


def _walk_lines(text: str):
    """Yield (line, section) where section is required/preferred/other."""
    section = "required"
    for raw in text.splitlines():
        line = raw.strip().lstrip("-–—*•●▪ ").strip()
        if not line:
            continue
        m_pref, m_req, m_oth = _SEC_PREFERRED.match(line), _SEC_REQUIRED.match(line), _SEC_OTHER.match(line)
        short = len(line) <= 70 or ":" in line[:50]
        if short and (m_pref or m_req or m_oth) and (line.endswith(":") or ":" in line[:50] or len(line) <= 40):
            section = "preferred" if m_pref else ("required" if m_req else "other")
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if rest:
                yield rest, section
            continue
        yield line, section


def _clean_phrase(p: str) -> str:
    p = re.sub(r"\b(is|are) (a )?(plus|preferred|desirable)\b.*$", "", p, flags=re.I)
    p = re.split(r"\s+(?:for|to|using|with|in|on|at|of)\s+", p.strip())[0]
    p = re.sub(r"^(the|a|an|any|strong|good|working)\s+", "", p, flags=re.I)
    p = re.sub(r"\s+(frameworks?|tools?|technologies|platforms?|libraries|pipelines?|systems?)$", "", p, flags=re.I)
    return p.strip(" ,.;:()")


def _custom_skills(line: str) -> list[str]:
    out = []
    for m in _CUSTOM_TRIGGER.finditer(line):
        clause = re.sub(r"CI/CD", "CICD", m.group(1), flags=re.I)
        for ph in re.split(r",|/|\band\b|\bor\b|&", clause):
            ph = _clean_phrase(ph)
            words = ph.split()
            if not (1 <= len(words) <= 4 and 2 <= len(ph) <= 40):
                continue
            if any(w.lower() in _GENERIC_PHRASES for w in words) and len(words) == 1:
                continue
            techy = any(w[:1].isupper() for w in words) or bool(re.search(r"[.+#\d]", ph))
            if techy and not find_skills(ph, skills_section=True) and not _soft(ph):
                out.append(ph)
    return out


def _soft(text: str) -> list[str]:
    return [name for name, rx in SOFT_SKILLS.items() if re.search(rx, text, re.I)]


def _education(lines: list[tuple[str, str]]) -> dict:
    required, preferred, fields, quals = [], [], [], []
    for line, section in lines:
        low = line.lower()
        lvl = None
        if re.search(r"\bph\.?\s?d\b|doctorate", low):
            lvl = 4
        elif re.search(r"\bmaster|\bm\.?\s?tech\b|\bmca\b|\bm\.?\s?sc\b|\bmba\b|\bm\.?\s?e\b", low):
            lvl = 3
        elif re.search(r"\bbachelor|\bb\.?\s?tech\b|\bb\.?\s?e\b|\bbca\b|\bb\.?\s?sc\b|\bb\.?\s?com\b|\bbba\b|\bdegree\b|\bgraduate\b", low):
            lvl = 2
        elif re.search(r"\bdiploma\b", low):
            lvl = 1
        if lvl is None:
            continue
        quals.append(line)
        (preferred if (_CUE_PREFERRED.search(line) or section == "preferred") else required).append(lvl)
        fields += [f for f, rx in FIELDS.items() if re.search(rx, low)]
    return {
        "required_level": min(required) if required else None,
        "required_level_name": LEVEL_NAMES[min(required)] if required else None,
        "preferred_level": max(preferred) if preferred else None,
        "preferred_level_name": LEVEL_NAMES[max(preferred)] if preferred else None,
        "fields": sorted(set(fields)),
        "statements": quals[:6],
    }


def _experience(lines: list[tuple[str, str]]) -> dict:
    years, fresher = [], False
    intern_req = intern_pref = project_exp = False
    for line, section in lines:
        low = line.lower()
        if re.search(r"\bfresher|entry[- ]level|no (prior )?experience (is )?required|\b0\s*[-–to]+\s*1\s*years?", low):
            fresher = True
        m = re.search(r"(\d{1,2})\s*(?:\+|[-–]|to)?\s*(?:\d{1,2})?\s*\+?\s*(?:years?|yrs?)\b", low)
        if m and "experience" in low and not _CUE_PREFERRED.search(line):
            years.append(int(m.group(1)))
        if "intern" in low:
            if _CUE_PREFERRED.search(line) or section == "preferred":
                intern_pref = True
            else:
                intern_req = True
        if re.search(r"project experience|hands-on projects|academic projects|personal projects|real[- ]world projects|portfolio", low):
            project_exp = True
    min_years = max(years) if years else (0 if fresher else None)
    if fresher and years and max(years) <= 1:
        min_years = 0
    return {"min_years": min_years, "entry_level": fresher or min_years == 0,
            "internship_required": intern_req, "internship_preferred": intern_pref,
            "project_experience_mentioned": project_exp}


def analyze_job(text: str, target_role: str) -> dict:
    lines = list(_walk_lines(text))
    skills: dict[str, dict] = {}

    def add(name, cat, level, custom):
        cur = skills.get(name)
        if cur is None or _RANK[level] > _RANK[cur["level"]]:
            skills[name] = {"name": name, "category": cat, "level": level,
                            "weight": LEVEL_WEIGHT[level], "custom": custom}

    for line, section in lines:
        if section == "other" and not _CUE_MANDATORY.search(line):
            # responsibilities still mention required tech, treat as mandatory by default
            pass
        level = _level_for_line(line, section)
        listy = line.count(",") >= 2 or "/" in line
        for name, cat in find_skills(line, skills_section=listy).items():
            add(name, cat, level, False)
        for ph in _custom_skills(line):
            add(ph, "custom", level, True)

    soft = sorted({s for line, _ in lines for s in _soft(line)})
    words = Counter(w for w in re.findall(r"[A-Za-z][A-Za-z+#.\-]{2,}", text.lower()) if w not in _STOP)
    warnings = []
    if not skills:
        warnings.append("No technical skills could be detected in this job description.")
    exp = _experience(lines)
    edu = _education(lines)
    if exp["min_years"] is None:
        warnings.append("No experience requirement stated; experience score will be marked unknown.")
    if edu["required_level"] is None:
        warnings.append("No education requirement stated; education score will be marked unknown.")
    if len(text.split()) < 40:
        warnings.append("The job description is very short; results may be incomplete.")
    ordered = sorted(skills.values(), key=lambda s: (-_RANK[s["level"]], s["custom"], s["name"].lower()))
    return {
        "target_role": target_role,
        "skills": ordered,
        "experience": exp,
        "education": edu,
        "soft_skills": soft,
        "domains": [d for d in DOMAINS if d in text.lower()],
        "keywords": [w for w, _ in words.most_common(12)],
        "warnings": warnings,
    }
