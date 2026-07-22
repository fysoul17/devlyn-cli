# Generated criteria — run-budget feature (`Job.max_runs(n)`)

recommend: /devlyn:ideate first (large free-form goal; proceeding with a best-effort
spec and logged assumptions per the autonomy contract — no mid-pipeline prompts).

## Requirements

1. `Job.max_runs(n)` is a chainable setter that returns the `Job` instance itself,
   usable anywhere in the fluent chain, e.g.
   `schedule.every(5).seconds.max_runs(3).do(job_fn)` and
   `schedule.every().max_runs(3).seconds.do(job_fn)`.
2. The budget counts actual executions of the job function. After the job has
   executed `n` times in total, the job removes itself from its scheduler exactly
   as a job returning `CancelJob` does (same removal path as the existing
   `CancelJob` mechanism in `Scheduler._run_job` / `Job.run`). The nth execution
   itself still runs normally; an (n+1)-th execution must never happen.
3. Enforced on every path that runs jobs through the scheduler:
   `Scheduler.run_pending()` and `Scheduler.run_all()`, including the
   module-level `schedule.run_pending()` / `schedule.run_all()` wrappers that
   delegate to the default scheduler.
4. Interaction with `.until(deadline)`: whichever limit — run-count budget or
   until-deadline — is reached first cancels the job (first-limit-wins).
   Existing `.until()` semantics (deadline check before running, and after
   rescheduling) must not regress.
5. After a job exhausts its budget and is removed, `Scheduler.next_run` /
   `Scheduler.idle_seconds` (and the module-level `schedule.next_run()` /
   `schedule.idle_seconds()` wrappers) must reflect the removal.
6. Validation: `n` must be an `int >= 1`; any other value (wrong type, `<= 0`,
   non-integral) raises `ValueError` at `.max_runs(...)` call time, not at
   `.do()` or run time.
7. Calling `.max_runs()` more than once on the same job: the last call wins
   (the budget and the executed-count both reset to reflect only the latest
   call — no accumulation across calls).
8. Budgets are per-job: multiple jobs with different budgets scheduled on the
   same scheduler must not interfere with each other's counts or cancellation.
9. Document the new method wherever this project documents comparable `Job`
   methods (at minimum: the `Job.max_runs` docstring, and a usage example in
   `docs/examples.rst` alongside the existing `.until()` example).

## Constraints

- Follow the existing `schedule/__init__.py` single-module structure and the
  existing `CancelJob` / `ScheduleError` family conventions already used by
  `.until()` (`docs/examples.rst:219-245`, `schedule/__init__.py:576-642`) for
  style consistency, without overriding requirement 6's explicit `ValueError`
  contract.
- No new public module-level functions/classes beyond `Job.max_runs`; this is a
  `Job`-scoped API addition only.

## Out of Scope

- Anything not implied by the run-budget feature above (no unrelated
  refactors of `Scheduler`/`Job`, no changes to `.until()`'s own semantics
  beyond the first-limit-wins interaction).

## Assumptions

(Every assumption below is scope-narrowing and reversible.)

- A job function raising an exception during its `n`-th call still counts as
  an "actual execution" toward the budget (the call happened; `schedule`'s
  existing behavior lets caller-side exceptions propagate from `Job.run()`
  unmodified — this feature does not add new exception handling).
- `bool` is rejected by the `int >= 1` check (Python `bool` is a subclass of
  `int`; existing codebase validation patterns for other integer parameters —
  e.g. `interval` — do not special-case bool, so `max_runs` follows the same
  precedent and does not special-case it either).
- Documentation lands in `Job.max_runs`'s docstring plus one example block in
  `docs/examples.rst`; no new standalone doc page.

<!-- devlyn:verification -->
## Verification

- `python3 -m unittest discover -s . -p test_schedule.py -v` exits 0 with `OK`
  in the output; this runs the full existing suite plus new tests covering
  Requirements 1-9 (chainability in both call orders, budget enforcement
  through `run_pending()` and `run_all()`, the nth-run-executes /
  (n+1)th-never-happens boundary, `.until()` first-limit-wins in both
  orderings, `next_run`/`idle_seconds` reflecting removal, the `ValueError`
  validation matrix, last-call-wins on repeated `.max_runs()` calls, and
  per-job independence).
- `python3 -c "import schedule; j = schedule.every().seconds.max_runs(3); assert j is not None"`
  exits 0 — smoke check that `.max_runs(n)` returns the `Job` instance
  (Requirement 1).

```json
{
  "verification_commands": [
    {
      "cmd": "python3 -m unittest discover -s . -p test_schedule.py -v",
      "exit_code": 0,
      "stdout_contains": ["OK"]
    },
    {
      "cmd": "python3 -c \"import schedule; j = schedule.every().seconds.max_runs(3); assert j is not None\"",
      "exit_code": 0
    }
  ]
}
```
