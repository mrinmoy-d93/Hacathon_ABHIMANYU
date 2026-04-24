"""Admin console schemas (FRS §6.6 five tabs)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ConfidenceDistribution(BaseModel):
    high: int
    medium: int
    low: int


class RecentActivityItem(BaseModel):
    id: int
    action: str
    timestamp: datetime
    confidence_score: float | None


class AdminDashboard(BaseModel):
    total_cases: int
    active_searches: int
    matches_found: int
    review_pending: int
    confidence_distribution: ConfidenceDistribution
    recent_activity: list[RecentActivityItem]


class AdminCaseRow(BaseModel):
    case_id: str
    person_name: str
    status: str
    predicted_current_age: int
    last_seen_location: str
    confidence_score: float | None
    assigned_field_worker_id: str | None


class AdminCasesPage(BaseModel):
    items: list[AdminCaseRow]
    page: int
    page_size: int
    total: int


class AdminCaseRejectRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1024)


class AdminActionResponse(BaseModel):
    case_id: str
    action: str
    status: str


class FieldWorkerRow(BaseModel):
    id: str
    name: str
    zone: str | None
    verification_count: int
    accuracy_score: float


class FieldWorkerAssign(BaseModel):
    user_id: str
    zone: str = Field(min_length=1, max_length=128)


class FieldWorkerUpdate(BaseModel):
    zone: str | None = None
    leave_status: str | None = Field(default=None, pattern=r"^(active|on_leave)$")


class SettingsOut(BaseModel):
    confidence_threshold: float
    auto_alert_threshold: float
    gpt4o_enabled: bool
    geo_clustering_enabled: bool
    current_model_version: str


class SettingsUpdate(BaseModel):
    confidence_threshold: float | None = Field(default=None, ge=0.40, le=0.90)
    auto_alert_threshold: float | None = Field(default=None, ge=0.60, le=0.99)
    gpt4o_enabled: bool | None = None
    geo_clustering_enabled: bool | None = None


class AuditEntry(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: int
    timestamp: datetime
    actor_id: str | None
    action: str
    model_version: str | None
    confidence_score: float | None
    input_hash: str
    output_hash: str


class AuditLogPage(BaseModel):
    items: list[AuditEntry]
    page: int
    page_size: int
    total: int
