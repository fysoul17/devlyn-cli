# Generated criteria — run-budget feature (`Job.max_runs`)

Source: free-form goal, `.devlyn/goal.raw.txt` (medium complexity).

## Requirements

- Add `Job.max_runs(n)` as a chainable setter (returns `self`) usable at any point in the fluent chain — e.g. `schedule.every(5).seconds.max_runs(3).do(job_fn)` and `schedule.every().max_runs(3).seconds.do(job_fn)`.
- `n` must be an `int >= 1`; any other value (non-int, `0`, negative, `None`, float, etc.) raises `ValueError` at `.max_runs(...)` call time. Calling `.max_runs()` more than once on the same job — the last call wins.
- The budget counts actual invocations of `job_func`. After the job has executed `n` times in total, the job removes itself from its scheduler exactly as a job returning `CancelJob` does (`Scheduler._run_job` / `Scheduler.cancel_job`). The nth execution itself still runs normally; an (n+1)th execution must never happen. This must hold for every execution path that runs jobs through the scheduler — `Scheduler.run_pending()` and `Scheduler.run_all()`.
- First-limit-wins interaction with `.until(deadline)`: whichever limit (run-count budget or `.until()` deadline) is reached first cancels the job. Existing `.until()` / `cancel_after` / `Job._is_overdue` semantics must not regress. Budgets are per-job: multiple jobs with different budgets must not interfere with each other.
- After a job exhausts its budget and self-cancels, `Scheduler.next_run` / `Scheduler.idle_seconds` must reflect its removal, same as any other cancelled job.

## Constraints

- Match the existing Job builder-pattern style: every other chainable setter (`.tag()`, `.to()`, `.until()`, `.at()`) returns `self`; `.max_runs()` must do the same.
- Reuse the existing `CancelJob` cancellation mechanism (`Job.run()` returning `CancelJob`, handled by `Scheduler._run_job`) rather than adding a second, parallel cancellation path.
- Stdlib only — no new dependencies, consistent with the rest of `schedule/__init__.py`.
- Document the new method wherever comparable `Job` methods are documented: a docstring on `Job.max_runs` (picked up by `docs/reference.rst`'s `autoclass:: schedule.Job`) and a short usage example alongside the existing `until()` example in `docs/examples.rst`.

## Out of Scope

- Anything not `Job.max_runs()` and its interaction with `.until()`, `run_pending()`, `run_all()`, `next_run`, and `idle_seconds` — e.g. no changes to `.at()`, timezone handling, `.to()` randomized intervals, or tagging.
- No new public `Scheduler` methods.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands": [{"cmd": "python3 -m unittest test_schedule", "exit_code": 0}]}
```
