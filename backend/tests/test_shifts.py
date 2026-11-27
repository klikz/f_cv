from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.services.shifts import ShiftDef, active_set, match_shift

TZ = ZoneInfo("Asia/Tashkent")
EPOCH = datetime(2000, 1, 1, tzinfo=UTC)

DEFAULT = [
    ShiftDef(1, "Kunduzgi smena", time(8, 0), time(19, 0), EPOCH),
    ShiftDef(2, "Tungi smena", time(19, 0), time(8, 0), EPOCH),
]


def local(y, m, d, hh, mm, ss=0):
    return datetime(y, m, d, hh, mm, ss, tzinfo=TZ)


@pytest.mark.parametrize(
    ("ts", "shift_id", "shift_date"),
    [
        (local(2026, 11, 26, 7, 59), 2, date(2026, 11, 25)),  # tungi, kechagi sana
        (local(2026, 11, 26, 7, 59, 59), 2, date(2026, 11, 25)),
        (local(2026, 11, 26, 8, 0), 1, date(2026, 11, 26)),  # kunduzgi boshlanishi
        (local(2026, 11, 26, 18, 59), 1, date(2026, 11, 26)),
        (local(2026, 11, 26, 18, 59, 59), 1, date(2026, 11, 26)),
        (local(2026, 11, 26, 19, 0), 2, date(2026, 11, 26)),  # tungi boshlanishi
        (local(2026, 11, 26, 23, 59), 2, date(2026, 11, 26)),
        (local(2026, 11, 27, 0, 0), 2, date(2026, 11, 26)),  # yarim tun
        (local(2026, 11, 27, 0, 30), 2, date(2026, 11, 26)),  # boshlangan sanaga tegishli
        (local(2027, 1, 1, 0, 30), 2, date(2026, 12, 31)),  # yil almashishi
        (local(2028, 3, 1, 3, 0), 2, date(2028, 2, 29)),  # kabisa yili
    ],
)
def test_default_boundaries(ts, shift_id, shift_date):
    m = match_shift(DEFAULT, ts, TZ)
    assert m is not None
    assert (m.shift_id, m.shift_date) == (shift_id, shift_date)


def test_utc_input_converted_to_local():
    # 2026-11-26 03:00 UTC == 08:00 Toshkent
    m = match_shift(DEFAULT, datetime(2026, 11, 26, 3, 0, tzinfo=UTC), TZ)
    assert m is not None and m.shift_id == 1 and m.shift_date == date(2026, 11, 26)
    # 02:59:59 UTC == 07:59:59 Toshkent → tungi, kechagi sana
    m = match_shift(DEFAULT, datetime(2026, 11, 26, 2, 59, 59, tzinfo=UTC), TZ)
    assert m is not None and m.shift_id == 2 and m.shift_date == date(2026, 11, 25)


def test_naive_datetime_rejected():
    with pytest.raises(ValueError):
        match_shift(DEFAULT, datetime(2026, 11, 26, 9, 0), TZ)


def test_gap_is_out_of_shift():
    shifts = [
        ShiftDef(1, "1-smena", time(8, 0), time(17, 0), EPOCH),
        ShiftDef(2, "2-smena", time(20, 0), time(5, 0), EPOCH),
    ]
    assert match_shift(shifts, local(2026, 11, 26, 18, 0), TZ) is None
    assert match_shift(shifts, local(2026, 11, 26, 6, 0), TZ) is None
    assert match_shift(shifts, local(2026, 11, 26, 17, 0), TZ) is None  # tugash vaqti kirmaydi
    m = match_shift(shifts, local(2026, 11, 26, 4, 59), TZ)
    assert m is not None and m.shift_id == 2 and m.shift_date == date(2026, 11, 25)


def test_no_shifts_defined():
    assert match_shift([], local(2026, 11, 26, 9, 0), TZ) is None


def test_versioning_only_affects_future():
    change = local(2026, 12, 1, 0, 0)
    shifts = [
        *DEFAULT,
        ShiftDef(3, "Kunduzgi (yangi)", time(7, 0), time(19, 0), change),
        ShiftDef(4, "Tungi (yangi)", time(19, 0), time(7, 0), change),
    ]
    # o'zgarishdan oldin — eski to'plam
    before = match_shift(shifts, local(2026, 11, 30, 7, 30), TZ)
    assert before is not None and before.shift_id == 2
    # o'zgarishdan keyin — yangi to'plam
    after = match_shift(shifts, local(2026, 12, 2, 7, 30), TZ)
    assert after is not None and after.shift_id == 3
    assert {s.id for s in active_set(shifts, local(2026, 12, 2, 7, 30))} == {3, 4}


def test_24h_shift():
    shifts = [ShiftDef(1, "Kun bo'yi", time(8, 0), time(8, 0), EPOCH)]
    a = match_shift(shifts, local(2026, 11, 26, 8, 0), TZ)
    b = match_shift(shifts, local(2026, 11, 27, 7, 59), TZ)
    assert a is not None and a.shift_date == date(2026, 11, 26)
    assert b is not None and b.shift_date == date(2026, 11, 26)
