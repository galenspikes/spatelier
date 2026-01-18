"""Add SQLite transcription storage (JSON + FTS5)

Revision ID: 9b3c2f1d8a7b
Revises: e6162c0475c1
Create Date: 2026-01-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b3c2f1d8a7b"
down_revision: Union[str, Sequence[str], None] = "e6162c0475c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add transcription storage tables for SQLite."""
    op.create_table(
        "transcriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "media_file_id",
            sa.Integer(),
            sa.ForeignKey("media_files.id"),
            nullable=False,
        ),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("processing_time", sa.Float(), nullable=True),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("segments_json", sa.JSON(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        op.f("ix_transcriptions_id"), "transcriptions", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_transcriptions_media_file_id"),
        "transcriptions",
        ["media_file_id"],
        unique=False,
    )

    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute(
            "CREATE VIRTUAL TABLE transcriptions_fts USING fts5("
            "full_text, content='transcriptions', content_rowid='id'"
            ")"
        )
        op.execute(
            "CREATE TRIGGER transcriptions_ai AFTER INSERT ON transcriptions BEGIN "
            "INSERT INTO transcriptions_fts(rowid, full_text) VALUES (new.id, new.full_text); "
            "END;"
        )
        op.execute(
            "CREATE TRIGGER transcriptions_ad AFTER DELETE ON transcriptions BEGIN "
            "INSERT INTO transcriptions_fts(transcriptions_fts, rowid, full_text) "
            "VALUES('delete', old.id, old.full_text); "
            "END;"
        )
        op.execute(
            "CREATE TRIGGER transcriptions_au AFTER UPDATE ON transcriptions BEGIN "
            "INSERT INTO transcriptions_fts(transcriptions_fts, rowid, full_text) "
            "VALUES('delete', old.id, old.full_text); "
            "INSERT INTO transcriptions_fts(rowid, full_text) VALUES (new.id, new.full_text); "
            "END;"
        )


def downgrade() -> None:
    """Remove transcription storage tables."""
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS transcriptions_au")
        op.execute("DROP TRIGGER IF EXISTS transcriptions_ad")
        op.execute("DROP TRIGGER IF EXISTS transcriptions_ai")
        op.execute("DROP TABLE IF EXISTS transcriptions_fts")

    op.drop_index(op.f("ix_transcriptions_media_file_id"), table_name="transcriptions")
    op.drop_index(op.f("ix_transcriptions_id"), table_name="transcriptions")
    op.drop_table("transcriptions")
