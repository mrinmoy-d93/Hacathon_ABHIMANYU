"""Supabase client wrapper: Storage uploads + public URL resolution.

The service-role key is required for server-side writes; it is **only** loaded
from ``SUPABASE_SERVICE_KEY`` env and never hard-coded.
"""
from __future__ import annotations

import logging
import mimetypes
import uuid
from functools import lru_cache
from typing import Any
from urllib.parse import urlparse

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> Any:
    """Return a Supabase ``Client``. Import is deferred so tests that mock this
    function don't need the ``supabase`` package installed."""
    from supabase import create_client  # local import — see docstring

    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured")
    return create_client(settings.supabase_url, settings.supabase_service_key)


def _guess_mime(filename: str | None) -> str:
    if not filename:
        return "application/octet-stream"
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def upload_photo(
    file_bytes: bytes,
    bucket: str,
    case_id: str,
    filename: str | None = None,
    content_type: str | None = None,
) -> str:
    """Upload bytes to ``bucket`` under a case-scoped path, return the public URL.

    Path: ``{case_id}/{uuid4}{ext}`` — the UUID prevents collisions when the
    same case uploads multiple photos.
    """
    client = get_client()
    ext = ""
    if filename and "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()
    path = f"{case_id}/{uuid.uuid4()}{ext}"
    storage = client.storage.from_(bucket)

    storage.upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type or _guess_mime(filename)},
    )

    public = storage.get_public_url(path)
    logger.info("uploaded photo to bucket=%s path=%s", bucket, path)
    return public


def delete_photo(url: str) -> None:
    """Delete a previously uploaded object given its public URL.

    Public URL shape: ``{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}``.
    """
    parsed = urlparse(url)
    parts = parsed.path.split("/storage/v1/object/public/", 1)
    if len(parts) != 2 or not parts[1]:
        raise ValueError(f"Unrecognised Supabase public URL: {url}")
    bucket, _, path = parts[1].partition("/")
    if not bucket or not path:
        raise ValueError(f"Cannot parse bucket/path from URL: {url}")

    client = get_client()
    client.storage.from_(bucket).remove([path])
    logger.info("deleted photo from bucket=%s path=%s", bucket, path)
