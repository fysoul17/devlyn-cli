# Generated criteria — run-budget feature (`Job.max_runs`)

Source: free-form goal at `.devlyn/goal.raw.txt` (sha256 `0194d750427cec5c6a6f6c3e0196e7ba20f0238162648ca1db6bbe4ce2b5a309`).

## Requirements

- [ ] `Job.max_runs(n)` is a chainable setter that returns the `Job` instance, callable anywhere in the fluent chain (e.g. `schedule.every(5).seconds.max_runs(3).do(job_fn)` and `schedule.every().max_runs(3).seconds.do(job_fn)` are both valid and equivalent).
- [ ] Validation: `n` must be an `int` and `n >= 1`; any other value (wrong type, `0`, negative, `bool` is accepted only because `bool` is an `int` subclass — treat per Python's normal `isinstance(n, int)` semantics) raises `ValueError` at `.max_runs(...)` call time, not later. Calling `.max_runs()` more than once on the same job: the last call's value wins (no accumulation, no exception).
- [ ] The budget counts actual executions of the job function (i.e. increments only when `Job.run()` actually calls `job_func`, not on skipped/overdue runs). After the job has executed `n` times in total, the job removes itself from its scheduler exactly as a job returning `CancelJob` does (same `Scheduler._run_job` removal path). The n-th execution itself must still run normally; an (n+1)-th execution must never happen.
- [ ] The budget is enforced on every execution path that runs jobs through the scheduler, including `Scheduler.run_pending()` and `Scheduler.run_all()` (both call `Scheduler._run_job` -> `Job.run()`, so the enforcement point is `Job.run()`/its return value).
- [ ] Interaction with `.until(deadline)`: first-limit-wins. Whichever of {run budget exhausted, `.until()` deadline reached} occurs first cancels the job. Existing `.until()` semantics (deadline checked before running, and re-checked after computing the next run) must not regress.
- [ ] After a job exhausts its budget and is removed, `Scheduler.next_run` / `Scheduler.idle_seconds` (and the module-level `schedule.next_run()` / `schedule.idle_seconds()` shortcuts) reflect the removal (i.e. no longer consider that job).
- [ ] Budgets are per-job: two or more jobs with different `max_runs(n)` values scheduled on the same scheduler run and expire independently without interfering with each other's counts.
- [ ] Document `.max_runs()` next to the existing comparable Job methods: a docstring on `Job.max_runs` consistent with sibling methods (`Job.until`, `Job.tag`) so it is picked up by `docs/reference.rst`'s `autoclass:: schedule.Job` `:members:`, plus a short usage example in `docs/examples.rst` alongside the existing "Run a job until a certain time" / "Run a job once" sections.

## Constraints

- Follow the existing codebase's builder-pattern style: setters return `self`, validation errors raise `schedule.ScheduleValueError` (a `ScheduleValueError` — the library's existing convention for validation errors, e.g. `Job.until`, `Job.at`) or a bare `ValueError` — the goal explicitly says `ValueError`, and `ScheduleValueError` already subclasses `ValueError`, so raising `ScheduleValueError` satisfies both the goal's literal `ValueError` requirement and the codebase's convention.
- Job cancellation must reuse the existing `CancelJob` removal mechanism (`Job.run()` returning `CancelJob`, consumed by `Scheduler._run_job`) rather than a parallel removal path.
- No new external dependencies.

## Out of Scope

- Anything not related to `Job.max_runs` / run-budget counting (no unrelated refactors of `Job` or `Scheduler`).
- Persisting run counts across process restarts.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "python3 -m unittest test_schedule -v", "description": "Full existing unittest suite (repo's runnable test entrypoint; pytest is declared in tox.ini but not installed in this environment, and test_schedule.py is unittest.TestCase-based so unittest runs it directly) must keep passing with the new tests included." }
  ]
}
```
