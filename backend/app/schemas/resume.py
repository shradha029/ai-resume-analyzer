from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class PersonalInfo(BaseModel):
    full_name: Optional[str] = Field(None, max_length=150)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=40)
    linkedin: Optional[str] = Field(None, max_length=300)
    github: Optional[str] = Field(None, max_length=300)
    portfolio: Optional[str] = Field(None, max_length=300)


class EducationItem(BaseModel):
    degree: Optional[str] = Field(None, max_length=200)
    institution: Optional[str] = Field(None, max_length=200)
    graduation_year: Optional[int] = Field(None, ge=1950, le=2100)
    cgpa: Optional[float] = Field(None, ge=0, le=100)
    cgpa_scale: Optional[float] = Field(None, gt=0, le=100)
    percentage: Optional[float] = Field(None, ge=0, le=100)
    coursework: list[str] = Field(default_factory=list, max_length=50)


class SkillItem(BaseModel):
    name: str = Field(max_length=80)
    category: str = Field(max_length=30)
    found_in: list[str] = Field(default_factory=list, max_length=10)


class ExperienceItem(BaseModel):
    organization: Optional[str] = Field(None, max_length=200)
    title: Optional[str] = Field(None, max_length=200)
    duration: Optional[str] = Field(None, max_length=100)
    type: Literal["employment", "internship"] = "employment"
    responsibilities: list[str] = Field(default_factory=list, max_length=30)
    technologies: list[str] = Field(default_factory=list, max_length=50)


class ProjectItem(BaseModel):
    title: str = Field(max_length=200)
    description: str = Field("", max_length=3000)
    technologies: list[str] = Field(default_factory=list, max_length=50)


class CertificationItem(BaseModel):
    name: str = Field(max_length=250)
    issuer: Optional[str] = Field(None, max_length=200)
    date: Optional[str] = Field(None, max_length=50)


class ParsedResume(BaseModel):
    personal: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: Optional[str] = Field(None, max_length=2000)
    education: list[EducationItem] = Field(default_factory=list, max_length=20)
    skills: list[SkillItem] = Field(default_factory=list, max_length=300)
    experience: list[ExperienceItem] = Field(default_factory=list, max_length=30)
    projects: list[ProjectItem] = Field(default_factory=list, max_length=30)
    certifications: list[CertificationItem] = Field(default_factory=list, max_length=50)
    achievements: list[str] = Field(default_factory=list, max_length=50)
    publications: list[str] = Field(default_factory=list, max_length=50)
    extracurricular: list[str] = Field(default_factory=list, max_length=50)
    sections_detected: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    file_size: int
    page_count: int
    status: str
    uploaded_at: datetime


class ExtractedOut(BaseModel):
    resume_id: int
    data: ParsedResume
    is_user_edited: bool
    updated_at: datetime
