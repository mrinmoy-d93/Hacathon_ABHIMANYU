"""Face-aging service.

Runs SAM/HRFAE on Replicate to synthesise an aged photograph at the
predicted present-day age.
"""
from __future__ import annotations


async def age_progress(image_bytes: bytes, current_age: int, target_age: int) -> bytes:
    """Return PNG bytes of the aged face."""
    raise NotImplementedError("Wire up Replicate call in implementation phase")
