# Generated criteria — max_runs exception-safety fix (outer-loop iteration 2)

Source: free-form goal, `.devlyn/goal.raw.txt` (medium complexity). Follow-up to run `rs-20260720T040421Z-4402cc885dcc`, which shipped `Job.max_runs()` but left VERIFY `NEEDS_WORK` after two independent rounds: `job_func()` raising on the budget-exhausting call leaves the job scheduled (cancellation only happens via `return CancelJob` at the end of `Job.run()`, never reached on a raise), letting a later `run_pending()`/`run_all()` invoke `job_func()` again.

## Requirements

- When the run budget (`Job._remaining_runs`, `schedule/__init__.py`) reaches zero on this invocation, remove the job from its scheduler via the existing `self.scheduler.cancel_job(self)` call **before** `job_func()` is invoked, so removal happens no later than immediately before the exhausting call — guaranteed regardless of whether `job_func()` raises.
- The exhausting (nth) execution must still call `job_func()` normally — do not skip or gate the call itself; only the scheduler-removal timing moves earlier.
- Do not add `try`/`except` around `job_func()`. Exception handling for job_func failures is explicitly out of scope; the fix is scheduler-removal timing only.
- The existing success-path behavior must be unchanged: `job_func()`'s return value is still captured and returned from `Job.run()` when it doesn't raise; `Scheduler._run_job`'s existing `CancelJob`-return-based removal still functions (calling `cancel_job` on an already-removed job is a pre-existing no-op, per `Scheduler.cancel_job`'s `except ValueError` guard).
- New regression test: a job with `max_runs(1)` whose `job_func` raises on its call must no longer be present in `scheduler.jobs` immediately after the raising call (assert on scheduler membership, not just the internal counter).

## Constraints

- Touch only `schedule/__init__.py` and `test_schedule.py`. No doc changes needed (the public `Job.max_runs()` contract and its docstring are unchanged; only internal cancellation-timing behavior changes).
- Reuse the existing `Scheduler.cancel_job` method — do not add a new public `Scheduler` method or a second cancellation path.
- All existing tests (including the `max_runs` tests added in the prior iteration) must keep passing unmodified in their assertions, except the specific prior regression test for this exact gap (`test_max_runs_counts_raising_job_execution` in `test_schedule.py`, added in run `rs-20260720T040421Z-4402cc885dcc` round 2) may be extended/strengthened to also assert scheduler-membership removal, since it directly targets this defect.

## Out of Scope

- Any behavior around `job_func()` raising beyond guaranteeing scheduler removal (no retry logic, no exception suppression, no logging changes).
- `.until()`, `.at()`, timezone handling, tagging, `.to()` randomized intervals — unaffected by this fix.

<!-- devlyn:verification -->
## Verification

```json
{"verification_commands": [{"cmd": "python3 -m unittest test_schedule", "exit_code": 0}]}
```
