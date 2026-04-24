"""Face detection via InsightFace (CPU).

Production path: ``insightface.app.FaceAnalysis(name='buffalo_l',
providers=['CPUExecutionProvider'])``. The model is downloaded on first
request (~300 MB) and cached in ``~/.insightface``.

Sandbox / test path: when ``USE_MOCK_AI`` is true the real model is never
loaded. ``insightface`` / ``onnxruntime`` / ``cv2`` imports are wrapped in
``try/except`` so the module imports cleanly even when the deps aren't
installed (required for pytest in the sandbox per the Phase 3 brief).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings
from app.services._mock_ai import mock_detect_face
from app.services.ai_common import NoFaceDetectedError

logger = logging.getLogger(__name__)

try:  # Optional — real install happens in the HF Spaces Dockerfile (Phase 6).
    import cv2  # type: ignore
    import numpy as _np  # type: ignore
except ImportError:  # pragma: no cover - exercised only in sandbox
    cv2 = None  # type: ignore
    _np = None  # type: ignore

try:
    from insightface.app import FaceAnalysis  # type: ignore

    _HAS_INSIGHTFACE = True
except ImportError:  # pragma: no cover
    FaceAnalysis = None  # type: ignore
    _HAS_INSIGHTFACE = False

_face_app: Any | None = None


def _load_face_app() -> Any:
    """Lazy-load the buffalo_l pack on first call."""
    global _face_app
    if _face_app is not None:
        return _face_app
    if not _HAS_INSIGHTFACE:
        raise RuntimeError("insightface is not installed in this environment")

    logger.info("loading InsightFace buffalo_l on CPU — first call will download weights")
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    _face_app = app
    return _face_app


def _fetch_bytes(image_bytes_or_url: bytes | str) -> bytes:
    if isinstance(image_bytes_or_url, bytes):
        return image_bytes_or_url
    resp = httpx.get(image_bytes_or_url, timeout=10.0, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


def _largest_face(faces: list) -> Any:
    def area(face: Any) -> float:
        x1, y1, x2, y2 = face.bbox
        return float((x2 - x1) * (y2 - y1))

    return max(faces, key=area)


def detect_face(image_bytes_or_url: bytes | str) -> dict:
    """Detect the primary face in an image.

    Returns a dict with keys ``bbox``, ``landmarks_68``, ``confidence`` and
    ``face_img_bytes`` (PNG-encoded cropped face).

    Raises :class:`NoFaceDetectedError` if no face is found. When multiple
    faces are present, the one with the largest bounding-box area is returned.
    """
    if get_settings().use_mock_ai:
        return mock_detect_face(image_bytes_or_url)

    if cv2 is None or _np is None:
        raise RuntimeError("OpenCV is required for face detection")

    image_bytes = _fetch_bytes(image_bytes_or_url)
    arr = _np.frombuffer(image_bytes, dtype=_np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise NoFaceDetectedError("image bytes could not be decoded")

    faces = _load_face_app().get(img)
    if not faces:
        raise NoFaceDetectedError("no face detected by InsightFace")

    face = _largest_face(faces) if len(faces) > 1 else faces[0]
    x1, y1, x2, y2 = [int(max(0, v)) for v in face.bbox]
    face_crop = img[y1:y2, x1:x2]
    ok, buf = cv2.imencode(".png", face_crop)
    if not ok:
        raise NoFaceDetectedError("failed to encode cropped face")

    landmarks = (
        face.landmark_2d_106.tolist()
        if hasattr(face, "landmark_2d_106") and face.landmark_2d_106 is not None
        else face.kps.tolist()
    )
    return {
        "bbox": [float(x1), float(y1), float(x2), float(y2)],
        "landmarks_68": landmarks,
        "confidence": float(face.det_score),
        "face_img_bytes": buf.tobytes(),
    }
