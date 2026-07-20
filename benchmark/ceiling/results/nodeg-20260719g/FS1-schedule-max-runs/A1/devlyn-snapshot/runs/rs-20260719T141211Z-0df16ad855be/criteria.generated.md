# Generated criteria — run-budget feature for `schedule` library

Source: free-form goal (`.devlyn/goal.raw.txt`), complexity = medium.

## Context anchors

- `schedule/__init__.py`: `Job` is a fluent builder (`Job.until()`, `Job.tag()`, `Job.to()` all return `self`); `Job.run()` executes `self.job_func()` then reschedules, returning `CancelJob` when `_is_overdue()` (driven by `self.cancel_after`, set by `.until()`); `Scheduler._run_job()` calls `job.run()` and cancels the job via `self.cancel_job(job)` when the return value `is CancelJob`. `Scheduler.run_pending()` and `Scheduler.run_all()` both funnel through `_run_job()`. `Scheduler.get_next_run()` / `idle_seconds` derive from `self.jobs`, so removal via `cancel_job()` already updates them — no separate bookkeeping needed if `max_runs` reuses the `CancelJob` path.
- `docs/examples.rst` documents comparable `Job` methods (e.g. "Run a job until a certain time" for `.until()`) as a short prose + code-block section under `docs/examples.rst`; `docs/reference.rst` autodocuments `Job` via `.. autoclass:: schedule.Job :members:`, so a proper docstring on `max_runs()` is required and sufficient for the reference page.
- `test_schedule.py::SchedulerTests.test_until_time` is the closest existing test pattern for a chainable deadline-setter; new tests should follow the existing `make_mock_job()` / `mock_datetime()` helpers already used throughout the file.

## Requirements

- [ ] Add `Job.max_runs(n)`: chainable, returns `self`, usable at any point in the fluent chain (`schedule.every(5).seconds.max_runs(3).do(job_fn)` and `schedule.every().max_runs(3).seconds.do(job_fn)` both work).
- [ ] The budget counts actual executions of the job's function. After the job's function has executed `n` times in total, the job removes itself from its scheduler exactly as a job returning `CancelJob` does (same removal path/effect as existing `CancelJob` handling). The nth execution itself still runs normally; there must never be an (n+1)-th execution.
- [ ] Applies on every execution path that runs jobs through the scheduler: `Scheduler.run_pending()` and `Scheduler.run_all()` (and therefore the module-level `schedule.run_pending()` / `schedule.run_all()` shortcuts, which delegate to the default scheduler).
- [ ] Interaction with `.until(deadline)`: whichever limit is reached first cancels the job (first-limit-wins). Existing `.until()` semantics (deadline-only jobs, no `max_runs`) must not regress — verified by the existing `test_until_time` / related `until` tests continuing to pass unmodified.
- [ ] After a job exhausts its run budget and is removed, `Scheduler.next_run` / `Scheduler.idle_seconds` (and the module-level `schedule.next_run()` / `schedule.idle_seconds()` shortcuts) reflect the removal (i.e. no longer consider that job).
- [ ] Validation: `n` must be an integer `>= 1`; any other value (non-int, `0`, negative, `None`, float, etc.) raises `ScheduleValueError` (this library's convention for job-configuration validation errors, e.g. `Job.until()` and `Job.at()` both raise `ScheduleValueError` for invalid input — not a bare `ValueError`, since `ScheduleValueError` subclasses `ScheduleError` which subclasses `Exception`, not `ValueError`) at `.max_runs(...)` call time.
- [ ] Calling `.max_runs()` more than once on the same job: the last call wins (budget and remaining-count state reset to the new `n`).
- [ ] Budgets are per-job: multiple jobs with different (or no) `max_runs` budgets scheduled on the same scheduler must not interfere with each other's counts or cancellation.
- [ ] Document the new API alongside comparable `Job` methods: a docstring on `Job.max_runs()` (picked up by `docs/reference.rst` autodoc) plus a short prose + code example section in `docs/examples.rst` following the existing `.until()` / tagging section style.

## Constraints

- Keep the existing `CancelJob` / `_run_job()` removal mechanism as the single removal path; do not add a second, parallel job-removal code path in `Scheduler`.
- Match existing validation conventions: raise `schedule.ScheduleValueError` (not bare `ValueError`) for invalid `n`, consistent with `Job.until()`/`Job.at()`.
- Preserve backward compatibility: jobs that never call `.max_runs()` behave exactly as before.

## Out of Scope

- Anything not required by the bullets above (e.g. persisting run counts across process restarts, exposing a public getter/property for the remaining budget, CLI/config surface — none requested).
- Pre-existing code style, unrelated docs sections, or unrelated test refactors.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "id": "V1", "cmd": "/opt/homebrew/bin/pytest test_schedule.py -q", "description": "Full existing test suite (81 tests as of base_ref) plus new max_runs tests must pass." }
  ]
}
```
