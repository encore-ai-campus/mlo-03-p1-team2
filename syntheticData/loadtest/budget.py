"""Single shared write budget for one load-test run (one process, one asyncio loop).

Every write request reserves its worst-case record count *before* it is sent.
- success with a known outcome -> settle(actual)       (unused part is released)
- definite rejection (4xx)      -> settle(0)
- unknown outcome (timeout/5xx) -> mark_unknown()      (kept reserved until DB reconcile)

The budget is persisted so a resumed run continues from the same totals.
"""
from dataclasses import dataclass, field, fields
import itertools


@dataclass
class Reservation:
    id: int
    total: int
    mongo: int


@dataclass
class Budget:
    total_cap: int
    mongo_cap: int
    committed_total: int = 0
    committed_mongo: int = 0
    unknown_total: int = 0
    unknown_mongo: int = 0
    db_floor_total: int = 0   # last DB-observed count (includes rows of requests still in flight)
    db_floor_mongo: int = 0
    inflight: dict = field(default_factory=dict)
    _ids: itertools.count = field(default_factory=lambda: itertools.count(1), repr=False)

    # ---- totals ---------------------------------------------------------------------------
    def inflight_total(self) -> int:
        return sum(r.total for r in self.inflight.values())

    def inflight_mongo(self) -> int:
        return sum(r.mongo for r in self.inflight.values())

    def used_total(self) -> int:
        local = self.committed_total + self.unknown_total + self.inflight_total()
        return max(local, self.db_floor_total + self.inflight_total())

    def used_mongo(self) -> int:
        local = self.committed_mongo + self.unknown_mongo + self.inflight_mongo()
        return max(local, self.db_floor_mongo + self.inflight_mongo())

    def remaining(self) -> tuple[int, int]:
        return self.total_cap - self.used_total(), self.mongo_cap - self.used_mongo()

    # ---- request lifecycle ----------------------------------------------------------------
    def reserve(self, total: int, mongo: int = 0, limit_total: int | None = None,
                limit_mongo: int | None = None) -> Reservation | None:
        """Reserve worst-case records. `limit_*` is an optional lower per-phase ceiling."""
        if mongo > total:
            raise ValueError('mongo records are part of the total')
        cap_t = min(self.total_cap, limit_total if limit_total is not None else self.total_cap)
        cap_m = min(self.mongo_cap, limit_mongo if limit_mongo is not None else self.mongo_cap)
        if self.used_total() + total > cap_t or self.used_mongo() + mongo > cap_m:
            return None
        r = Reservation(next(self._ids), total, mongo)
        self.inflight[r.id] = r
        return r

    def settle(self, r: Reservation, total: int, mongo: int = 0) -> None:
        """Known outcome: `total`/`mongo` records were actually stored (<= reserved)."""
        self.inflight.pop(r.id)
        # If more rows than reserved were stored the real number is kept (cost model was wrong).
        self.committed_total += total
        self.committed_mongo += mongo

    def mark_unknown(self, r: Reservation) -> None:
        self.inflight.pop(r.id)
        self.unknown_total += r.total
        self.unknown_mongo += r.mongo

    # ---- reconciliation with the databases -----------------------------------------------
    def observe_db(self, db_total: int, db_mongo: int) -> None:
        """While requests may be in flight: DB counts only raise the floor."""
        self.db_floor_total = max(self.db_floor_total, db_total)
        self.db_floor_mongo = max(self.db_floor_mongo, db_mongo)

    def reconcile_quiet(self, db_total: int, db_mongo: int) -> dict:
        """With nothing in flight the DB is the truth: unknown outcomes are resolved."""
        if self.inflight:
            raise RuntimeError('reconcile_quiet requires no requests in flight')
        before = self.snapshot()
        self.committed_total, self.committed_mongo = db_total, db_mongo
        self.unknown_total = self.unknown_mongo = 0
        self.db_floor_total, self.db_floor_mongo = db_total, db_mongo
        return {'before': before, 'after': self.snapshot()}

    # ---- persistence ----------------------------------------------------------------------
    def snapshot(self) -> dict:
        d = {f.name: getattr(self, f.name) for f in fields(self) if f.name not in ('inflight', '_ids')}
        d['inflight_total'], d['inflight_mongo'] = self.inflight_total(), self.inflight_mongo()
        d['used_total'], d['used_mongo'] = self.used_total(), self.used_mongo()
        return d

    @classmethod
    def restore(cls, d: dict) -> 'Budget':
        """Resume: anything in flight at save time is treated as unknown (kept reserved)."""
        return cls(d['total_cap'], d['mongo_cap'], d['committed_total'], d['committed_mongo'],
                d['unknown_total'] + d.get('inflight_total', 0), d['unknown_mongo'] + d.get('inflight_mongo', 0),
                d['db_floor_total'], d['db_floor_mongo'])
