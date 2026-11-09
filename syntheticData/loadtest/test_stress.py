"""Stress phase: load curve shape and VU -> (scenario, account) assignment."""
import run_load


def test_stress_curve():
    f = run_load.stress_profile(peak=200, up=900, hold=180, down=120)
    assert f(0) == 1
    assert all(f(t) <= f(t + 1) for t in range(899))          # never decreases while ramping up
    assert f(450) == 100 and f(900) == 200 and f(1079) == 200
    assert f(1140) == 100 and f(1200) == 0
    assert max(f(t) for t in range(1201)) == 200


def test_blend_assignment_gives_each_writer_its_own_account():
    blend = [['read', {}], ['mixed', {}]]
    n_acc = 100
    plan = [(blend[i % 2][0], (i // 2) % n_acc) for i in range(200)]
    writers = [a for s, a in plan if s == 'mixed']
    assert len(writers) == 100 and len(set(writers)) == 100   # 100 mixed VUs, all on different accounts
    # VUs start in index order, so at any target VU count the split stays ~50/50
    for k in (1, 2, 51, 150, 200):
        mixed = sum(1 for s, _ in plan[:k] if s == 'mixed')
        assert abs(mixed - k / 2) <= 0.5
