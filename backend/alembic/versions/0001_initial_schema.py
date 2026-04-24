"""initial schema — users, cases, photos, matches, not_match_feedback, audit_log, app_settings

Revision ID: 0001
Revises:
Create Date: 2026-04-24

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def _json_col() -> sa.types.TypeEngine:
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _uuid_col() -> sa.types.TypeEngine:
    return sa.Uuid()


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("CREATE SEQUENCE IF NOT EXISTS case_seq START 1")

    op.create_table(
        "users",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False, unique=True, index=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("family", "field_worker", "admin", name="user_role", native_enum=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "cases",
        sa.Column("case_id", sa.String(16), primary_key=True),
        sa.Column("person_name", sa.String(255), nullable=False),
        sa.Column("year_missing", sa.Integer(), nullable=False),
        sa.Column("age_at_disappearance", sa.Integer(), nullable=False),
        sa.Column("last_seen_location", sa.String(255), nullable=False),
        sa.Column("identifying_marks", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("active", "under_review", "found", "closed", name="case_status", native_enum=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_by", _uuid_col(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "photos",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("case_id", sa.String(16), sa.ForeignKey("cases.case_id"), nullable=False, index=True),
        sa.Column("supabase_url", sa.String(1024), nullable=False),
        sa.Column("age_at_photo", sa.Integer(), nullable=False),
        sa.Column("embedding", _json_col(), nullable=True),
        sa.Column("is_predicted_aged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "matches",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("case_id", sa.String(16), sa.ForeignKey("cases.case_id"), nullable=False, index=True),
        sa.Column("candidate_photo_id", _uuid_col(), sa.ForeignKey("photos.id"), nullable=False, index=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column(
            "tier",
            sa.Enum("high", "medium", "low", name="match_tier", native_enum=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pending", "confirmed", "not_match", name="match_status", native_enum=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("field_worker_id", _uuid_col(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "not_match_feedback",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("match_id", _uuid_col(), sa.ForeignKey("matches.id"), nullable=False, unique=True, index=True),
        sa.Column("real_photo_url", sa.String(1024), nullable=False),
        sa.Column("error_vector", _json_col(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_log",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("actor_id", _uuid_col(), nullable=True, index=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(64), nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("hmac_signature", sa.String(64), nullable=False),
    )

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", _json_col(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_by", _uuid_col(), sa.ForeignKey("users.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("audit_log")
    op.drop_table("not_match_feedback")
    op.drop_table("matches")
    op.drop_table("photos")
    op.drop_table("cases")
    op.drop_table("users")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP SEQUENCE IF EXISTS case_seq")
