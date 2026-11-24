from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now():
    return datetime.now(timezone.utc)


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    target_role: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    parsed: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    analyses: Mapped[list["ResumeAnalysis"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_descriptions.id", ondelete="CASCADE"), index=True)
    target_role: Mapped[str] = mapped_column(String(100))
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    skill_coverage_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    tfidf_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    semantic_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    method: Mapped[str] = mapped_column(String(40))
    component_scores: Mapped[dict] = mapped_column(JSON)
    additional_skills: Mapped[list] = mapped_column(JSON)
    details: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    resume = relationship("Resume", back_populates="analyses")
    job = relationship("JobDescription", back_populates="analyses")
    skill_matches: Mapped[list["SkillMatch"]] = relationship(back_populates="analysis", cascade="all, delete-orphan",
                                                              order_by="SkillMatch.id")
    skill_gaps: Mapped[list["SkillGap"]] = relationship(back_populates="analysis", cascade="all, delete-orphan",
                                                         order_by="SkillGap.id")
    recommendations = relationship("Recommendation", back_populates="analysis", cascade="all, delete-orphan",
                                   order_by="Recommendation.id")
    reports = relationship("AnalysisReport", back_populates="analysis", cascade="all, delete-orphan")


class SkillMatch(Base):
    __tablename__ = "skill_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("resume_analyses.id", ondelete="CASCADE"), index=True)
    skill: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(30))
    level: Mapped[str] = mapped_column(String(15))
    weight: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(15))  # matched | partial | missing
    credit: Mapped[float] = mapped_column(Float)
    custom: Mapped[bool] = mapped_column(default=False)
    demonstrated: Mapped[bool] = mapped_column(default=False)
    evidence: Mapped[list] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)

    analysis: Mapped[ResumeAnalysis] = relationship(back_populates="skill_matches")


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("resume_analyses.id", ondelete="CASCADE"), index=True)
    gap_type: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)

    analysis: Mapped[ResumeAnalysis] = relationship(back_populates="skill_gaps")
