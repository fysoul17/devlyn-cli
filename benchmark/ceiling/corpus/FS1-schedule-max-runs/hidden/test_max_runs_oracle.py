"""Hidden oracle for FS1 (iter-0064). Behavior-only: exercises exactly the
API pinned in task.txt, never internal attribute names. Self-contained
mock_datetime copy so arm edits to test_schedule.py cannot break the oracle."""

import datetime

import pytest

import schedule
from schedule import ScheduleValueError  # noqa: F401  (import guard: module intact)


class mock_datetime:
    """Monkey-patch datetime for predictable results (upstream pattern)."""

    def __init__(self, year, month, day, hour, minute, second=0):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.original_datetime = None

    def __enter__(self):
        class MockDate(datetime.datetime):
            @classmethod
            def today(cls):
                return cls(self.year, self.month, self.day)

            @classmethod
            def now(cls, tz=None):
                return cls(
                    self.year,
                    self.month,
                    self.day,
                    self.hour,
                    self.minute,
                    self.second,
                )

        self.original_datetime = datetime.datetime
        datetime.datetime = MockDate
        return MockDate(
            self.year, self.month, self.day, self.hour, self.minute, self.second
        )

    def __exit__(self, *args, **kwargs):
        datetime.datetime = self.original_datetime


@pytest.fixture(autouse=True)
def clean_default_scheduler():
    schedule.clear()
    yield
    schedule.clear()


def test_budget_exhausts_and_unschedules():
    runs = []
    job = schedule.every().second.max_runs(3).do(lambda: runs.append(1))
    for _ in range(5):
        schedule.run_all()
    assert len(runs) == 3
    assert job not in schedule.get_jobs()


def test_single_run_budget():
    runs = []
    schedule.every().second.max_runs(1).do(lambda: runs.append(1))
    schedule.run_all()
    schedule.run_all()
    assert len(runs) == 1
    assert schedule.get_jobs() == []


def test_chainable_and_position_flexible():
    j = schedule.every(2).seconds
    assert j.max_runs(2) is j
    runs = []
    schedule.every().max_runs(2).seconds.do(lambda: runs.append(1))
    for _ in range(3):
        schedule.run_all()
    # j never got .do(), so only the second job runs
    assert len(runs) == 2


def test_budget_reached_before_deadline():
    runs = []
    schedule.every().second.max_runs(2).until(
        datetime.timedelta(hours=1)
    ).do(lambda: runs.append(1))
    for _ in range(4):
        schedule.run_all()
    assert len(runs) == 2
    assert schedule.get_jobs() == []


def test_deadline_reached_before_budget():
    runs = []
    with mock_datetime(2026, 7, 7, 12, 0, 0):
        schedule.every().second.max_runs(10).until(
            datetime.datetime(2026, 7, 7, 12, 0, 30)
        ).do(lambda: runs.append(1))
    with mock_datetime(2026, 7, 7, 12, 0, 10):
        schedule.run_all()
    assert len(runs) == 1
    with mock_datetime(2026, 7, 7, 12, 0, 40):
        schedule.run_pending()
    assert len(runs) == 1
    assert schedule.get_jobs() == []


def test_run_pending_flow_respects_budget():
    runs = []
    with mock_datetime(2026, 7, 7, 12, 0, 0):
        schedule.every().second.max_runs(2).do(lambda: runs.append(1))
    with mock_datetime(2026, 7, 7, 12, 0, 2):
        schedule.run_pending()
    assert len(runs) == 1
    with mock_datetime(2026, 7, 7, 12, 0, 4):
        schedule.run_pending()
    assert len(runs) == 2
    with mock_datetime(2026, 7, 7, 12, 0, 6):
        schedule.run_pending()
    assert len(runs) == 2
    assert schedule.get_jobs() == []


@pytest.mark.parametrize("bad", [0, -1, 2.5, "3", None])
def test_invalid_n_raises_value_error(bad):
    job = schedule.every().second
    with pytest.raises(ValueError):
        job.max_runs(bad)


def test_last_call_wins():
    runs = []
    schedule.every().second.max_runs(5).max_runs(2).do(lambda: runs.append(1))
    for _ in range(4):
        schedule.run_all()
    assert len(runs) == 2


def test_budgets_are_per_job():
    a, b = [], []
    schedule.every().second.max_runs(1).do(lambda: a.append(1))
    schedule.every().second.max_runs(3).do(lambda: b.append(1))
    for _ in range(4):
        schedule.run_all()
    assert len(a) == 1
    assert len(b) == 3
    assert schedule.get_jobs() == []


def test_next_run_reflects_removal():
    schedule.every().second.max_runs(1).do(lambda: None)
    schedule.run_all()
    assert schedule.next_run() is None
    assert schedule.idle_seconds() is None
