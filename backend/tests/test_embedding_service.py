from __future__ import annotations

import numpy as np
import pytest

from app.services import embedding_service


def test_mock_embedding_shape_and_norm():
    vec = embedding_service.get_embedding(b"seeded-face")
    assert vec.shape == (512,)
    assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-6)


def test_mock_embedding_is_deterministic():
    a = embedding_service.get_embedding(b"same")
    b = embedding_service.get_embedding(b"same")
    assert np.allclose(a, b)


def test_cosine_similarity_bounds():
    v = np.ones(8)
    assert embedding_service.cosine_similarity(v, v) == pytest.approx(1.0)
    assert embedding_service.cosine_similarity(v, -v) == pytest.approx(-1.0)
    assert embedding_service.cosine_similarity(np.array([1.0, 0.0]), np.array([0.0, 1.0])) == pytest.approx(0.0)


def test_cosine_similarity_handles_zero_vector():
    assert embedding_service.cosine_similarity(np.zeros(5), np.ones(5)) == 0.0
