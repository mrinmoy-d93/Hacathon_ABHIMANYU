"""Health probe schema (FRS NFR-2, NFR-8)."""
from __future__ import annotations

from pydantic import BaseModel


class ProviderHealth(BaseModel):
    openai: bool
    groq: bool
    hf: bool
    replicate: bool


class HealthResponse(BaseModel):
    status: str
    db: bool
    providers: ProviderHealth
    version: str
    uptime_seconds: float
