"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("mbti", sa.String(4), nullable=False),
        sa.Column("consent", sa.Boolean(), nullable=False),
        sa.Column("consented_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "performances",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("english", sa.String(200), nullable=False),
        sa.Column("sub", sa.String(200), nullable=False),
        sa.Column("image", sa.String(200), nullable=False),
        sa.Column("style", sa.String(50), nullable=False),
        sa.Column("venue", sa.String(200), nullable=False),
        sa.Column("date_label", sa.String(100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("badge", sa.String(100), nullable=False),
        sa.Column("tag", sa.String(100), nullable=False),
        sa.Column("slots", sa.JSON(), nullable=False),
    )
    op.create_index("ix_performances_category", "performances", ["category"])

    op.create_table(
        "orders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("performance_id", sa.String(50), sa.ForeignKey("performances.id"), nullable=False),
        sa.Column("mbti", sa.String(4), nullable=False),
        sa.Column("performance_title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("venue", sa.String(200), nullable=False),
        sa.Column("performance_date", sa.Date(), nullable=False),
        sa.Column("session_time", sa.String(5), nullable=False),
        sa.Column("seat_grade", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("payment_method", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_mock", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_performance_id", "orders", ["performance_id"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])

    op.create_table(
        "events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("mbti", sa.String(4), nullable=True),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("performance_id", sa.String(50), sa.ForeignKey("performances.id"), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_user_id", "events", ["user_id"])
    op.create_index("ix_events_type", "events", ["type"])
    op.create_index("ix_events_performance_id", "events", ["performance_id"])

    op.create_table(
        "favorites",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("performance_id", sa.String(50), sa.ForeignKey("performances.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("favorites")
    op.drop_table("events")
    op.drop_table("orders")
    op.drop_table("performances")
    op.drop_table("users")
