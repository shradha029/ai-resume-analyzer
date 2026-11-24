from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class JobAnalyzeRequest(BaseModel):
    target_role: str = Field(min_length=2, max_length=100)
    job_description: str = Field(min_length=40, max_length=20000)

    @field_validator("target_role", "job_description")
    @classmethod
    def strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class JobOut(BaseModel):
    id: int
    target_role: str
    parsed: dict[str, Any]
    created_at: datetime


class JobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_role: str
    created_at: datetime


class AnalysisCreateRequest(BaseModel):
    resume_id: int
    job_id: int
    weights: Optional[dict[str, float]] = Field(
        None, description="Optional overrides for skills, experience, education, projects, certifications")


class SkillMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: str
    category: str
    level: str
    weight: float
    status: str
    credit: float
    custom: bool
    demonstrated: bool
    evidence: list[str]
    explanation: str


class GapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gap_type: str
    severity: str
    title: str
    description: str


class AnalysisOut(BaseModel):
    id: int
    resume_id: int
    job_id: int
    target_role: str
    match_score: Optional[float]
    skill_match_score: Optional[float]
    skill_coverage_score: Optional[float]
    component_scores: dict[str, Any]
    skill_matches: list[SkillMatchOut]
    gaps: list[GapOut]
    additional_skills: list[str]
    tfidf_similarity: Optional[float]
    semantic_similarity: Optional[float]
    method: str
    details: dict[str, Any]
    resume_quality_score: Optional[float] = None
    profile_readiness_score: Optional[float] = None
    quality: Optional[dict[str, Any]] = None
    created_at: datetime


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    priority: str
    title: str
    action: str
    reason: str
    resources: list[dict[str, str]]


class RecommendationsOut(BaseModel):
    recommendations: list[RecommendationOut]
    ai_summary: Optional[str] = None
    ai_status: str = "disabled"  # disabled | ok | error | not_requested


class AnalysisSummary(BaseModel):
    id: int
    resume_id: int
    resume_filename: str
    target_role: str
    match_score: Optional[float]
    skill_coverage_score: Optional[float]
    created_at: datetime
