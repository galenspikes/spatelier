"""Add file tracking columns to media_files

Revision ID: e6162c0475c1
Revises: 4b58c98a7204
Create Date: 2025-11-03 00:10:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6162c0475c1"
down_revision: Union[str, Sequence[str], None] = "4b58c98a7204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add OS-level file tracking columns to media_files table."""
    # Add file_device column
    op.add_column("media_files", sa.Column("file_device", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_media_files_file_device"), "media_files", ["file_device"], unique=False
    )

    # Add file_inode column
    op.add_column("media_files", sa.Column("file_inode", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_media_files_file_inode"), "media_files", ["file_inode"], unique=False
    )

    # Add file_identifier column (device:inode string)
    op.add_column(
        "media_files", sa.Column("file_identifier", sa.String(length=50), nullable=True)
    )
    op.create_index(
        op.f("ix_media_files_file_identifier"),
        "media_files",
        ["file_identifier"],
        unique=True,
    )


def downgrade() -> None:
    """Remove OS-level file tracking columns from media_files table."""
    # Drop indexes first
    op.drop_index(op.f("ix_media_files_file_identifier"), table_name="media_files")
    op.drop_index(op.f("ix_media_files_file_inode"), table_name="media_files")
    op.drop_index(op.f("ix_media_files_file_device"), table_name="media_files")

    # Drop columns
    op.drop_column("media_files", "file_identifier")
    op.drop_column("media_files", "file_inode")
    op.drop_column("media_files", "file_device")
