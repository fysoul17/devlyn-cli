# Generated criteria — run-budget feature for `schedule`

Source: free-form goal (`.devlyn/goal.raw.txt`). Complexity: medium.

## Requirements

- [ ] `Job.max_runs(n)` is a chainable setter (returns the `Job` instance, matching the existing pattern of `tag()`, `to()`, `until()`) and is usable at any point in the fluent chain before `.do()`, e.g. `schedule.every(5).seconds.max_runs(3).do(job_fn)` and `schedule.every().max_runs(3).seconds.do(job_fn)`.
- [ ] The budget counts actual executions of the job function (not scheduler ticks). After the job has executed `n` times in total, the job removes itself from its scheduler exactly as a job returning `CancelJob` from `Job.run()` does today (see `Scheduler._run_job`). The nth execution itself still runs normally; an (n+1)th execution must never happen.
- [ ] Applies to every execution path that runs jobs through the scheduler: `Scheduler.run_pending()` and `Scheduler.run_all()` (both funnel through `Scheduler._run_job` → `Job.run()`).
- [ ] Interaction with `.until(deadline)`: whichever limit (run-count budget or `cancel_after` deadline) is reached first cancels the job — first-limit-wins. Existing `.until()` / `cancel_after` / `_is_overdue` semantics must not regress (see `test_until_time` in `test_schedule.py`).
- [ ] After a job exhausts its budget, `Scheduler.next_run` / `Scheduler.idle_seconds` must reflect its removal (falls out naturally once the job is removed from `Scheduler.jobs`, same as the existing `.until()` cancellation path).
- [ ] Validation: `n` must be an integer `>= 1`; any other value raises `ValueError` (builtin, not `ScheduleValueError`) at `.max_runs(...)` call time — this is an explicit, literal requirement from the goal text and intentionally diverges from this codebase's usual `ScheduleValueError` convention for setter validation.
- [ ] Calling `.max_runs()` more than once on the same job: the last call wins (overwrites the stored budget, does not accumulate).
- [ ] Budgets are per-job: multiple jobs with different budgets must not interfere with each other (per-instance state, no shared counters).
- [ ] `Job.max_runs` gets a docstring consistent with sibling methods (`tag()`, `to()`, `until()`); `docs/reference.rst` autodocs `schedule.Job` with `:members:`, so no manual doc-page edit is required beyond the docstring itself.

## Constraints

- Match existing chainable-setter style in `schedule/__init__.py` (`Job.tag`, `Job.to`, `Job.until`): validate eagerly in the setter, store state on `self`, `return self`.
- Integrate with the existing cancellation flow in `Job.run()` / `Job._is_overdue()` rather than adding parallel scheduler-side bookkeeping — `Scheduler._run_job` already unschedules a job whenever `Job.run()` returns `CancelJob`.
- Do not change `.until()`'s own validation, string-parsing, or timezone behavior.
- Keep the new attribute(s) initialized in `Job.__init__` so per-job state is isolated (mirrors `self.cancel_after`, `self.tags`, etc.).

## Out of Scope

- Persisting run counts across process restarts.
- Changing `.until()` semantics beyond what first-limit-wins interaction requires.
- Any change to `repeat()` beyond what already works because `Job.max_runs()` is chainable and returns the `Job` passed into `repeat()`.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    { "cmd": "python3 -m unittest test_schedule.py -v", "expect_exit_code": 0 }
  ]
}
```
