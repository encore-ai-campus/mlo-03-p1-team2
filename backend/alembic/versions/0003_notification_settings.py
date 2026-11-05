"""Account notification preferences.

Revision ID: 0003
Revises: 0002
"""
import sqlalchemy as sa
from alembic import context, op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    table_options = {}
    bind = op.get_bind()
    if bind.dialect.name in ("mysql", "mariadb") and not context.is_offline_mode():
        # 기존 users의 콜레이션은 현재 DB 기본값과 다를 수 있습니다.
        # 외래 키의 양쪽 문자열 컬럼이 동일한 문자셋·콜레이션을 사용하도록 맞춥니다.
        user_id = bind.execute(sa.text(
            "SELECT CHARACTER_SET_NAME AS column_charset, COLLATION_NAME AS column_collation "
            "FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'id'"
        )).mappings().one()
        prefix = bind.dialect.name
        table_options = {
            f"{prefix}_engine": "InnoDB",
            f"{prefix}_charset": user_id["column_charset"],
            f"{prefix}_collate": user_id["column_collation"],
        }
    op.create_table(
        "notification_settings",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("booking_reminders", sa.Boolean(), nullable=False),
        sa.Column("favorite_updates", sa.Boolean(), nullable=False),
        **table_options,
    )


def downgrade() -> None:
    op.drop_table("notification_settings")
