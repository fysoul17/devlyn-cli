"""
P3 - Requirement 7 (last-call-wins on repeated .max_runs() calls, no
accumulation across calls) combined with Requirement 5 (next_run /
idle_seconds reflect job removal once the budget is exhausted) and
Requirement 8 (per-job independence: a second, unrelated job's budget
must not interfere with the first job's, and next_run/idle_seconds
must correctly move on to the surviving job once the first is removed).

Pre-implementation baseline: Job.max_runs does not exist, so this is
expected to fail with AttributeError at job scheduling time.
"""
import datetime
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
import schedule


class _FrozenDatetime(datetime.datetime):
    _frozen_now = None

    @classmethod
    def now(cls, tz=None):
        return cls._frozen_now


def _freeze(dt):
    _FrozenDatetime._frozen_now = dt
    datetime.datetime = _FrozenDatetime


_real_datetime = datetime.datetime

calls = {"a": 0, "b": 0}


def job_a_fn():
    calls["a"] += 1


def job_b_fn():
    calls["b"] += 1


try:
    schedule.clear()
    _freeze(_real_datetime(2020, 1, 1, 12, 0, 0))
    job_a = schedule.every(5).seconds.max_runs(5).do(job_a_fn)
    # job_b runs far less often and has a much larger budget, so it is
    # still alive long after job_a is removed -- proves per-job
    # independence (Requirement 8) and gives a surviving job for the
    # "next_run/idle_seconds move on to the other entity" check below.
    job_b = schedule.every(1).hours.max_runs(1000).do(job_b_fn)

    # Req 5 (pre-removal baseline): while job_a is scheduled, it is the
    # earliest job, so next_run/idle_seconds must reflect it specifically.
    assert schedule.next_run() == job_a.next_run
    assert schedule.next_run() != job_b.next_run

    # First execution of job_a under the original budget of 5.
    _freeze(_real_datetime(2020, 1, 1, 12, 0, 5))
    schedule.run_pending()
    assert calls == {"a": 1, "b": 0}
    assert len(schedule.jobs) == 2

    # Req 7: calling .max_runs() again overwrites the remaining budget --
    # last call wins, no accumulation with the 4 remaining from the first
    # call (would be 4, or 4+2=6 if buggy; must be exactly 2).
    job_a.max_runs(2)
    assert job_a.max_runs_remaining == 2, (
        f"last .max_runs(2) call must set remaining to exactly 2, "
        f"got {job_a.max_runs_remaining}"
    )

    # Two more executions under the NEW budget of 2: the 2nd of these
    # (job_a's 3rd execution overall) must exhaust the budget and remove
    # job_a, even though 5 was the originally-configured total. job_b's
    # own budget (1000) must be completely unaffected (Requirement 8).
    _freeze(_real_datetime(2020, 1, 1, 12, 0, 10))
    schedule.run_pending()
    assert calls == {"a": 2, "b": 0}
    assert len(schedule.jobs) == 2, "budget of 2 has one execution left"

    _freeze(_real_datetime(2020, 1, 1, 12, 0, 15))
    schedule.run_pending()
    assert calls == {"a": 3, "b": 0}
    assert len(schedule.jobs) == 1, (
        "job_a must be removed after its 2nd execution under the reset "
        "budget of 2, not after 5 total executions"
    )
    assert schedule.jobs == [job_b], "job_b must survive, untouched by job_a's budget"
    assert job_b.max_runs_remaining == 1000, (
        "job_b's independent budget must be unaffected by job_a's exhaustion"
    )

    # Req 5: once job_a is removed, next_run/idle_seconds (both the
    # Scheduler properties and the module-level wrappers) must reflect
    # the removal by moving on to job_b's state -- not by returning stale
    # data for job_a and not by incorrectly returning None while job_b is
    # still scheduled.
    assert schedule.next_run() == job_b.next_run, (
        "next_run must move on to the surviving job_b once job_a is removed"
    )
    assert schedule.idle_seconds() is not None
    assert schedule.default_scheduler.next_run == job_b.next_run
    assert schedule.default_scheduler.idle_seconds is not None

    # Now remove job_b too (drain its tiny remaining budget by driving
    # run_all(), which runs regardless of schedule) and confirm next_run/
    # idle_seconds finally go to None once no jobs remain at all.
    for _ in range(1000):
        schedule.run_all()
    assert len(schedule.jobs) == 0
    assert schedule.next_run() is None, "next_run must reflect total removal"
    assert schedule.idle_seconds() is None, "idle_seconds must reflect total removal"

    print("PROBE_P3_OK")
finally:
    datetime.datetime = _real_datetime
