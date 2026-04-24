"""Tamper-evident audit log writer.

Every AI decision is appended with an SHA-256 checksum chained to the
previous record, per FRS §10.3.
"""
from __future__ import annotations

import hashlib


def chain_checksum(row_data: str, prev_checksum: str) -> str:
    payload = f"{row_data}||{prev_checksum}".encode()
    return hashlib.sha256(payload).hexdigest()


async def append(action: str, case_id: str, payload: dict, prev_checksum: str = "") -> str:
    raise NotImplementedError("Wire up Supabase insert in implementation phase")
