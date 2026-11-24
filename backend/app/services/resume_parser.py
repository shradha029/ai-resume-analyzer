"""Rule-based resume parser: regex + section heuristics + skill dictionary.

Nothing is invented: a field that cannot be found is left empty and a warning is added.
Professional experience is read ONLY from Experience/Internship sections; projects are never
counted as experience.
"""
import re

from app.schemas.resume import ParsedResume
from app.services.skill_catalog import find_skills

# ---------- section headings ----------
_HEADING_WORDS = {
    "education": ["education", "academic background", "academic qualifications", "educational qualifications"],
    "skills": ["skills", "technical skills", "key skills", "core competencies", "technical proficiency",
               "skills & tools", "skills and tools", "technical skills & tools"],
    "experience": ["experience", "work experience", "professional experience", "employment",
                   "employment history", "work history"],
    "internships": ["internships", "internship", "internship experience"],
    "projects": ["projects", "academic projects", "personal projects", "project work", "key projects",
                 "technical projects"],
    "certifications": ["certifications", "certificates", "licenses & certifications",
                       "certifications & courses", "courses & certifications", "certification"],
    "achievements": ["achievements", "awards", "honors", "accomplishments", "awards & achievements",
                     "achievements & awards", "awards and achievements"],
    "publications": ["publications", "research papers", "research publications"],
    "extracurricular": ["extracurricular activities", "extracurricular", "activities",
                        "positions of responsibility", "volunteering", "volunteer experience", "leadership"],
    "summary": ["summary", "professional summary", "objective", "career objective", "profile", "about me"],
}
_HEADING_MAP = {w: k for k, words in _HEADING_WORDS.items() for w in words}


def _heading_key(line: str):
    if len(line) > 45:
        return None
    norm = re.sub(r"\s+", " ", re.sub(r"[^a-z& ]", "", line.lower())).strip()
    return _HEADING_MAP.get(norm)


def split_sections(text: str):
    header, sections, current = [], {}, None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key = _heading_key(line)
        if key:
            current = key
            sections.setdefault(key, [])
        elif current is None:
            header.append(line)
        else:
            sections[current].append(line)
    return header, sections


# ---------- line normalisation (bullets / wrapped lines) ----------
_BULLETS = "•●▪■◦○·►➢✓➤"


def normalize_lines(lines: list[str]) -> list[tuple[bool, str]]:
    out: list[tuple[bool, str]] = []
    pending_bullet = False
    for line in lines:
        s = line.strip()
        if not s:
            continue
        is_bullet, body = False, s
        if s[0] in _BULLETS or (ord(s[0]) >= 0xE000 and ord(s[0]) <= 0xF8FF):
            is_bullet, body = True, s[1:].strip()
        elif s[0] in "-–—*" and len(s) > 1 and s[1] == " ":
            is_bullet, body = True, s[2:].strip()
        if is_bullet and not body:
            pending_bullet = True
            continue
        if pending_bullet:
            is_bullet, pending_bullet = True, False
        if not is_bullet and out and out[-1][0] and body[:1].islower():
            out[-1] = (True, out[-1][1] + " " + body)  # wrapped bullet line
            continue
        out.append((is_bullet, body))
    return out


# ---------- personal info ----------
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_LINKEDIN = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/[^\s,;|)]+", re.I)
_GITHUB = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[^\s,;|)]+", re.I)
_URL = re.compile(r"(?:https?://|www\.)[^\s,;|)]+", re.I)
_PHONE = re.compile(r"(?<![\d/])(\+?\d[\d\s().-]{8,16}\d)(?![\d/])")


def _first(rx, text):
    m = rx.search(text)
    return m.group(0).rstrip(".,;:)") if m else None


def _find_phone(text: str):
    for m in _PHONE.finditer(text):
        digits = re.sub(r"\D", "", m.group(1))
        if 10 <= len(digits) <= 13 and not re.fullmatch(r"(?:19|20)\d{2}\D*(?:19|20)\d{2}", m.group(1).strip()):
            return re.sub(r"\s+", " ", m.group(1)).strip()
    return None


def _find_name(header_lines: list[str]):
    for i, line in enumerate(header_lines[:6]):
        if any(c in line for c in "@|/:") or re.search(r"\d", line):
            continue
        if re.search(r"resume|curriculum|vitae|\bcv\b", line, re.I):
            continue
        words = line.replace(",", " ").split()
        if 1 <= len(words) <= 4 and all(re.fullmatch(r"[A-Za-z.'\-]+", w) for w in words) and (len(words) >= 2 or i == 0):
            return line.title() if line.isupper() else line
    return None


def parse_personal(header_lines: list[str], full_text: str) -> dict:
    head = "\n".join(header_lines)
    pick = lambda rx: _first(rx, head) or _first(rx, full_text)  # noqa: E731
    portfolio = None
    for m in _URL.finditer(head):
        u = m.group(0).rstrip(".,;:)")
        if "linkedin.com" not in u.lower() and "github.com" not in u.lower():
            portfolio = u
            break
    return {
        "full_name": _find_name(header_lines),
        "email": pick(_EMAIL),
        "phone": _find_phone(head) or _find_phone(full_text[:1500]),
        "linkedin": pick(_LINKEDIN),
        "github": pick(_GITHUB),
        "portfolio": portfolio,
    }


# ---------- education ----------
_DEGREE = re.compile(
    r"(?<![A-Za-z])(?:B\.?\s?Tech|B\.?\s?E\.?(?![A-Za-z])|B\.?\s?Sc\.?(?![A-Za-z])|B\.?\s?C\.?\s?A\.?(?![A-Za-z])"
    r"|B\.?\s?Com(?![A-Za-z])|BBA|M\.?\s?Tech|M\.?\s?E\.?(?![A-Za-z])|M\.?\s?Sc\.?(?![A-Za-z])"
    r"|M\.?\s?C\.?\s?A\.?(?![A-Za-z])|MBA|Ph\.?\s?D|Bachelor(?:'?s)?\s+of\s+\w+|Master(?:'?s)?\s+of\s+\w+"
    r"|Diploma|Senior Secondary|Higher Secondary|Secondary|Intermediate|Class\s+(?:XII|XI|X|12|10)|(?:10|12)th)"
)
_INST = re.compile(r"University|College|Institute|School|Academy|Polytechnic|\bIIT\b|\bNIT\b|\bIIIT\b|Vidyalaya", re.I)
_YEAR = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
_CGPA = re.compile(r"(?:CGPA|GPA|C\.G\.P\.A)\s*[:\-]?\s*(\d{1,2}(?:\.\d{1,2})?)(?:\s*/\s*(10|4|5))?", re.I)
_CGPA_SLASH = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2})\s*/\s*(10|4|5)(?!\d)")
_PERCENT = re.compile(r"(?<![\d.])(\d{2,3}(?:\.\d+)?)\s*%")
_SEP = re.compile(r"\s[|–—-]\s|\|")


def _degree_text(line: str) -> str:
    m = _DEGREE.search(line)
    s = line[m.start():]
    s = re.split(r"\s[|–—-]\s|\||\(|\bCGPA\b|\bGPA\b|(?:19|20)\d{2}|\d+(?:\.\d+)?\s*%", s, maxsplit=1)[0]
    return s.strip(" ,;:-–—")


def _institution_text(line: str):
    parts = [p for p in re.split(r"\s[|–—-]\s|\||,", line) if _INST.search(p)]
    if not parts:
        return None
    part = next((p for p in parts if not _DEGREE.search(p)), parts[0])
    return re.sub(r"\s*(?:19|20)\d{2}.*$", "", part).strip(" ,;:-–—") or None


def parse_education(lines: list[tuple[bool, str]]) -> list[dict]:
    groups, cur = [], None
    for _, text in lines:
        has_deg, has_inst = bool(_DEGREE.search(text)), bool(_INST.search(text))
        if cur is None or (has_deg and cur["deg"]) or (has_inst and cur["inst"]):
            cur = {"lines": [], "deg": None, "inst": None}
            groups.append(cur)
        cur["lines"].append(text)
        if has_deg and not cur["deg"]:
            cur["deg"] = text
        if has_inst and not cur["inst"]:
            cur["inst"] = text

    items = []
    for g in groups:
        blob = "\n".join(g["lines"])
        if not g["deg"] and not g["inst"]:
            continue
        item = {"degree": _degree_text(g["deg"]) if g["deg"] else None,
                "institution": _institution_text(g["inst"]) if g["inst"] else None,
                "graduation_year": None, "cgpa": None, "cgpa_scale": None, "percentage": None, "coursework": []}
        years = [int(y) for y in _YEAR.findall(blob)]
        if years:
            item["graduation_year"] = max(years)
        m = _CGPA.search(blob) or _CGPA_SLASH.search(blob)
        if m:
            item["cgpa"] = float(m.group(1))
            item["cgpa_scale"] = float(m.group(2)) if m.group(2) else None
        m = _PERCENT.search(blob)
        if m and float(m.group(1)) <= 100:
            item["percentage"] = float(m.group(1))
        for t in g["lines"]:
            cm = re.match(r"(?:relevant\s+)?course\s?work\s*:?\s*(.*)", t, re.I)
            if cm and cm.group(1):
                item["coursework"] = [c.strip() for c in re.split(r"[,;•|]", cm.group(1)) if c.strip()]
        items.append(item)
    return items


# ---------- experience ----------
_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|June?|July?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
_DATE = rf"(?:{_MONTH}\s*,?\s*(?:19|20)\d{{2}}|\d{{1,2}}/(?:19|20)\d{{2}}|(?:19|20)\d{{2}})"
_END = rf"(?:{_DATE}|Present|Current|Ongoing|Till\s+date|Now)"
_DASH = r"(?:-|–|—|\bto\b)"
_RANGE = re.compile(rf"{_DATE}\s*{_DASH}\s*{_END}|{_MONTH}\s*{_DASH}\s*{_MONTH}\s*(?:19|20)\d{{2}}", re.I)
_TITLE_WORDS = re.compile(
    r"intern|developer|engineer|analyst|trainee|associate|manager|consultant|designer|scientist|researcher|"
    r"architect|administrator|assistant|executive|lead|specialist|apprentice|programmer|fellow", re.I)
_PART_SPLIT = re.compile(r"\s*\|\s*|\s[–—-]\s|,\s+(?=[A-Z])|\s+at\s+|\s+@\s+")


def _parts(s: str) -> list[str]:
    return [p.strip(" ()|,:-–—") for p in _PART_SPLIT.split(s) if p.strip(" ()|,:-–—")]


def parse_experience(lines: list[tuple[bool, str]], section: str) -> list[dict]:
    entries, cur, pending = [], None, []
    for i, (is_bullet, text) in enumerate(lines):
        nxt = lines[i + 1][1] if i + 1 < len(lines) and not lines[i + 1][0] else ""
        if is_bullet:
            if cur:
                cur["bullets"].append(text)
            continue
        m = _RANGE.search(text)
        if m:
            cur = {"duration": m.group(0), "parts": pending + _parts(text.replace(m.group(0), " ")),
                   "bullets": [], "idx": i}
            entries.append(cur)
            pending = []
        elif nxt and _RANGE.search(nxt):
            pending = _parts(text)  # header line sitting above the date line
        elif cur and not cur["bullets"] and i == cur["idx"] + 1 and len(text) <= 45 and not text.endswith("."):
            cur["parts"] += _parts(text)  # e.g. "Company, City" under the title line
        elif cur:
            cur["bullets"].append(text)

    items = []
    for e in entries:
        title = next((p for p in e["parts"] if _TITLE_WORDS.search(p)), None)
        org = next((p for p in e["parts"] if p != title and len(p) > 1), None)
        blob = " ".join(e["parts"] + e["bullets"])
        is_intern = section == "internships" or bool(title and re.search("intern", title, re.I))
        items.append({
            "organization": org, "title": title, "duration": e["duration"],
            "type": "internship" if is_intern else "employment",
            "responsibilities": e["bullets"], "technologies": list(find_skills(blob)),
        })
    return items


# ---------- projects ----------
def parse_projects(lines: list[tuple[bool, str]]) -> list[dict]:
    projects, cur = [], None
    for i, (is_bullet, text) in enumerate(lines):
        if is_bullet:
            if cur is None:
                cur = {"title_line": "Untitled project", "desc": []}
                projects.append(cur)
            cur["desc"].append(text)
            continue
        looks_title = len(text) <= 100 and not text.endswith(".")
        prev_bullet = i > 0 and lines[i - 1][0]
        if cur is None or (looks_title and cur["desc"] and prev_bullet):
            cur = {"title_line": text, "desc": []}
            projects.append(cur)
        else:
            cur["desc"].append(text)

    items = []
    for p in projects:
        title = re.split(r"\s*\|\s*|\s[–—-]\s", p["title_line"])[0].strip(" :-–—")
        blob = p["title_line"] + "\n" + "\n".join(p["desc"])
        items.append({"title": title or "Untitled project", "description": "\n".join(p["desc"]),
                      "technologies": list(find_skills(blob))})
    return items


# ---------- certifications & simple lists ----------
def parse_certifications(lines: list[tuple[bool, str]]) -> list[dict]:
    items = []
    for _, text in lines:
        if len(text) > 160:
            continue
        date = None
        dm = re.search(rf"{_MONTH}\s*,?\s*(?:19|20)\d{{2}}|(?<!\d)(?:19|20)\d{{2}}(?!\d)", text, re.I)
        if dm:
            date = dm.group(0)
            text = text.replace(dm.group(0), " ")
        text = re.sub(r"\s+", " ", text).strip(" ()[],-–|")
        parts = [p.strip(" ,()") for p in re.split(r"\s[–—-]\s|\s*\|\s|\s+by\s+|\s+from\s+", text, maxsplit=1)]
        if parts and parts[0]:
            items.append({"name": parts[0], "issuer": parts[1] if len(parts) > 1 and parts[1] else None, "date": date})
    return items


def parse_list(lines: list[tuple[bool, str]]) -> list[str]:
    return [t for _, t in lines if t]


def section_texts(header: list[str], sections: dict) -> dict[str, str]:
    """Text of each logical section (used for skill evidence and by the matcher)."""
    other_head = re.sub(r"\S*(?:github|linkedin)\.com\S*", " ", "\n".join(header))
    return {
        "skills": "\n".join(sections.get("skills", [])),
        "experience": "\n".join(sections.get("experience", []) + sections.get("internships", [])),
        "projects": "\n".join(sections.get("projects", [])),
        "certifications": "\n".join(sections.get("certifications", [])),
        "other": other_head + "\n" + "\n".join(
            sections.get("summary", []) + sections.get("achievements", [])
            + sections.get("extracurricular", []) + sections.get("publications", [])),
    }


def get_section_texts(text: str) -> dict[str, str]:
    header, sections = split_sections(text)
    return section_texts(header, sections)


# ---------- main entry ----------
def parse_resume(text: str) -> dict:
    header, sections = split_sections(text)
    norm = {k: normalize_lines(v) for k, v in sections.items()}
    warnings: list[str] = []

    personal = parse_personal(header, text)
    if not personal["full_name"]:
        warnings.append("Name could not be detected; please enter it manually.")
    if not personal["email"]:
        warnings.append("No email address found.")

    texts = section_texts(header, sections)
    skills: dict[str, dict] = {}
    for where, blob in texts.items():
        for name, cat in find_skills(blob, skills_section=(where == "skills")).items():
            skills.setdefault(name, {"name": name, "category": cat, "found_in": []})["found_in"].append(where)
    if "skills" not in sections:
        warnings.append("No dedicated Skills section found; skills were detected from other sections.")
    if not skills:
        warnings.append("No known technical skills detected.")

    experience = parse_experience(norm.get("experience", []), "experience") + \
        parse_experience(norm.get("internships", []), "internships")
    if not experience:
        warnings.append("No professional experience or internship section found; none assumed.")

    education = parse_education(norm.get("education", []))
    if not education:
        warnings.append("No education details detected.")
    projects = parse_projects(norm.get("projects", []))

    data = {
        "personal": personal,
        "summary": " ".join(sections["summary"]) if sections.get("summary") else None,
        "education": education,
        "skills": list(skills.values()),
        "experience": experience,
        "projects": projects,
        "certifications": parse_certifications(norm.get("certifications", [])),
        "achievements": parse_list(norm.get("achievements", [])),
        "publications": parse_list(norm.get("publications", [])),
        "extracurricular": parse_list(norm.get("extracurricular", [])),
        "sections_detected": list(sections.keys()),
        "warnings": warnings,
    }
    return ParsedResume.model_validate(data).model_dump()
