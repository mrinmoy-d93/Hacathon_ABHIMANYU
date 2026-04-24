"""Shared exceptions and primitives for the AI pipeline.

Every AI service in ``app.services`` depends on these. The circuit breaker is
deliberately in-process and state-only — for distributed deployments it should
be swapped for a Redis-backed implementation, but the per-replica version is
sufficient for the single-dyno Hugging Face Spaces deployment (FRS §7.3).
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class AIError(RuntimeError):
    """Base class for AI pipeline errors."""


class NoFaceDetectedError(AIError):
    """Raised when face detection finds zero faces in an image."""


class InsufficientPhotosError(AIError):
    """Raised when fewer than the required photos are supplied (FRS FR-2.3)."""


class ProviderUnavailableError(AIError):
    """Raised by a single provider when its circuit is open or call fails."""


class AllProvidersFailedError(AIError):
    """Raised when every provider in a fallback chain has failed."""


@dataclass
class CircuitBreaker:
    """5-failure / 60-second cooldown per provider (FRS NFR-5).

    Thread-safe so multiple Uvicorn workers can share a single instance.
    """

    name: str
    threshold: int = 5
    cooldown_seconds: float = 60.0
    failures: int = 0
    opened_at: float | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def is_open(self) -> bool:
        with self._lock:
            if self.opened_at is None:
                return False
            if time.monotonic() - self.opened_at >= self.cooldown_seconds:
                # Half-open: give the next call a chance.
                logger.info("circuit breaker %s entering half-open state", self.name)
                self.opened_at = None
                self.failures = 0
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            if self.failures or self.opened_at:
                logger.info("circuit breaker %s closed after success", self.name)
            self.failures = 0
            self.opened_at = None

    def record_failure(self) -> None:
        with self._lock:
            self.failures += 1
            if self.failures >= self.threshold and self.opened_at is None:
                self.opened_at = time.monotonic()
                logger.warning(
                    "circuit breaker %s opened after %d failures (cooldown %.0fs)",
                    self.name,
                    self.failures,
                    self.cooldown_seconds,
                )

    def reset(self) -> None:
        with self._lock:
            self.failures = 0
            self.opened_at = None
