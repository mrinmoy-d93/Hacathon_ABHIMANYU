"""Aging-trajectory computation in ArcFace embedding space (FRS §4.3 step 3).

Given N ≥ 2 photographs of the same individual, each tagged with an age, we
model the face embedding as a linear function of age::

    e(age) ≈ e_base + (age − age_base) · Δv

For two photographs this reduces to the closed form::

    Δv = (e₂ − e₁) / (a₂ − a₁)      [age-wise rate vector, 512-d]

For three or more photographs we fit a per-dimension least-squares slope
using :func:`numpy.polyfit` (degree 1) — this is identical to the closed form
when N = 2 and robust to minor embedding noise when N > 2.

The output Δv is NOT L2-normalised: its magnitude carries the aging *speed*
per year and is consumed by ``aging_service`` to prime the GAN latent code.
"""
from __future__ import annotations

import logging
from typing import Iterable, TypedDict

import numpy as np

from app.services.ai_common import InsufficientPhotosError

logger = logging.getLogger(__name__)

MIN_PHOTOS = 2  # FRS FR-2.3


class TrajectoryPhoto(TypedDict):
    embedding: list[float] | np.ndarray
    age_at_photo: int


class Trajectory(TypedDict):
    base_embedding: list[float]
    base_age: int
    aging_direction: list[float]
    photo_count: int


def compute_trajectory(photos: Iterable[TrajectoryPhoto]) -> Trajectory:
    """Return the aging direction vector Δv (per-dimension slope) and the anchor."""
    photo_list = list(photos)
    if len(photo_list) < MIN_PHOTOS:
        raise InsufficientPhotosError(
            f"At least {MIN_PHOTOS} photos are required (FRS FR-2.3); got {len(photo_list)}."
        )

    ordered = sorted(photo_list, key=lambda p: p["age_at_photo"])
    ages = np.array([p["age_at_photo"] for p in ordered], dtype=np.float64)
    embeddings = np.array([np.asarray(p["embedding"], dtype=np.float64) for p in ordered])

    if len(ordered) == 2:
        delta_age = ages[1] - ages[0]
        if delta_age == 0:
            raise InsufficientPhotosError("photos must have distinct ages")
        delta_v = (embeddings[1] - embeddings[0]) / delta_age
    else:
        # Per-dimension least-squares slope. polyfit returns [slope, intercept].
        slopes = np.polyfit(ages, embeddings, deg=1)[0]
        delta_v = slopes

    base_idx = 0
    return Trajectory(
        base_embedding=embeddings[base_idx].tolist(),
        base_age=int(ages[base_idx]),
        aging_direction=delta_v.tolist(),
        photo_count=len(ordered),
    )
