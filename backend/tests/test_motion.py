import numpy as np

from vision.motion.signal import (
    HomeCycleDetector,
    MotionMeter,
    PeakCycleDetector,
    ReferenceTracker,
    StateMachine,
    autocorr_period,
)


def frames_static(n=20, h=60, w=100):
    rng = np.random.default_rng(0)
    base = rng.integers(60, 90, (h, w), dtype=np.uint8)
    return [base.copy() for _ in range(n)]


def test_motion_static_is_zero():
    m = MotionMeter()
    vals = [m.measure(f, None)[0] for f in frames_static()]
    assert max(vals) < 0.5


def test_motion_moving_block_detected():
    m = MotionMeter()
    vals = []
    for i in range(20):
        f = np.full((60, 100), 70, np.uint8)
        f[20:40, i * 4 : i * 4 + 20] = 220
        vals.append(m.measure(f, None)[0])
    assert np.mean(vals[3:]) > 3


def test_control_zone_subtracts_global_shake():
    m = MotionMeter()
    roi = np.zeros((60, 100), np.uint8)
    roi[:, :60] = 255
    ctrl = np.zeros((60, 100), np.uint8)
    ctrl[:, 80:] = 255
    rng = np.random.default_rng(1)
    base = rng.integers(0, 255, (60, 100), dtype=np.uint8)
    res = []
    for i in range(10):
        f = np.roll(base, i % 2, axis=1)  # butun kadr titraydi
        pct, cpct = m.measure(f, roi, ctrl)
        res.append(max(0.0, pct - cpct))
    assert np.mean(res[2:]) < 15  # titrash nazorat zonasi orqali ayiriladi


def test_state_machine_debounce():
    sm = StateMachine(threshold=2, min_on=3, min_off=10)
    t = 0.0
    changes = []
    seq = [5] * 30 + [0] * 50 + [5] * 5 + [0] * 150 + [5] * 50  # 0.1 s qadam
    for v in seq:
        c = sm.update(v, t)
        if c:
            changes.append((c, round(sm.since, 1)))
        t += 0.1
    states = [c for c, _ in changes]
    assert states[0] == "running"
    # qisqa to'xtash (5 s < min_off 10 s) va qisqa harakat (0.5 s < min_on 3 s) e'tiborsiz
    assert states == ["running", "stopped", "running"]


def test_state_unknown():
    sm = StateMachine()
    sm.update(5, 0)
    sm.update(5, 2)
    assert sm.set_unknown(3) and sm.state == "unknown"


def test_home_cycles_k1_and_k2():
    for k, expected in ((1, 6), (2, 3)):
        det = HomeCycleDetector(exit_thr=12, return_thr=6, k=k)
        cycles = []
        t = 0.0
        for _ in range(6):
            for v in [0] * 10 + [20] * 10 + [0] * 10:
                c = det.update(v, t)
                if c:
                    cycles.append(c)
                t += 0.1
        assert len(cycles) == expected
        if k == 1:
            durs = [round(e - s, 1) for s, e in cycles]
            assert all(abs(d - 1.0) < 0.15 for d in durs)


def test_home_hysteresis_ignores_noise():
    det = HomeCycleDetector(exit_thr=12, return_thr=6, k=1)
    t, n = 0.0, 0
    for v in [8, 10, 7, 11, 9] * 20:  # chegaralar orasida titraydi
        n += bool(det.update(v, t))
        t += 0.1
    assert n == 0


def test_peak_cycles_regular_and_with_stop():
    det = PeakCycleDetector(min_height=5, min_distance=0.5, k=1)
    sig = []
    for _ in range(10):
        sig += [0, 2, 6, 10, 6, 2, 0, 0, 0, 0]  # 1 s davr
    sig += [0] * 50  # to'xtash
    for _ in range(5):
        sig += [0, 2, 6, 10, 6, 2, 0, 0, 0, 0]
    cycles = []
    for i, v in enumerate(sig):
        c = det.update(v, i * 0.1)
        if c:
            cycles.append(round(c[1] - c[0], 1))
    assert cycles.count(1.0) >= 12
    assert any(d > 5 for d in cycles)  # to'xtash — uzun sikl (mikro-to'xtash sifatida aniqlanadi)


def test_autocorr_period():
    fps = 10
    t = np.arange(0, 60, 1 / fps)
    sig = (np.sin(2 * np.pi * t / 3.0) > 0.6).astype(float) * 10
    p = autocorr_period(sig, fps)
    assert p is not None and abs(p - 3.0) < 0.2


def test_reference_median():
    r = ReferenceTracker(n=5)
    for d in [3.0, 3.1, 2.9, 10.0, 3.0, 50]:
        r.add(d)
    assert abs(r.value - 3.0) < 0.11
    r2 = ReferenceTracker(manual=4.0, auto=False)
    r2.add(3)
    assert r2.value == 4.0


def test_state_machine_press_with_periodic_dwell():
    """Press: 1.6 s harakat + 1.4 s tayanchda tinch (sikl 3 s), 39 s ishlaydi, 21 s turadi — ikki marta takrorlanadi."""
    sm = StateMachine(threshold=2, min_on=3, min_off=6)
    t, hist = 0.0, []
    for _ in range(2):
        for _ in range(13):
            for v in [15] * 16 + [0] * 14:
                c = sm.update(v, t)
                if c:
                    hist.append((c, round(sm.since)))
                t += 0.1
        for _ in range(210):
            c = sm.update(0, t)
            if c:
                hist.append((c, round(sm.since)))
            t += 0.1
    assert [h[0] for h in hist] == ["running", "stopped", "running", "stopped"]
    assert hist[1][1] in (38, 39) and hist[2][1] == 60
