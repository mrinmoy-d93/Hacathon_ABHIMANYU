from __future__ import annotations

import uuid

import numpy as np

from app.models import Case, CaseStatus, Photo, User, UserRole
from app.services import recognition_service


def _bootstrap(session):
    user = User(name="u", phone="+919811100099", location="X", role=UserRole.FAMILY)
    session.add(user)
    session.flush()
    cases = []
    for i in range(3):
        case = Case(
            case_id=f"KHJ-2024-0000{i+1}",
            person_name=f"Person {i}",
            year_missing=2010,
            age_at_disappearance=10,
            last_seen_location="Ahmedabad",
            status=CaseStatus.ACTIVE,
            created_by=user.id,
        )
        session.add(case)
        cases.append(case)
    session.flush()
    return cases


def test_find_matches_returns_top_k_sorted(session):
    cases = _bootstrap(session)
    query = np.array([1.0, 0.0, 0.0] + [0.0] * 509)

    # Photo 0 — identical vector (cos=1)
    session.add(Photo(id=uuid.uuid4(), case_id=cases[0].case_id, supabase_url="a", age_at_photo=10, embedding=query.tolist()))
    # Photo 1 — orthogonal (cos=0)
    orth = np.array([0.0, 1.0, 0.0] + [0.0] * 509)
    session.add(Photo(id=uuid.uuid4(), case_id=cases[1].case_id, supabase_url="b", age_at_photo=10, embedding=orth.tolist()))
    # Photo 2 — opposite (cos=-1)
    session.add(Photo(id=uuid.uuid4(), case_id=cases[2].case_id, supabase_url="c", age_at_photo=10, embedding=(-query).tolist()))
    session.flush()

    matches = recognition_service.find_matches(session, query, top_k=2)
    assert len(matches) == 2
    assert matches[0]["similarity_score"] > matches[1]["similarity_score"]
    assert matches[0]["case_id"] == cases[0].case_id


def test_find_matches_respects_exclude_case(session):
    cases = _bootstrap(session)
    query = np.array([1.0] * 8 + [0.0] * 504)
    session.add(Photo(id=uuid.uuid4(), case_id=cases[0].case_id, supabase_url="a", age_at_photo=10, embedding=query.tolist()))
    session.add(Photo(id=uuid.uuid4(), case_id=cases[1].case_id, supabase_url="b", age_at_photo=10, embedding=query.tolist()))
    session.flush()

    matches = recognition_service.find_matches(session, query, top_k=5, exclude_case_id=cases[0].case_id)
    assert all(m["case_id"] != cases[0].case_id for m in matches)
    assert len(matches) == 1
