"""FastAPI routers — thin HTTP wrappers over :mod:`app.services`."""
from app.routers import admin, auth, cases, health, matches

__all__ = ["admin", "auth", "cases", "health", "matches"]
