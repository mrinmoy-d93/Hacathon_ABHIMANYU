"""Age-invariant face recognition (FRS §4.3 step 6, FR-3.5).

MVP implementation: full-table scan of ``photos.embedding`` with cosine
similarity computed in Python. This is O(N) but fine at the hackathon-scale
dataset (<10k photos).

TODO: once the dataset exceeds ~100k embeddings, replace the full scan with
pgvector's IVFFlat index (``SELECT ... ORDER BY embedding <=> :query LIMIT k``).
The Supabase ``vector`` extension is already enabled in the deployment guide.
"""
from __future__ import annotations

import heapq
import logging
from typing import TypedDict

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Photo
from app.services.embedding_service import cosine_similarity

logger = logging.getLogger(__name__)


class MatchCandidate(TypedDict):
    case_id: str
    photo_id: str
    similarity_score: float
    photo_url: str


def find_matches(
    session: Session,
    query_embedding: np.ndarray | list[float],
    top_k: int = 10,
    exclude_case_id: str | None = None,
) -> list[MatchCandidate]:
    """Return the top-k most similar photos by cosine similarity."""
    query = np.asarray(query_embedding, dtype=np.float64)

    stmt = select(Photo).where(Photo.embedding.is_not(None))
    if exclude_case_id is not None:
        stmt = stmt.where(Photo.case_id != exclude_case_id)

    scored: list[tuple[float, Photo]] = []
    for photo in session.execute(stmt).scalars():
        if not photo.embedding:
            continue
        score = cosine_similarity(query, photo.embedding)
        scored.append((score, photo))

    if not scored:
        return []

    top = heapq.nlargest(top_k, scored, key=lambda pair: pair[0])
    return [
        MatchCandidate(
            case_id=photo.case_id,
            photo_id=str(photo.id),
            similarity_score=float(score),
            photo_url=photo.supabase_url,
        )
        for score, photo in top
    ]
