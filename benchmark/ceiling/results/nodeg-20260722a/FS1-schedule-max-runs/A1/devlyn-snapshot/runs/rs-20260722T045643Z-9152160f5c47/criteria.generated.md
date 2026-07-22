# Free-form criteria — run-budget feature for `schedule.Job`

## Requirements

1. `Job.max_runs(n)` is a chainable setter that returns the `Job` instance
   itself, usable anywhere in the fluent chain — both
   `schedule.every(5).seconds.max_runs(3).do(job_fn)` and
   `schedule.every().max_runs(3).seconds.do(job_fn)` must work.
2. The budget counts actual executions of `job_func` (the call inside
   `Job.run()`), not `.do()` registration or `should_run` checks. After the
   job has executed `n` times in total, the job removes itself from its
   scheduler exactly as a job returning `CancelJob` does (i.e. `Job.run()`
   returns `CancelJob` on/after the nth execution so `Scheduler._run_job`
   cancels it the same way it cancels any other `CancelJob`-returning job).
   The nth execution itself still calls `job_func` normally; an (n+1)th call
   to `job_func` must never happen.
3. Applies to every path that runs jobs through the scheduler:
   `Scheduler.run_pending()` and `Scheduler.run_all()` (and therefore the
   module-level `schedule.run_pending()` / `schedule.run_all()` shortcuts,
   which delegate to the same `Scheduler` methods).
4. Interaction with `.until(deadline)` is first-limit-wins: whichever of the
   deadline or the run-budget is reached first cancels the job. Existing
   `.until()`-only behavior (no `.max_runs()` call) must not regress —
   the existing `until()`/`cancel_after` tests must keep passing unchanged.
5. After a job is cancelled for exhausting its run budget,
   `Scheduler.next_run` / `Scheduler.idle_seconds` (and the module-level
   `schedule.next_run()` / `schedule.idle_seconds()` shortcuts) must reflect
   the job's removal, matching the existing behavior already asserted for
   `CancelJob`/deadline-triggered removal.
6. Validation: `.max_runs(n)` raises when `n` is not an integer >= 1. The
   raised exception must satisfy `isinstance(exc, ValueError)` (goal's
   literal requirement) while also fitting this codebase's idiom of raising
   `ScheduleValueError` for Job configuration validation errors (see
   `.at()`, `.until()`, `_schedule_next_run()`). Reconcile the two —
   e.g. by making `ScheduleValueError` additionally inherit from the
   built-in `ValueError` — rather than raising a disconnected bare
   `ValueError` that breaks the existing `except ScheduleValueError` idiom
   used elsewhere in this module.
7. Calling `.max_runs()` more than once on the same job: the last call's `n`
   wins (replaces any previously configured budget). Re-configuring the
   budget must not reset the job's already-accumulated execution count.
8. Budgets are per-job instance: two jobs with different (or absent)
   `.max_runs()` budgets scheduled on the same scheduler must not interfere
   with each other's counts or cancellation.

## Constraints

- Mirror the existing `Job.run()` shape: the post-run `_is_overdue` check
  already discards `job_func`'s return value and returns `CancelJob`
  instead when the deadline is crossed — the run-budget check follows the
  same pattern (checked after `job_func` executes and the job reschedules).
- Store the budget and the run counter as internal `Job` attributes distinct
  from the `max_runs` method name (mirrors existing precedent: `to(latest)`
  stores into `self.latest`, `until(until_time)` stores into
  `self.cancel_after` — the setter method name and its backing attribute
  name are never the same, because `self.max_runs = n` inside a method
  named `max_runs` would shadow the method itself on that instance for all
  subsequent calls).
- Follow existing docstring conventions (`:param:`, `:return:`) so Sphinx's
  `autoclass Job :members:` in `docs/reference.rst` picks up the new method
  automatically — no manual edit to `docs/reference.rst` is needed.
- `docs/examples.rst` documents each comparable `Job` method (`.until()`,
  `CancelJob`) as its own titled section with a runnable code example —
  add an analogous section for `.max_runs()` there.
- Match existing code style (this project uses `black` formatting, per
  `tox.ini`'s `format` env).

## Out of Scope

- Changing `.until()`'s own semantics beyond the first-limit-wins
  interaction this feature requires.
- Changing `CancelJob` / `Scheduler.cancel_job` mechanics beyond what
  `max_runs` needs to plug into.
- Persisting or serializing run counts across process restarts.
- A public API to reset or inspect the remaining budget/count (not
  requested).
- `HISTORY.rst` (changelog is maintainer-curated at release time, not part
  of an unreleased in-progress change).
- pytz/timezone-related code paths.

<!-- devlyn:verification -->
## Verification

```json
{
  "verification_commands": [
    {
      "cmd": "python3 -m unittest test_schedule -v",
      "description": "Full existing test suite plus new max_runs() tests must pass (stdlib unittest — no pytest install required in this environment; test_schedule.py is unittest.TestCase-based)."
    }
  ]
}
```
