# Plan — max_runs exception-safety fix (outer-loop iteration 2)

<!-- devlyn:authorized-surface -->
## Files to touch

- `schedule/__init__.py` — edit. `Job.run()` (`schedule/__init__.py:691-724`): move the scheduler-removal for a budget-exhausting run from the post-`job_func()` `CancelJob`-return path to immediately after the `_remaining_runs` decrement, before `ret = self.job_func()` (`schedule/__init__.py:713`) is invoked. Satisfies Requirement "remove the job from its scheduler ... before `job_func()` is invoked ... guaranteed regardless of whether `job_func()` raises."
- `test_schedule.py` — edit. `test_max_runs_counts_raising_job_execution` (`test_schedule.py:461-469`): add an assertion that the job is no longer in the scheduler's job list immediately after the raising call, alongside the existing `assert job._remaining_runs == 0`. Satisfies Requirement "New regression test ... must no longer be present in `scheduler.jobs` immediately after the raising call (assert on scheduler membership, not just the internal counter)."

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py"]}
```

## Risks

- **No `try`/`except` around `job_func()`.** Explicitly out of scope (Requirement 3, Out of Scope). The fix is scheduler-removal timing only — `ret = self.job_func()` at `schedule/__init__.py:713` stays a bare call, unchanged in position and form.
- **No second cancellation path / no new `Scheduler` method.** Reuse `self.scheduler.cancel_job(self)` (`schedule/__init__.py:150-160`) exactly as it exists today. Do not add a `Job`-level removal helper or touch `Scheduler.cancel_job` itself.
- **Post-run `CancelJob` block stays as-is.** `schedule/__init__.py:717-719` (`if self._remaining_runs is not None and self._remaining_runs <= 0: return CancelJob`) must not be deleted or altered — on the non-raising exhausting run it still returns `CancelJob`, `Scheduler._run_job` (`schedule/__init__.py:172-175`) still calls `cancel_job`, and that second call is a documented pre-existing no-op via the `except ValueError` guard (Requirement 4). Removing this block would be scope expansion beyond the stated fix.
- **`self.scheduler` is assumed non-`None` at this point** — same assumption the existing code already makes (`Scheduler._run_job` only ever calls `job.run()` for jobs living in `self.jobs`, which requires `.do()` to have set `self.scheduler`, `schedule/__init__.py:675-680`). Do not add a defensive `None`-check; that would be unrequested robustness for an unobserved failure mode.
- **Do not add a new/duplicate `logger.debug` line for the new pre-emptive branch if it would double-log the same event** on the non-raising exhausting run (the post-run block at `schedule/__init__.py:718` already logs "Cancelling job %s" for that case). Minimal addition: the `if`-guard plus the `cancel_job` call; keep logging conservative or reuse the same message, but do not introduce new log statements beyond what's needed to mirror existing style — reviewer discretion at IMPLEMENT time, not a license to add unrelated logging.
- **Do not touch other `max_runs` tests or their assertions** (Constraints: "all existing tests ... must keep passing unmodified in their assertions"). Only `test_max_runs_counts_raising_job_execution` may be strengthened, by addition only — its existing `assert job._remaining_runs == 0` line stays.
- **Do not touch `.until()`, `.at()`, timezone handling, tagging, `.to()`** — explicitly out of scope and orthogonal to this code path.
- **Ambiguous scheduler-membership assertion form**: interpret strictly as checking the job is absent from `schedule.default_scheduler.jobs` (the scheduler `every()` in `test_schedule.py` registers against, per existing precedent at `test_schedule.py:232,1573,1606`) — equivalently `job.scheduler.jobs`. Either is acceptable; do not introduce a new scheduler instance or restructure the test beyond adding this one assertion.

## Acceptance restatement

Verbatim copy of the generated criteria's `## Verification` block:

```json
{"verification_commands": [{"cmd": "python3 -m unittest test_schedule", "exit_code": 0}]}
```
