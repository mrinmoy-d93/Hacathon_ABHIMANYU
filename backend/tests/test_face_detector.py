from __future__ import annotations

from app.services import face_detector


def test_mock_detect_returns_expected_shape():
    result = face_detector.detect_face(b"arbitrary-image-bytes")
    assert set(result) == {"bbox", "landmarks_68", "confidence", "face_img_bytes"}
    assert len(result["bbox"]) == 4
    assert len(result["landmarks_68"]) == 68
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["face_img_bytes"], bytes)


def test_mock_detect_is_deterministic():
    a = face_detector.detect_face(b"same-input")
    b = face_detector.detect_face(b"same-input")
    assert a == b


def test_mock_detect_accepts_url_string():
    result = face_detector.detect_face("https://example.com/face.jpg")
    assert "bbox" in result
    assert result["confidence"] > 0
