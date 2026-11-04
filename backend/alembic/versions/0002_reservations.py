"""reservations, payments, status history (booking flow)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("performance_id", sa.String(50), sa.ForeignKey("performances.id"), nullable=False),
        sa.Column("performance_title", sa.String(200), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("venue", sa.String(200), nullable=False),
        sa.Column("mbti", sa.String(4), nullable=False),
        sa.Column("performance_date", sa.Date(), nullable=False),
        sa.Column("session_time", sa.String(5), nullable=False),
        sa.Column("seat_grade", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("request_key", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "request_key", name="uq_reservations_user_request_key"),
    )
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])
    op.create_index("ix_reservations_performance_id", "reservations", ["performance_id"])
    op.create_index("ix_reservations_created_at", "reservations", ["created_at"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reservation_id", sa.String(36), sa.ForeignKey("reservations.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "status_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("reservation_id", sa.String(36), sa.ForeignKey("reservations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity", sa.String(20), nullable=False),
        sa.Column("from_status", sa.String(10), nullable=True),
        sa.Column("to_status", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_status_history_reservation_id", "status_history", ["reservation_id"])

    # 인덱스를 먼저 만들어 MySQL이 외래 키용 인덱스를 따로 만들지 않게 합니다.
    op.add_column("events", sa.Column("reservation_id", sa.String(36), nullable=True))
    op.create_index("ix_events_reservation_id", "events", ["reservation_id"])
    op.create_foreign_key("fk_events_reservation_id", "events", "reservations", ["reservation_id"], ["id"],
                          ondelete="CASCADE")


def downgrade() -> None:
    # MySQL은 외래 키가 사용 중인 인덱스를 지울 수 없으므로 외래 키부터 지웁니다.
    op.drop_constraint("fk_events_reservation_id", "events", type_="foreignkey")
    op.drop_index("ix_events_reservation_id", table_name="events")
    op.drop_column("events", "reservation_id")
    op.drop_table("status_history")
    op.drop_table("payments")
    op.drop_table("reservations")
