"""Case request/response schemas (FRS §6.2, FR-2.1–FR-2.6, FR-4.2)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    person_name: str = Field(min_length=2, max_length=255)
    year_missing: int = Field(ge=1900, le=2100)
    age_at_disappearance: int = Field(ge=0, le=120)
    last_seen_location: str = Field(min_length=2, max_length=255)
    identifying_marks: str | None = None


class CaseCreateResponse(BaseModel):
    case_id: str
    predicted_current_age: int


class PhotoOut(BaseModel):
    id: str
    supabase_url: str
    age_at_photo: int
    is_predicted_aged: bool


class PhotoUploadResponse(BaseModel):
    photo_id: str
    supabase_url: str


class MatchSummary(BaseModel):
    id: str
    candidate_photo_url: str
    confidence_score: float
    tier: str
    status: str


class CaseDetail(BaseModel):
    case_id: str
    person_name: str
    year_missing: int
    age_at_disappearance: int
    predicted_current_age: int
    last_seen_location: str
    identifying_marks: str | None
    status: str
    created_at: datetime
    photos: list[PhotoOut]
    matches: list[MatchSummary]


class ProcessResponse(BaseModel):
    status: str
    job_id: str


class ConfidenceDistribution(BaseModel):
    high: int
    medium: int
    low: int


class CaseResultMatch(BaseModel):
    match_id: str | None
    candidate_photo_url: str
    confidence_score: float
    tier: str
    explanation: str


class CaseResult(BaseModel):
    status: str
    aged_photo_url: str | None
    matches: list[CaseResultMatch]
    summary: str | None
    confidence_distribution: ConfidenceDistribution
    providers_used: dict[str, str]
    processing_time_seconds: float | None
    explanation: str
    confidence_score: float | None
