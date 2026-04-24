from __future__ import annotations

import numpy as np
import pytest

from app.services import trajectory_service
from app.services.ai_common import InsufficientPhotosError


def test_one_photo_raises():
    with pytest.raises(InsufficientPhotosError):
        trajectory_service.compute_trajectory([{"embedding": [0.0] * 8, "age_at_photo": 10}])


def test_two_photos_closed_form():
    e1 = np.array([0.0, 0.0, 0.0])
    e2 = np.array([2.0, 4.0, 6.0])
    photos = [
        {"embedding": e1.tolist(), "age_at_photo": 10},
        {"embedding": e2.tolist(), "age_at_photo": 20},
    ]
    traj = trajectory_service.compute_trajectory(photos)
    expected_direction = (e2 - e1) / 10.0
    assert np.allclose(traj["aging_direction"], expected_direction.tolist())
    assert traj["base_age"] == 10
    assert traj["photo_count"] == 2


def test_three_plus_photos_uses_regression():
    # Construct embeddings perfectly on a line: e = e0 + (age - 10) * slope
    slope = np.array([0.1, -0.2, 0.3])
    e0 = np.array([1.0, 2.0, 3.0])
    ages = [10, 15, 20, 25]
    photos = [
        {"embedding": (e0 + (a - 10) * slope).tolist(), "age_at_photo": a} for a in ages
    ]
    traj = trajectory_service.compute_trajectory(photos)
    assert np.allclose(traj["aging_direction"], slope.tolist(), atol=1e-9)
    assert traj["photo_count"] == 4


def test_photos_with_same_age_raise():
    with pytest.raises(InsufficientPhotosError):
        trajectory_service.compute_trajectory(
            [
                {"embedding": [1.0, 0.0], "age_at_photo": 10},
                {"embedding": [0.0, 1.0], "age_at_photo": 10},
            ]
        )
