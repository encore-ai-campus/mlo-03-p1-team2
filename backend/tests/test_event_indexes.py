"""The ranking and the popular sort must be answered from the events(type, performance_id) index."""
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings
from app.db.base import Base

API = "/api/v1"
BACKEND = Path(__file__).resolve().parents[1]
COMPOSITE = "ix_events_type_performance_id"


def _event_indexes(engine):
    return {ix["name"]: ix["column_names"] for ix in inspect(engine).get_indexes("events")}


@pytest.fixture()
def migrated(tmp_path, monkeypatch):
    """A file SQLite database at the 0004 schema, upgraded to head by the real migration.

    0001–0004 use MySQL-only DDL (ALTER ... ADD CONSTRAINT), so the 0004 events indexes are
    rebuilt by hand and the database is stamped 0004; only the migrations after that run.
    """
    url = f"sqlite:///{(tmp_path / 'migrated.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(f"drop index {COMPOSITE}"))
        conn.execute(text("create index ix_events_type on events (type)"))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.stamp(cfg, "0004")
    command.upgrade(cfg, "head")
    yield cfg, engine
    engine.dispose()
    get_settings.cache_clear()


def test_migration_creates_composite_index_and_drops_redundant_one(migrated):
    _, engine = migrated
    indexes = _event_indexes(engine)
    assert indexes[COMPOSITE] == ["type", "performance_id"]
    assert "ix_events_type" not in indexes
    assert indexes["ix_events_performance_id"] == ["performance_id"]   # still needed for the foreign key


def test_migration_downgrade_restores_previous_indexes(migrated):
    cfg, engine = migrated
    command.downgrade(cfg, "0004")
    indexes = _event_indexes(engine)
    assert COMPOSITE not in indexes
    assert indexes["ix_events_type"] == ["type"]
    command.upgrade(cfg, "head")
    assert COMPOSITE in _event_indexes(engine)


def test_models_match_migrated_events_indexes(migrated):
    _, engine = migrated
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    index_diff = [d for d in diff if d[0] in ("add_index", "remove_index") and d[1].table.name == "events"]
    assert index_diff == []


def _count_plan(session_factory, types):
    params = {f"t{i}": t for i, t in enumerate(types)}
    names = ", ".join(f":{k}" for k in params)
    sql = f"select performance_id, count(*) from events where type in ({names}) group by performance_id"
    with session_factory() as s:
        return " ".join(row[-1] for row in s.execute(text("explain query plan " + sql), params))


@pytest.mark.parametrize("types", [("performance_view",), ("mock_purchase", "payment_completed")])
def test_ranking_counts_use_covering_index(db_session, types):
    plan = _count_plan(db_session, types)
    assert f"COVERING INDEX {COMPOSITE}" in plan, plan


def test_ranking_counts_views_and_purchases_per_performance(client, auth):
    for pid, n in (("color", 3), ("opera", 1), ("jazz", 2)):
        for _ in range(n):
            assert client.post(f"{API}/events", json={"performance_id": pid}, headers=auth).status_code == 201
    client.post(f"{API}/events", json={"performance_id": "opera", "type": "booking_started"}, headers=auth)

    ranking = client.get(f"{API}/performances/ranking", params={"limit": 3}).json()
    assert [(r["id"], r["purchases"], r["views"]) for r in ranking] == [
        ("color", 0, 3), ("jazz", 0, 2), ("opera", 0, 1)]
