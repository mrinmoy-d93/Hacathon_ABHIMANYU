"""Populate a KHOJO database with demo users, cases, photos, and default settings.

Usage:
    DATABASE_URL=postgresql://... python scripts/seed_demo_data.py

Run against a dev/staging database only. The script is idempotent on phone
numbers + case IDs: if a seed row already exists it is skipped.
"""
from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# Allow "python scripts/seed_demo_data.py" from the repo root.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models import (  # noqa: E402
    AppSettings,
    Case,
    CaseStatus,
    Photo,
    User,
    UserRole,
)


# Public-domain portrait stock (Unsplash, no-attribution CDN URLs).
_STOCK_PHOTOS = [
    "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde",
    "https://images.unsplash.com/photo-1544005313-94ddf0286df2",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d",
    "https://images.unsplash.com/photo-1502685104226-ee32379fefbe",
    "https://images.unsplash.com/photo-1463453091185-61582044d556",
]


def _random_embedding(rng: random.Random) -> list[float]:
    # Normally-distributed, L2-normalised — mimics ArcFace output shape.
    vec = np.array([rng.gauss(0.0, 1.0) for _ in range(512)], dtype=np.float64)
    norm = float(np.linalg.norm(vec)) or 1.0
    return (vec / norm).tolist()


def _get_or_create_user(session: Session, *, phone: str, **fields) -> User:
    existing = session.execute(select(User).where(User.phone == phone)).scalar_one_or_none()
    if existing:
        return existing
    user = User(phone=phone, **fields)
    session.add(user)
    session.flush()
    return user


def _get_or_create_case(session: Session, *, case_id: str, **fields) -> Case:
    existing = session.get(Case, case_id)
    if existing:
        return existing
    case = Case(case_id=case_id, **fields)
    session.add(case)
    session.flush()
    return case


def _upsert_setting(session: Session, key: str, value) -> None:
    existing = session.get(AppSettings, key)
    if existing:
        existing.value = value
        existing.updated_at = datetime.now(timezone.utc)
        return
    session.add(AppSettings(key=key, value=value))


def seed(database_url: str) -> None:
    engine = create_engine(database_url, future=True)
    rng = random.Random(20260424)

    with Session(engine) as session:
        family = _get_or_create_user(
            session,
            name="Priya Sharma",
            phone="+919812300001",
            location="Ahmedabad, Gujarat",
            role=UserRole.FAMILY,
        )
        field_worker = _get_or_create_user(
            session,
            name="Ravi Patel",
            phone="+919812300002",
            location="Surat, Gujarat",
            role=UserRole.FIELD_WORKER,
        )
        admin = _get_or_create_user(
            session,
            name="Inspector A. Shah",
            phone="+919812300003",
            location="Gandhinagar, Gujarat",
            role=UserRole.ADMIN,
        )

        case_specs = [
            ("KHJ-2024-00001", "Arjun Desai", 2009, 10, "Old City, Ahmedabad", CaseStatus.ACTIVE),
            ("KHJ-2024-00002", "Meera Joshi", 2015, 7, "Kalupur Station, Ahmedabad", CaseStatus.ACTIVE),
            ("KHJ-2024-00003", "Kabir Kumar", 2018, 14, "Surat Railway Stn.", CaseStatus.UNDER_REVIEW),
            ("KHJ-2024-00004", "Ananya Patel", 2012, 9, "Vadodara Bus Stand", CaseStatus.FOUND),
            ("KHJ-2024-00005", "Rohan Mehta", 2008, 16, "Rajkot Market", CaseStatus.CLOSED),
        ]

        for case_id, name, year_missing, age_dis, location, status in case_specs:
            case = _get_or_create_case(
                session,
                case_id=case_id,
                person_name=name,
                year_missing=year_missing,
                age_at_disappearance=age_dis,
                last_seen_location=location,
                identifying_marks=None,
                status=status,
                created_by=family.id,
            )

            # Skip photo seeding if this case already has photos.
            if case.photos:
                continue

            for i in range(2):
                session.add(
                    Photo(
                        id=uuid.uuid4(),
                        case_id=case.case_id,
                        supabase_url=_STOCK_PHOTOS[(hash(case.case_id) + i) % len(_STOCK_PHOTOS)],
                        age_at_photo=age_dis + i * 2,
                        embedding=_random_embedding(rng),
                        is_predicted_aged=False,
                    )
                )

        # Defaults per FRS §6.6 Tab 4.
        _upsert_setting(session, "confidence_threshold", 0.60)
        _upsert_setting(session, "auto_alert_threshold", 0.80)
        _upsert_setting(session, "geo_clustering_radius_km", 5)
        _upsert_setting(session, "geo_clustering_min_count", 3)
        _upsert_setting(session, "gpt4o_enabled", True)
        _upsert_setting(session, "geo_clustering_enabled", True)
        _upsert_setting(session, "active_model_version", "v1.0")

        session.commit()
        print(
            f"seeded: users={{family: {family.id}, field_worker: {field_worker.id}, admin: {admin.id}}}, "
            f"cases={len(case_specs)}, settings=7"
        )


def main() -> int:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set — refusing to run.", file=sys.stderr)
        return 1
    seed(url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
