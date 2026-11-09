"""Monitor safety: bad Prometheus samples must not crash it, and a dead monitor must stop the load."""
import time
import run_load


class FakeRun:
    def __init__(self):
        self.prom_baseline = None
        self.reasons = []

    def abort(self, reason, fatal=True):
        self.reasons.append(reason)


def monitor(run):
    m = run_load.Monitor.__new__(run_load.Monitor)
    m.run = run
    return m


def test_error_sample_is_ignored_not_crashing():
    run = FakeRun()
    sample = {k: {'error': 'ConnectTimeout'} for k in ('up', 'boot_time', 'disk_avail_bytes')}
    assert monitor(run).check_prom(sample) is False
    assert run.reasons == []


def test_partial_error_and_low_disk():
    run = FakeRun()
    sample = {'up': {'fastapi-175': 1.0, 'fastapi-176': 0.0}, 'boot_time': {'fastapi-175': 100.0},
              'disk_avail_bytes': {'nginx-177': 5e8, 'x': 'error'}, 'mysql_threads_connected': {'error': 'X'}}
    assert monitor(run).check_prom(sample) is True
    assert any('fastapi-176' in r for r in run.reasons) and any('disk' in r for r in run.reasons)


def test_reboot_detected():
    run = FakeRun()
    m = monitor(run)
    m.check_prom({'up': {'fastapi-175': 1.0}, 'boot_time': {'fastapi-175': 100.0}})
    m.check_prom({'up': {'fastapi-175': 1.0}, 'boot_time': {'fastapi-175': 500.0}})
    assert any('rebooted' in r for r in run.reasons)


def test_watchdog_stops_load_when_monitor_is_stale(tmp_path):
    r = run_load.Run.__new__(run_load.Run)
    r.stop_reason, r.stage_stop, r.dir, r.monitor_tick = None, None, tmp_path, time.time() - 30
    r.log_event = lambda *a, **k: None
    r.stop_fatal = False
    assert r.stopping() is True and 'watchdog' in r.stop_reason
