"""Case ID generator producing `KHJ-YYYY-XXXXX` per FRS FR-1.3.

On PostgreSQL an atomic sequence (`case_seq`) provides collision-free counters
across concurrent writers. On SQLite (used only for tests) we fall back to a
``MAX(case_id)``-based query, which is sufficient for single-writer tests.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def generate_case_id(session: Session, year: int) -> str:
    """Return next `KHJ-YYYY-XXXXX` identifier.

    The counter is global (not per-year) when backed by a Postgres sequence —
    this matches FRS FR-1.3 which only requires uniqueness and the stated
    format, not per-year numbering.
    """
    bind = session.get_bind()
    dialect = bind.dialect.name if bind is not None else "sqlite"

    if dialect == "postgresql":
        counter = session.execute(text("SELECT nextval('case_seq')")).scalar_one()
    else:
        # SQLite fallback: pick the highest existing counter for this year + 1.
        row = session.execute(
            text(
                "SELECT case_id FROM cases "
                "WHERE case_id LIKE :prefix "
                "ORDER BY case_id DESC LIMIT 1"
            ),
            {"prefix": f"KHJ-{year}-%"},
        ).scalar()
        counter = (int(row.rsplit("-", 1)[-1]) + 1) if row else 1

    return f"KHJ-{year}-{int(counter):05d}"
