"""Account notification preferences.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("booking_reminders", sa.Boolean(), nullable=False),
        sa.Column("favorite_updates", sa.Boolean(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_settings")
