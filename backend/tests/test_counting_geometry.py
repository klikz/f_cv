import numpy as np

from vision.logic.geometry import CrossingState, LineCounter, point_in_polygon, segments_intersect, side
from vision.logic.tracker import ByteTracker

# vertikal chiziq x=500 (A tepada, B pastda) — normal n = (-1, 0)? A=(500,100), B=(500,900): dx=0, dy=800 → n=(-1,0)
# ya'ni "oldinga" — chapga. Chapdan o'ngga harakat uchun A va B ni almashtiramiz.
LINE_LR = ((500.0, 900.0), (500.0, 100.0))  # n = (1, 0): chapdan o'ngga


def run(points, lc=None, start_age=1):
    lc = lc or LineCounter(*LINE_LR, max_angle=60, min_track_frames=3, min_distance=20)
    st = CrossingState()
    out = []
    for i, p in enumerate(points):
        r = lc.update(st, p, age=start_age + i)
        if r is not None:
            out.append(r)
    return out


def test_side_and_intersect():
    a, b = LINE_LR
    assert side(a, b, (600, 500)) > 0 and side(a, b, (400, 500)) < 0
    assert segments_intersect((400, 500), (600, 500), a, b)
    assert not segments_intersect((400, 50), (600, 50), a, b)  # kesmadan tashqarida (chiziq uchidan o'tdi)


def test_straight_crossing_counts_once():
    pts = [(x, 500) for x in range(300, 800, 40)]
    assert run(pts) == [1]


def test_reverse_crossing_direction():
    pts = [(x, 500) for x in range(800, 300, -40)]
    assert run(pts) == [-1]


def test_walking_along_line_not_counted():
    pts = [(x, y) for x, y in zip([495, 505, 495, 505, 495, 505, 495, 505], range(200, 600, 50), strict=False)]
    assert run(pts) == []


def test_jitter_on_line_not_counted():
    pts = [(440, 500), (470, 500), (490, 500), (510, 500), (490, 500), (510, 500), (495, 500), (505, 500)]
    assert run(pts) == []


def test_go_back_before_confirm_not_counted():
    pts = [(400, 500), (450, 500), (490, 500), (510, 500), (490, 500), (450, 500), (400, 500)]
    assert run(pts) == []


def test_born_near_line_not_counted():
    # track chiziq yonida (10 px) tug'ilgan — boshlang'ich tomonda yetarli uzoqlik yo'q
    pts = [(495, 500), (530, 500), (580, 500), (640, 500)]
    assert run(pts) == []


def test_steep_angle_rejected():
    # deyarli chiziq bo'ylab (pastga) harakat, oxirida kesib o'tadi — burchak > 60°
    pts = [(480, 100), (485, 200), (490, 300), (495, 400), (502, 500), (510, 600), (530, 700)]
    lc = LineCounter(*LINE_LR, max_angle=60, min_track_frames=3, min_distance=20)
    assert run(pts, lc) == []


def test_young_track_rejected():
    pts = [(470, 500), (530, 500)]
    lc = LineCounter(*LINE_LR, max_angle=60, min_track_frames=5, min_distance=20)
    assert run(pts, lc) == []


def test_back_and_forth_reports_alternating_directions():
    fwd = [(x, 500) for x in range(300, 800, 40)]
    back = [(x, 500) for x in range(780, 300, -40)]
    # har kesib o'tish (yo'nalish almashganda) qaytariladi; siyosat (e'tiborsiz/ayirish/alohida) CountingTask da
    assert run(fwd + back + fwd) == [1, -1, 1]


def test_point_in_polygon():
    poly = [(0, 0), (100, 0), (100, 100), (0, 100)]
    assert point_in_polygon((50, 50), poly)
    assert not point_in_polygon((150, 50), poly)


def test_tracker_keeps_id_and_handles_two_objects():
    tr = ByteTracker()
    ids = set()
    for k in range(10):
        dets = np.array([[100 + 30 * k, 100, 300 + 30 * k, 300, 0.9], [900 - 30 * k, 400, 1100 - 30 * k, 600, 0.8]])
        active, _ = tr.update(dets)
        ids |= {t.id for t in active}
    assert ids == {1, 2}
    # bir kadr aniqlanmasa ham track yo'qolmaydi
    tr.update(np.zeros((0, 5)))
    active, _ = tr.update(np.array([[100 + 330, 100, 300 + 330, 300, 0.9]]))
    assert [t.id for t in active] == [1]


def test_touching_objects_get_separate_tracks():
    tr = ByteTracker()
    for k in range(8):
        x = 100 + 40 * k
        dets = np.array([[x, 100, x + 200, 300, 0.85], [x + 202, 100, x + 402, 300, 0.85]])
        active, _ = tr.update(dets)
    assert sorted(t.id for t in active) == [1, 2]
