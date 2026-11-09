import pytest
from budget import Budget


def test_reserve_blocks_at_cap_including_inflight():
    b = Budget(10, 5)
    r1 = b.reserve(6, 2)
    assert r1 and b.remaining() == (4, 3)
    assert b.reserve(5) is None          # 6 in flight + 5 > 10
    b.settle(r1, 5, 2)                   # one record fewer than worst case
    assert b.remaining() == (5, 3)
    assert b.reserve(5, 3) is not None
    assert b.reserve(1) is None


def test_mongo_cap_is_inside_total():
    b = Budget(100, 3)
    assert b.reserve(4, 4) is None
    with pytest.raises(ValueError):
        b.reserve(1, 2)


def test_unknown_outcome_stays_reserved_until_quiet_reconcile():
    b = Budget(10, 10)
    r = b.reserve(5, 0)
    b.mark_unknown(r)
    assert b.remaining()[0] == 5
    b.reconcile_quiet(db_total=0, db_mongo=0)   # DB shows it was not stored
    assert b.remaining() == (10, 10)


def test_db_floor_counts_rows_of_unacknowledged_requests():
    b = Budget(10, 10)
    r = b.reserve(3)
    b.observe_db(4, 0)          # 4 rows exist although nothing was settled yet
    assert b.used_total() == 7  # floor 4 + 3 in flight (conservative double count)
    b.settle(r, 3)
    assert b.used_total() == 4
    with pytest.raises(RuntimeError):
        b.reserve(1) and b.reconcile_quiet(0, 0)


def test_phase_limit_is_lower_than_global_cap():
    b = Budget(100, 100)
    assert b.reserve(10, limit_total=9) is None
    assert b.reserve(9, limit_total=9) is not None


def test_restore_treats_inflight_as_unknown():
    b = Budget(10, 10)
    b.reserve(4, 1)
    c = Budget.restore(b.snapshot())
    assert c.used_total() == 4 and c.used_mongo() == 1 and not c.inflight
