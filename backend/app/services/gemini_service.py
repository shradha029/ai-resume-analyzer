"""Optional Gemini explanation layer. The core analysis never depends on it."""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def is_configured() -> bool:
    return bool(settings.GEMINI_API_KEY.strip())


def build_prompt(analysis: dict, recs: list[dict]) -> str:
    gaps = "\n".join(f"- [{g['severity']}] {g['title']}" for g in analysis["gaps"][:10])
    todo = "\n".join(f"- {r['title']}: {r['action']}" for r in recs[:8])
    return (
        "You are a career-guidance assistant. Using ONLY the facts below, write a friendly plain-language summary "
        "(max 180 words) of how this resume compares with the job and what to do next. "
        "Do NOT invent skills, experience, certifications or achievements. Do NOT claim a chance of getting hired. "
        "Do not add facts that are not listed.\n\n"
        f"Target role: {analysis['target_role']}\n"
        f"Resume quality: {analysis.get('resume_quality_score')}/100; match: {analysis['match_score']}/100; "
        f"skill coverage: {analysis['skill_coverage_score']}/100\n"
        f"Detected gaps:\n{gaps}\n\nSuggested actions:\n{todo}\n"
    )


def explain(analysis: dict, recs: list[dict]) -> tuple[str | None, str]:
    """Return (text, status) where status is disabled | ok | error."""
    if not is_configured():
        return None, "disabled"
    try:
        r = httpx.post(URL.format(model=settings.GEMINI_MODEL), params={"key": settings.GEMINI_API_KEY},
                       json={"contents": [{"parts": [{"text": build_prompt(analysis, recs)}]}]}, timeout=30)
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return (text or None), ("ok" if text else "error")
    except Exception as exc:  # network, quota, bad key, unexpected response shape
        logger.warning("Gemini explanation failed: %s", type(exc).__name__)
        return None, "error"
