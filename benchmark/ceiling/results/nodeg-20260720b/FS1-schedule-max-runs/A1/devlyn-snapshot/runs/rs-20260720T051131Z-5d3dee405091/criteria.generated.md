# Generated criteria — run-budget feature (Job.max_runs)

## Requirements

- `Job.max_runs(n)` is a chainable setter on `Job` usable anywhere in the fluent chain (e.g. `schedule.every(5).seconds.max_runs(3).do(job_fn)` and `schedule.every().max_runs(3).seconds.do(job_fn)`) and returns the `Job` instance.
- The budget counts actual executions of `job_func`. After the job has executed `n` times in total, the job removes itself from its scheduler exactly as a job returning `CancelJob` does. The nth execution itself still runs normally; an (n+1)-th execution must never happen. This applies through every execution path that runs jobs through the scheduler, including both `run_pending()` and `run_all()`.
- Interaction with `.until(deadline)` is first-limit-wins: whichever limit (run budget or until deadline) is reached first cancels the job. Existing `.until()` semantics (docs/reference.rst autodoc of `Job.until`, `test_schedule.py::test_until_time`) must not regress.
- After a job exhausts its budget, `Scheduler.next_run` / `Scheduler.idle_seconds` reflect its removal (recomputed from the remaining scheduled jobs).
- Validation: `n` must be an integer >= 1; any other value raises `ValueError` at `.max_runs(...)` call time (the codebase's `ScheduleValueError` already subclasses `ValueError` — see `Job.until()`, `Job.at()`). Calling `.max_runs()` more than once on the same job: the last call wins. Budgets are per-job — multiple jobs with different budgets must not interfere with each other.

## Constraints

- Reuse the existing `CancelJob` removal mechanism (`Job.run()` returns `CancelJob`; `Scheduler._run_job()` calls `self.cancel_job(job)` when `isinstance(ret, CancelJob) or ret is CancelJob`) rather than adding a parallel removal path — this is how `.until()` already integrates with `run_pending()`/`run_all()`.
- Document `max_runs` with a docstring in the same style as `Job.until()` / `Job.run()` in `schedule/__init__.py` — `docs/reference.rst` autodocs `Job` via `.. autoclass:: schedule.Job`, so the docstring is the documentation; no separate prose doc file needs hand-editing.
- Match existing validation idiom: raise `ScheduleValueError` (not a bare `ValueError`) for invalid `n`, consistent with `until()`'s `ScheduleValueError` usage elsewhere in `Job`.

## Out of Scope

- Anything not in `schedule/__init__.py`, `test_schedule.py`, or `docs/reference.rst`.
- No behavior change to unrelated `Job`/`Scheduler` methods (tags, `.at()`, `.to()`, unit chains, `.until()`'s own semantics beyond the first-limit-wins interaction).

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "/opt/homebrew/bin/python3 -m pytest test_schedule.py -q", "expect_exit": 0 }
  ]
}
```
