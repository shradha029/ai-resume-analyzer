"""PDF report generation (ReportLab)."""
import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BLUE, VIOLET, GREY = colors.HexColor("#3b5bdb"), colors.HexColor("#7048e8"), colors.HexColor("#868e96")


def _t(x) -> str:
    """Make arbitrary text safe for the built-in Helvetica font and Paragraph markup."""
    return escape(str(x if x is not None else "-").encode("cp1252", "replace").decode("cp1252"))


def _bar(label: str, value, color) -> Drawing:
    d = Drawing(440, 22)
    d.add(String(0, 7, label, fontName="Helvetica", fontSize=9))
    d.add(Rect(150, 4, 220, 12, fillColor=colors.HexColor("#e9ecef"), strokeColor=None))
    if value is not None:
        d.add(Rect(150, 4, 220 * max(0, min(value, 100)) / 100, 12, fillColor=color, strokeColor=None))
    d.add(String(378, 7, "unknown" if value is None else f"{value:.1f}%", fontName="Helvetica-Bold", fontSize=9))
    return d


def _table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#ced4da")),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2ff")), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    return t


def build_report(analysis: dict, resume: dict, job: dict, recs: list[dict], ai_summary: str | None = None) -> bytes:
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=20, textColor=BLUE, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=13, textColor=VIOLET, spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=GREY)
    cell = ParagraphStyle("c", parent=body, fontSize=8, leading=10)

    def P(x, st=body):
        return Paragraph(_t(x), st)

    def C(x):
        return Paragraph(_t(x), cell)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8 * cm, rightMargin=1.8 * cm, topMargin=1.6 * cm,
                            bottomMargin=1.6 * cm, title="Resume Analysis Report")
    el = [P("Resume Analysis Report", h1),
          P(f"Generated {datetime.now():%d %b %Y, %H:%M} | AI-Powered Resume Analyzer and Job-Specific Skill Gap Detection System", small)]

    # 1-2 candidate & target role
    p = resume["personal"]
    el += [P("1. Candidate information", h2), _table([
        ["Name", C(p["full_name"])], ["Email", C(p["email"])], ["Phone", C(p["phone"])],
        ["LinkedIn", C(p["linkedin"])], ["GitHub", C(p["github"])], ["Portfolio", C(p["portfolio"])],
    ], [3 * cm, 14 * cm], header=False)]
    el += [P("2. Target job role", h2), P(analysis["target_role"])]

    # 3 job summary
    sk = job["skills"]
    by = lambda lv: ", ".join(s["name"] for s in sk if s["level"] == lv) or "none detected"  # noqa: E731
    ex, ed = job["experience"], job["education"]
    exp_txt = ("entry-level" if ex["entry_level"] else f"{ex['min_years']}+ years") if ex["min_years"] is not None else "not stated"
    edu_txt = (ed["required_level_name"] or "not stated") + (f" in {', '.join(ed['fields'])}" if ed["fields"] else "")
    el += [P("3. Job description summary", h2),
           P(f"Mandatory skills: {by('mandatory')}"), P(f"Preferred skills: {by('preferred')}"),
           P(f"Optional skills: {by('optional')}"), P(f"Experience requirement: {exp_txt}"),
           P(f"Education requirement: {edu_txt}"),
           P(f"Soft skills mentioned: {', '.join(job['soft_skills']) or 'none'}")]

    # 4-6 scores
    el += [P("4-6. Scores", h2),
           _bar("Resume Quality Score", analysis.get("resume_quality_score"), BLUE),
           _bar("Resume-Job Match Score", analysis["match_score"], VIOLET),
           _bar("Skill Coverage Score", analysis["skill_coverage_score"], BLUE),
           _bar("Skill Match Score", analysis["skill_match_score"], VIOLET),
           _bar("Profile Readiness (heuristic)", analysis.get("profile_readiness_score"), GREY),
           P("These scores describe presentation and fit. They are not a probability of being shortlisted or hired.", small)]
    rows = [["Component", "Score", "Weight used", "Notes"]]
    for k, c in analysis["component_scores"].items():
        rows.append([k.capitalize(), "unknown" if c["score"] is None else f"{c['score']}", f"{c['weight_effective']:.0%}", C(" ".join(c["notes"]))])
    el += [Spacer(1, 6), _table(rows, [2.6 * cm, 1.8 * cm, 2.2 * cm, 10.4 * cm])]

    # 7 extracted skills
    cats = {}
    for s in resume["skills"]:
        cats.setdefault(s["category"], []).append(s["name"])
    el += [P("7. Extracted skills", h2)] + [P(f"{k.capitalize()}: {', '.join(v)}") for k, v in cats.items()]
    if not cats:
        el.append(P("No known technical skills were detected."))

    # 8-10 matched / partial / missing
    for n, (title, st) in enumerate([("8. Matched skills", "matched"), ("9. Partially matched skills", "partial"),
                                     ("10. Missing skills", "missing")]):
        ms = [m for m in analysis["skill_matches"] if m["status"] == st]
        el.append(P(title, h2))
        if not ms:
            el.append(P("None."))
            continue
        rows = [["Skill", "Requirement", "Credit", "Explanation"]] + [
            [C(m["skill"]), m["level"], f"{m['credit']:.2f}", C(m["explanation"])] for m in ms]
        el.append(_table(rows, [3.2 * cm, 2.2 * cm, 1.5 * cm, 10.1 * cm]))
    if analysis["additional_skills"]:
        el.append(P("Additional skills on the resume not requested by this job: " + ", ".join(analysis["additional_skills"]), small))

    # 11-13 gap analyses
    cs = analysis["component_scores"]
    el += [P("11. Experience gap analysis", h2)] + [P(x) for x in cs["experience"]["notes"]]
    el += [P("12. Education gap analysis", h2)] + [P(x) for x in cs["education"]["notes"]]
    el.append(P("13. Project relevance analysis", h2))
    el += [P(x) for x in cs["projects"]["notes"]]
    prj = analysis["details"].get("projects", [])
    if prj:
        rows = [["Project", "Matching job skills", "Relevance", "TF-IDF sim."]] + [
            [C(r["title"]), C(", ".join(r["matching_skills"]) or "-"), r["relevance"], f"{r['tfidf_similarity']:.2f}"] for r in prj]
        el.append(_table(rows, [5 * cm, 6.5 * cm, 2.2 * cm, 2.3 * cm]))

    # 14 recommendations
    el.append(P("14. Personalized recommendations", h2))
    if ai_summary:
        el += [P("AI-generated summary (Gemini, based only on the analysis above):", small), P(ai_summary)]
    for i, r in enumerate(recs, 1):
        el.append(P(f"{i}. [{r['priority'].upper()}] {r['title']}: {r['action']}", body))
        el.append(P("Why: " + r["reason"] + ("  Resources: " + "; ".join(f"{x['name']} ({x['url']})" for x in r["resources"]) if r["resources"] else ""), small))
    if not recs:
        el.append(P("No gaps detected that need action."))

    # 15 methodology
    el += [P("15. Scoring methodology and limitations", h2),
           P("Match = 0.40 Skills + 0.20 Experience + 0.15 Education + 0.15 Projects + 0.10 Certifications (weights configurable). "
             "Each component is 0-100. Components whose information is missing are marked unknown and excluded; the remaining weights "
             "are re-normalised."),
           P("Skill Match = sum(weight x credit) / sum(weight) x 100 with weights mandatory 1.0, preferred 0.6, optional 0.3. Credit: "
             "demonstrated 1.0, implied 0.85, listed only 0.70, related technology 0.35. Skill Coverage counts only demonstrated skills."),
           P("Resume Quality = section completeness 20 + skills presentation 20 + descriptions 25 + measurable achievements 15 + "
             "formatting 10 + education/certifications 10, using documented rules."),
           P(f"Method used: {analysis['method']}. TF-IDF similarity between resume and job text: {analysis['tfidf_similarity']}."
             + (f" Semantic similarity: {analysis['semantic_similarity']}." if analysis.get("semantic_similarity") is not None else "")),
           P("Limitations: parsing is rule-based and can miss or mis-read unusual layouts; scanned PDFs are not supported; skills outside "
             "the built-in dictionary are detected only from phrases such as 'experience with X'; grammar is not checked; semantic "
             "thresholds are initial values. Scores are decision-support indicators, not predictions of selection or employment.", small)]
    doc.build(el)
    return buf.getvalue()


def remove_report_files(analyses) -> None:
    """Delete generated report files from disk (called before DB rows are deleted)."""
    from pathlib import Path

    for a in analyses:
        for rep in a.reports:
            Path(rep.file_path).unlink(missing_ok=True)
