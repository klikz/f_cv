import numpy as np
import pytest

from vision.video.shm import FrameRingReader, FrameRingWriter, ReaderCache


def _frame(v: int, h=36, w=64):
    return np.full((h, w, 3), v % 256, np.uint8)


def test_write_read_latest_and_by_seq():
    w = FrameRingWriter("fcv_test_rw_1", 64, 36, slots=4)
    try:
        r = FrameRingReader("fcv_test_rw_1")
        assert r.read() is None
        for i in range(1, 4):
            w.write(_frame(i), ts=100.0 + i)
        seq, ts, img = r.read()
        assert seq == 3 and ts == 103.0 and img[0, 0, 0] == 3
        assert r.read(2)[2][0, 0, 0] == 2
        r.close()
    finally:
        w.close()


def test_ring_overwrite_drops_old_frames():
    w = FrameRingWriter("fcv_test_rw_2", 64, 36, slots=4)
    try:
        r = FrameRingReader("fcv_test_rw_2")
        for i in range(1, 11):
            w.write(_frame(i))
        assert r.read(3) is None  # buferdan chiqib ketgan
        assert r.read(10)[2][0, 0, 0] == 10
        assert r.latest_seq == 10
        r.close()
    finally:
        w.close()


def test_wrong_shape_rejected():
    w = FrameRingWriter("fcv_test_rw_3", 64, 36, slots=2)
    try:
        with pytest.raises(ValueError):
            w.write(np.zeros((10, 10, 3), np.uint8))
    finally:
        w.close()


def test_reader_cache_switches_generation():
    w1 = FrameRingWriter("fcv_9_sub_1", 64, 36, slots=2)
    w2 = FrameRingWriter("fcv_9_sub_2", 32, 18, slots=2)
    cache = ReaderCache()
    try:
        assert cache.get("fcv_9_sub_1").w == 64
        r2 = cache.get("fcv_9_sub_2")
        assert r2.w == 32
        assert "fcv_9_sub_1" not in cache._readers
        assert cache.get("missing_segment") is None
    finally:
        cache.close()
        w1.close()
        w2.close()


def test_reader_does_not_unlink_on_close():
    w = FrameRingWriter("fcv_test_rw_4", 64, 36, slots=2)
    try:
        r = FrameRingReader("fcv_test_rw_4")
        r.close()
        FrameRingReader("fcv_test_rw_4").close()  # hali mavjud
    finally:
        w.close()
