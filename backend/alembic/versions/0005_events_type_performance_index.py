"""Composite index on events(type, performance_id) for popularity ranking.

The ranking and the popular sort count events per performance for some event types.
With only single-column indexes MariaDB scanned the whole events table for
performance_view (70 % of the rows). The composite index covers the query, and
it replaces ix_events_type because type is its leading column.

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_events_type_performance_id", "events", ["type", "performance_id"])
    op.drop_index("ix_events_type", table_name="events")


def downgrade() -> None:
    op.create_index("ix_events_type", "events", ["type"])
    op.drop_index("ix_events_type_performance_id", table_name="events")
