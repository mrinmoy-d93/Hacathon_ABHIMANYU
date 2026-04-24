from datetime import datetime

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    age_at_disappearance: int = Field(ge=0, le=120)
    missing_year: int = Field(ge=1950, le=2100)
    last_location: str
    identifying_marks: str | None = None


class CaseResponse(BaseModel):
    id: int
    khj_id: str
    name: str
    age_at_disappearance: int
    missing_year: int
    predicted_present_age: int
    last_location: str
    status: str
    created_at: datetime
