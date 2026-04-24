"""Alert routing + geo-clustering.

Consumes the scoring result and the matched case to decide:

* ``high``   — create a confirmed :class:`Match` row, auto-assign a field
              worker whose registered location is closest to the case's
              ``last_seen_location`` (geocoded via free Nominatim).
* ``medium`` — create a :class:`Match` row with status=pending (human review).
* ``low``    — no Match row; the event is logged to audit only.

A side-effect of every call is a geo-clustering check: if the case joins a
hot-spot of 3 or more cases within ``GEO_CLUSTER_RADIUS_KM`` kilometres and
``GEO_CLUSTER_WINDOW_DAYS`` days, a ``geo_alert`` audit entry is emitted.
"""
from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Case, Match, MatchStatus, MatchTier, User, UserRole
from app.services import audit_service

logger = logging.getLogger(__name__)

GEO_CLUSTER_RADIUS_KM = 10.0
GEO_CLUSTER_WINDOW_DAYS = 7
GEO_CLUSTER_MIN_COUNT = 3


class RouteResult(TypedDict):
    action: str
    match_id: str | None
    assigned_field_worker_id: str | None
    cluster_alert: bool


# ─── geocoding ────────────────────────────────────────────────────────────
@lru_cache(maxsize=512)
def _geocode(location: str) -> tuple[float, float] | None:
    """Return ``(lat, lon)`` via Nominatim or ``None`` on failure."""
    if not location:
        return None
    try:
        from geopy.geocoders import Nominatim  # lazy import

        geolocator = Nominatim(user_agent="khojo-alert-router", timeout=5)
        hit = geolocator.geocode(location)
    except Exception as exc:  # noqa: BLE001
        logger.warning("geocoding failed for %r: %s", location, exc)
        return None
    if hit is None:
        return None
    return (float(hit.latitude), float(hit.longitude))


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


# ─── field-worker assignment ──────────────────────────────────────────────
def _assign_field_worker(session: Session, case: Case) -> User | None:
    """Pick the field worker closest to ``case.last_seen_location``.

    Ties and geocode failures fall back to the field worker with the fewest
    currently-pending matches — this yields round-robin behaviour in the
    common case where Nominatim is unavailable.
    """
    workers = session.execute(
        select(User).where(User.role == UserRole.FIELD_WORKER)
    ).scalars().all()
    if not workers:
        return None

    case_coords = _geocode(case.last_seen_location)

    scored: list[tuple[float, User]] = []
    if case_coords:
        for worker in workers:
            worker_coords = _geocode(worker.location or "")
            distance = _haversine_km(case_coords, worker_coords) if worker_coords else math.inf
            scored.append((distance, worker))
        scored.sort(key=lambda pair: pair[0])
        # If the nearest worker has a finite distance, pick them.
        if scored and math.isfinite(scored[0][0]):
            return scored[0][1]

    # Fallback: worker with fewest currently-pending matches.
    pending_count = dict(
        session.execute(
            select(Match.field_worker_id, func.count(Match.id))
            .where(Match.status == MatchStatus.PENDING)
            .group_by(Match.field_worker_id)
        ).all()
    )
    workers.sort(key=lambda w: pending_count.get(w.id, 0))
    return workers[0]


# ─── geo-clustering ───────────────────────────────────────────────────────
def _check_geo_cluster(session: Session, case: Case, actor_id: uuid.UUID | None) -> bool:
    case_coords = _geocode(case.last_seen_location)
    if not case_coords:
        return False

    cutoff = datetime.now(timezone.utc) - timedelta(days=GEO_CLUSTER_WINDOW_DAYS)
    recent = session.execute(
        select(Case).where(Case.created_at >= cutoff, Case.case_id != case.case_id)
    ).scalars().all()

    cluster = [case]
    for other in recent:
        other_coords = _geocode(other.last_seen_location)
        if other_coords and _haversine_km(case_coords, other_coords) <= GEO_CLUSTER_RADIUS_KM:
            cluster.append(other)

    if len(cluster) < GEO_CLUSTER_MIN_COUNT:
        return False

    audit_service.write_audit(
        session,
        action="geo_alert",
        actor_id=actor_id,
        model_version=None,
        prompt_version=None,
        input_data={
            "case_id": case.case_id,
            "radius_km": GEO_CLUSTER_RADIUS_KM,
            "window_days": GEO_CLUSTER_WINDOW_DAYS,
        },
        output_data={"cluster_size": len(cluster), "case_ids": [c.case_id for c in cluster]},
    )
    return True


# ─── public entry point ──────────────────────────────────────────────────
def route(
    session: Session,
    case: Case,
    *,
    candidate_photo_id: uuid.UUID | str,
    similarity_score: float,
    tier: str,
    actor_id: uuid.UUID | None = None,
) -> RouteResult:
    """Create (or skip) a Match row and return a summary for the pipeline."""
    cluster_alert = _check_geo_cluster(session, case, actor_id)

    if tier == "low":
        audit_service.write_audit(
            session,
            action="match.inconclusive",
            actor_id=actor_id,
            model_version=None,
            prompt_version=None,
            input_data={"case_id": case.case_id, "candidate_photo_id": str(candidate_photo_id)},
            output_data={"similarity": similarity_score, "tier": tier},
            confidence_score=similarity_score,
        )
        return RouteResult(
            action="mark_inconclusive",
            match_id=None,
            assigned_field_worker_id=None,
            cluster_alert=cluster_alert,
        )

    assigned: User | None = None
    status = MatchStatus.PENDING
    match_tier = MatchTier.HIGH if tier == "high" else MatchTier.MEDIUM
    action = "auto_alert_field_worker" if tier == "high" else "queue_for_human_review"

    if tier == "high":
        assigned = _assign_field_worker(session, case)

    photo_uuid = (
        candidate_photo_id
        if isinstance(candidate_photo_id, uuid.UUID)
        else uuid.UUID(str(candidate_photo_id))
    )
    match = Match(
        case_id=case.case_id,
        candidate_photo_id=photo_uuid,
        confidence_score=similarity_score,
        tier=match_tier,
        status=status,
        field_worker_id=assigned.id if assigned else None,
    )
    session.add(match)
    session.flush()

    audit_service.write_audit(
        session,
        action=f"match.{tier}",
        actor_id=actor_id,
        model_version=None,
        prompt_version=None,
        input_data={"case_id": case.case_id, "candidate_photo_id": str(candidate_photo_id)},
        output_data={
            "match_id": str(match.id),
            "assigned_field_worker_id": str(assigned.id) if assigned else None,
            "tier": tier,
        },
        confidence_score=similarity_score,
    )

    return RouteResult(
        action=action,
        match_id=str(match.id),
        assigned_field_worker_id=str(assigned.id) if assigned else None,
        cluster_alert=cluster_alert,
    )
