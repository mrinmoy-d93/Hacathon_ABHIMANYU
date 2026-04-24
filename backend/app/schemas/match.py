"""Match + field-worker feedback schemas (FRS §6.5, FR-5.1–FR-5.5)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class PendingMatch(BaseModel):
    id: str
    case_id: str
    person_name: str
    candidate_photo_url: str
    confidence_score: float
    tier: str
    created_at: datetime
    explanation: str


class ConfirmMatchResponse(BaseModel):
    confirmed: bool
    family_notified: bool
    provider_used: str
    confidence_score: float
    explanation: str


class NotMatchResponse(BaseModel):
    error_vector_captured: bool
    case_reopened: bool
    feedback_pool_size: int
    training_cycle_triggered: bool
    confidence_score: float
    explanation: str
