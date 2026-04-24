"""ArcFace embedding + cosine similarity helpers (FRS §4.3 step 2).

In production the embedding is produced by the same ``FaceAnalysis`` instance
that ran detection — InsightFace returns a 512-d ArcFace vector alongside the
detection result. We re-run here when called standalone to keep this service
usable after an external re-crop.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from app.config import get_settings
from app.services._mock_ai import mock_embedding

logger = logging.getLogger(__name__)

try:
    import cv2  # type: ignore
    from insightface.app import FaceAnalysis  # type: ignore

    _HAS_INSIGHTFACE = True
except ImportError:  # pragma: no cover - sandbox path
    cv2 = None  # type: ignore
    FaceAnalysis = None  # type: ignore
    _HAS_INSIGHTFACE = False

_face_app: Any | None = None


def _load_face_app() -> Any:
    global _face_app
    if _face_app is not None:
        return _face_app
    if not _HAS_INSIGHTFACE:
        raise RuntimeError("insightface is not installed in this environment")
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    _face_app = app
    return _face_app


def _normalise(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    return vec if norm == 0 else (vec / norm)


def get_embedding(face_img_bytes: bytes) -> np.ndarray:
    """Return a 512-d L2-normalised face embedding."""
    if get_settings().use_mock_ai:
        return mock_embedding(face_img_bytes)

    if cv2 is None:
        raise RuntimeError("OpenCV is required for embedding extraction")

    arr = np.frombuffer(face_img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("cannot decode face image bytes")

    faces = _load_face_app().get(img)
    if not faces:
        raise ValueError("no face detected in cropped image")
    embedding = np.asarray(faces[0].embedding, dtype=np.float64)
    return _normalise(embedding)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors, mapped to the standard [-1, 1] range."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
