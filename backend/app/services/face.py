"""Face detection and embedding service.

In the cloud-native deployment the heavy CV pipeline (InsightFace + ArcFace)
runs on Replicate. This module wraps those API calls.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FaceEmbedding:
    vector: list[float]
    model_version: str


async def detect_and_embed(image_bytes: bytes) -> FaceEmbedding:
    """Call Replicate-hosted InsightFace/ArcFace pipeline. Returns 512-d embedding."""
    raise NotImplementedError("Wire up Replicate call in implementation phase")
