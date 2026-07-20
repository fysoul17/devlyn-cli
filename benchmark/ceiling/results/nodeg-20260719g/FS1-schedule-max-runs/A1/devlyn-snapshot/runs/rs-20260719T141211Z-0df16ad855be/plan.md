# Plan — `Job.max_runs(n)` run-budget feature

<!-- devlyn:authorized-surface -->
## Files to touch

- `schedule/__init__.py` — **edit**. Add per-job run-budget state and the `Job.max_runs(n)` builder method; wire the budget check into `Job.run()`, the single method both `Scheduler.run_pending()` (`schedule/__init__.py:99-101`) and `Scheduler.run_all()` (`schedule/__init__.py:118-119`) call via `Scheduler._run_job()` (`schedule/__init__.py:172-175`), so both execution paths (and their module-level `schedule.run_pending()`/`schedule.run_all()` shortcuts) get the behavior for free (Requirements bullets 1–3, 5, 7).
- `test_schedule.py` — **edit**. Add a `test_max_runs` method to `SchedulerTests` (adjacent to `test_until_time`, `test_schedule.py:312`), following the existing `make_mock_job()` (`test_schedule.py:33-36`) / `mock_datetime` (`test_schedule.py:39-93`) helper patterns, covering: chainability at either point in the fluent chain, exact-n-executions-then-cancel with `schedule.run_pending()` and with `schedule.run_all()`, first-limit-wins interaction with `.until()`, validation errors for non-int/0/negative/None/float via `ScheduleValueError`, last-call-wins on repeated `.max_runs()` calls, and no cross-job interference with a second job on the same scheduler. Do not modify `test_until_time` or any other existing test (Requirements bullets 1–8, Constraints).
- `docs/examples.rst` — **edit**. Add one new prose + `.. code-block:: python` section (e.g. "Limit the number of runs"), placed after the existing "Run a job until a certain time" section (`docs/examples.rst:219-245`), mirroring that section's style (Requirement bullet 9, last clause).

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py", "docs/examples.rst"]}
```

## Risks

- **`docs/reference.rst` is intentionally NOT touched.** `docs/reference.rst:31-33` already autodocuments `Job` with `.. autoclass:: schedule.Job :members:`, so a docstring on `max_runs()` is automatically picked up. Editing `docs/reference.rst` would be an unrequested, redundant addition — refuse this expansion (Requirement bullet 9 only requires the docstring to exist; the anchor in `.devlyn/criteria.generated.md:8` confirms autodoc is "required and sufficient").
- **No public getter/property for remaining budget.** Explicitly out of scope (`.devlyn/criteria.generated.md:31`). The remaining-count state is a private instance attribute (e.g. `self._runs_remaining`), not exposed via `__repr__`/`__str__` or a new property. Do not add one "for completeness."
- **`ScheduleValueError`, not bare `ValueError`, for invalid `n`.** The user's goal text says "raises ValueError" but this codebase's idiom for job-configuration validation errors is `ScheduleValueError` (see `Job.until()` at `schedule/__init__.py:494,506,514,519,525,547,639` and `Job.at()`), which subclasses `ScheduleError` subclasses `Exception` — not `ValueError`. Using the library's own convention here is the idiomatic choice, not a deviation from user intent; treating "ValueError" literally would be inconsistent with every other validation call in `Job`.
- **`isinstance(n, int)` without special-casing `bool`.** Python's `bool` is a subclass of `int`, so `True`/`False` would pass `isinstance(n, int)` (as `1`/`0`). The requirements list only "non-int, `0`, negative, `None`, float" as invalid — `bool` is not mentioned, and no existing validation in this file (`.at()`, `.until()`, `.to()`) special-cases `bool`. Adding a `type(n) is int` or `isinstance(n, bool)` exclusion would be unrequested speculative robustness. Plan: validate with `not isinstance(n, int) or n < 1` only; `True` naturally satisfies `n >= 1` and behaves as `max_runs(1)`, `False` naturally fails as `n < 1`. This is a strict, minimal reading of the stated validation rule.
- **Counter must decrement only on the actual-execution path.** `Job.run()` (`schedule/__init__.py:674-698`) has an early return (`schedule/__init__.py:686-688`) when the job is already overdue per `.until()` — `job_func()` is never called on that path. The new budget decrement must sit strictly after `ret = self.job_func()` (`schedule/__init__.py:691`), not before, or the budget would be consumed by executions that never happened, violating "the budget counts actual executions."
- **Do not touch `.until()` / `_is_overdue()` logic.** The existing `if self._is_overdue(...)` checks (`schedule/__init__.py:686`, `695`) must remain byte-for-byte as-is; the new `max_runs` check is an additional, independent `if` block placed after the post-execution `_is_overdue` recompute point (or immediately before it — order doesn't change behavior since either `CancelJob` wins) so that `test_until_time` (`test_schedule.py:312-388`) passes unmodified, satisfying first-limit-wins without merging the two conditions into one.
- **Do not add a second removal path.** `Job.run()` must keep returning the sentinel `CancelJob` for `Scheduler._run_job()` (`schedule/__init__.py:172-175`) to act on — no direct `self.scheduler.cancel_job(self)` call from inside `Job`, preserving the single existing removal mechanism (Constraints bullet 1).
- **Last-call-wins is automatic, not special-cased.** `.max_runs(n)` unconditionally overwrites `self._runs_remaining = n`; no extra "already set" branch is needed or wanted (Requirement bullet 6).
- **Per-job isolation is automatic.** `_runs_remaining` is a plain instance attribute initialized in `Job.__init__`; no shared/class-level state, so no explicit cross-job-interference guard is needed (Requirement bullet 7) — the risk is only in verifying this with a test, not in implementation.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

### Requirements

- [ ] Add `Job.max_runs(n)`: chainable, returns `self`, usable at any point in the fluent chain (`schedule.every(5).seconds.max_runs(3).do(job_fn)` and `schedule.every().max_runs(3).seconds.do(job_fn)` both work).
- [ ] The budget counts actual executions of the job's function. After the job's function has executed `n` times in total, the job removes itself from its scheduler exactly as a job returning `CancelJob` does (same removal path/effect as existing `CancelJob` handling). The nth execution itself still runs normally; there must never be an (n+1)-th execution.
- [ ] Applies on every execution path that runs jobs through the scheduler: `Scheduler.run_pending()` and `Scheduler.run_all()` (and therefore the module-level `schedule.run_pending()` / `schedule.run_all()` shortcuts, which delegate to the default scheduler).
- [ ] Interaction with `.until(deadline)`: whichever limit is reached first cancels the job (first-limit-wins). Existing `.until()` semantics (deadline-only jobs, no `max_runs`) must not regress — verified by the existing `test_until_time` / related `until` tests continuing to pass unmodified.
- [ ] After a job exhausts its run budget and is removed, `Scheduler.next_run` / `Scheduler.idle_seconds` (and the module-level `schedule.next_run()` / `schedule.idle_seconds()` shortcuts) reflect the removal (i.e. no longer consider that job).
- [ ] Validation: `n` must be an integer `>= 1`; any other value (non-int, `0`, negative, `None`, float, etc.) raises `ScheduleValueError` (this library's convention for job-configuration validation errors, e.g. `Job.until()` and `Job.at()` both raise `ScheduleValueError` for invalid input — not a bare `ValueError`, since `ScheduleValueError` subclasses `ScheduleError` which subclasses `Exception`, not `ValueError`) at `.max_runs(...)` call time.
- [ ] Calling `.max_runs()` more than once on the same job: the last call wins (budget and remaining-count state reset to the new `n`).
- [ ] Budgets are per-job: multiple jobs with different (or no) `max_runs` budgets scheduled on the same scheduler must not interfere with each other's counts or cancellation.
- [ ] Document the new API alongside comparable `Job` methods: a docstring on `Job.max_runs()` (picked up by `docs/reference.rst` autodoc) plus a short prose + code example section in `docs/examples.rst` following the existing `.until()` / tagging section style.

### Verification

```json
{
  "verification_commands": [
    { "id": "V1", "cmd": "/opt/homebrew/bin/pytest test_schedule.py -q", "description": "Full existing test suite (81 tests as of base_ref) plus new max_runs tests must pass." }
  ]
}
```
