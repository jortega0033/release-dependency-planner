"""Reference oracle for the future scheduling conventions in docs/PRD.md section 6.2.

This is test-only date arithmetic used to confirm the hand-calculated F-LAUNCH
expectations. It is not application code and does not exercise the server.
"""
import unittest
from datetime import date, timedelta


def is_working(day, holidays=frozenset()):
    return day.weekday() < 5 and day not in holidays


def next_working(day, holidays=frozenset()):
    while not is_working(day, holidays):
        day += timedelta(days=1)
    return day


def schedule(start, tasks, holidays=frozenset()):
    """tasks: ordered dict id -> (days, [preds]). Returns id -> (start, exclusive_end)."""
    result = {}
    remaining = dict(tasks)
    while remaining:
        progressed = False
        for tid, (days, preds) in list(remaining.items()):
            if any(p not in result for p in preds):
                continue
            earliest = max([start] + [result[p][1] for p in preds])
            first = next_working(earliest, holidays)
            last = first
            for _ in range(days - 1):
                last = next_working(last + timedelta(days=1), holidays)
            result[tid] = (first, next_working(last + timedelta(days=1), holidays))
            del remaining[tid]
            progressed = True
        if not progressed:
            raise ValueError("cycle")
    return result


def fixture(a_days=2):
    return {"a": (a_days, []), "b": (1, []), "c": (2, ["a", "b"])}


class ReferenceSchedule(unittest.TestCase):
    start = date(2026, 11, 23)  # Monday

    def test_start_is_monday(self):
        self.assertEqual(self.start.strftime("%a"), "Mon")

    def test_base_fixture(self):  # CHK-F02 (oracle only)
        got = schedule(self.start, fixture())
        self.assertEqual(got["a"], (date(2026, 11, 23), date(2026, 11, 25)))
        self.assertEqual(got["b"], (date(2026, 11, 23), date(2026, 11, 24)))
        self.assertEqual(got["c"], (date(2026, 11, 25), date(2026, 11, 27)))

    def test_a_three_days(self):  # CHK-F03 (oracle only)
        got = schedule(self.start, fixture(3))
        self.assertEqual(got["a"], (date(2026, 11, 23), date(2026, 11, 26)))
        self.assertEqual(got["c"], (date(2026, 11, 26), date(2026, 11, 30)))

    def test_holiday_tuesday(self):  # CHK-F04 (oracle only)
        got = schedule(self.start, fixture(), holidays=frozenset({date(2026, 11, 24)}))
        self.assertEqual(got["a"][1], date(2026, 11, 26))

    def test_cycle_detected(self):
        with self.assertRaises(ValueError):
            schedule(self.start, {"a": (1, ["b"]), "b": (1, ["a"])})


if __name__ == "__main__":
    unittest.main()
