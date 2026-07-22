"""
P2 - Compound probe for Requirement 2 (nth execution runs, (n+1)th never
happens), Requirement 4 (first-limit-wins between the run-count budget and
.until(deadline), in both orderings), and Requirement 8 (per-job
independence).

Two jobs share one scheduler:
  - job_a: max_runs(2) reached BEFORE its own until() deadline
           (budget is the first limit for job_a).
  - job_b: max_runs(100) (never reached) but its until() deadline is
           reached BEFORE the budget could ever matter
           (deadline is the first limit for job_b).

This directly targets an ordering-inversion bug: an implementation that
checks the two limits in a fixed code order (e.g. "if a budget is
configured, only check the budget and skip the deadline check") would
fail to cancel job_b at the right time, because job_b DOES have a budget
configured (100) that is nowhere near exhausted. Only an implementation
that evaluates both limits independently, and cancels on whichever is
actually reached first, passes this probe.

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


def job_a():
    calls["a"] += 1


def job_b():
    calls["b"] += 1


try:
    schedule.clear()

    _freeze(_real_datetime(2020, 1, 1, 11, 35, 0))
    job_obj_a = (
        schedule.every(5)
        .seconds.max_runs(2)
        .until(_real_datetime(2020, 1, 1, 11, 36, 0))
        .do(job_a)
    )
    job_obj_b = (
        schedule.every(5)
        .seconds.max_runs(100)
        .until(_real_datetime(2020, 1, 1, 11, 35, 12))
        .do(job_b)
    )
    assert len(schedule.jobs) == 2

    # Tick 1 (t=11:35:05): both jobs are due, neither limit reached yet.
    _freeze(_real_datetime(2020, 1, 1, 11, 35, 5))
    schedule.run_pending()
    assert calls == {"a": 1, "b": 1}, f"tick1 calls={calls}"
    assert len(schedule.jobs) == 2, "neither job should cancel on tick 1"

    # Tick 2 (t=11:35:10): job_a's budget is exhausted by its 2nd (nth)
    # execution -> it must run this time, then be removed (Req 2).
    # job_b's until deadline (11:35:12) is not yet passed by "now"
    # (11:35:10 <= 11:35:12), so it still runs; but its NEXT scheduled run
    # would be 11:35:15, which IS past 11:35:12, so job_b is cancelled by
    # the deadline check on this same tick -- while its budget (100) is
    # nowhere near exhausted (Req 4, "deadline wins first" ordering).
    _freeze(_real_datetime(2020, 1, 1, 11, 35, 10))
    schedule.run_pending()
    assert calls == {"a": 2, "b": 2}, f"tick2 calls={calls}"
    assert len(schedule.jobs) == 0, "both jobs should be cancelled by tick 2"

    # Req 8: per-job independence -- each job was cancelled for its OWN
    # reason, not the other's.
    assert job_obj_a.max_runs_remaining == 0, (
        "job_a should be cancelled because its budget hit 0"
    )
    assert job_obj_b.max_runs_remaining == 98, (
        f"job_b's budget must be far from exhausted "
        f"(got {job_obj_b.max_runs_remaining}); it must have been "
        f"cancelled by its until() deadline instead, independent of "
        f"job_a's budget-based cancellation"
    )

    # Req 2: the (n+1)th execution must never happen for job_a -- neither
    # job is even in the scheduler any more, so a further run_pending()
    # must not change either call count.
    _freeze(_real_datetime(2020, 1, 1, 11, 35, 15))
    schedule.run_pending()
    assert calls == {"a": 2, "b": 2}, f"post-cancel tick calls={calls}"

    print("PROBE_P2_OK")
finally:
    datetime.datetime = _real_datetime
