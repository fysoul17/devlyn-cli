<!-- devlyn:authorized-surface -->
# Files to touch

- `schedule/__init__.py` — edit — add `Job.max_runs(n)` chainable setter, `Job.run_count`/`Job._max_runs` instance state, and a budget check in `Job.run()`. Implements Requirements bullets 1 (chainable setter usable anywhere in the fluent chain, returns `Job`), 2 (budget counts actual executions; self-removal via the existing `CancelJob` path; nth execution runs normally, no (n+1)th), 3 (first-limit-wins with `.until()`), 4 (`next_run`/`idle_seconds` reflect removal — inherited for free from the existing `CancelJob` → `Scheduler.cancel_job()` mechanism), and 5 (validation raises `ScheduleValueError`, last-call-wins, per-job independence).
- `test_schedule.py` — edit — add tests exercising: chainable usage in both example orderings from Requirement 1; budget enforcement through both `run_pending()` and `run_all()`; nth execution still calls `job_func` and no (n+1)th call ever happens; first-limit-wins against `.until()` in both directions (budget-first and deadline-first); `next_run`/`idle_seconds` after budget-triggered removal; `ScheduleValueError` on invalid `n` (non-int, `< 1`); last-call-wins on repeated `.max_runs()` calls; two jobs with different budgets not interfering. Existing tests (`test_until_time`, `test_cancel_job`, `test_cancel_jobs`, and the rest of the 90+ suite) are contract and are not modified or weakened.

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py"]}
```

`docs/reference.rst` is intentionally **not** touched: `.. autoclass:: schedule.Job` with `:members: :undoc-members:` (docs/reference.rst:31-33) already autodocs every public method on `Job`, including the new `max_runs` docstring, per Constraint 2.

# Risks

**Out-of-scope expansions to refuse:**
- No top-level `schedule.max_runs(...)` module-level shortcut. Scheduler-level ops (`every`, `run_pending`, `run_all`, `get_jobs`, `clear`, `cancel_job`, `next_run`, `idle_seconds`, `repeat` — schedule/__init__.py:843-913) get shortcuts; job-level chainable setters (`tag`, `at`, `to`, `until`) do not. `max_runs` is a job-level setter like `until`, so it gets none either.
- No edits to `docs/reference.rst` (autodoc already covers it — see above).
- No changes to `.at()`, `.to()`, tag handling, unit-chain properties, or `.until()`'s own semantics beyond the one specified interaction point (Out of Scope bullets 1-2 of the criteria).
- No parallel removal mechanism (e.g. a second `if self.run_count >= n: scheduler.cancel_job(self)` called from inside `Job.run()`). Constraint 1 requires reusing the existing `CancelJob` return path that `Scheduler._run_job()` already checks (schedule/__init__.py:172-175) — `Job.run()` must *return* `CancelJob`, exactly like the `.until()` overdue path does (schedule/__init__.py:695-697), and let `_run_job` do the removal.
- No storing the budget value under the public name `self.max_runs`. `max_runs` is also the chainable setter method's name; `self.max_runs = n` inside that method would shadow the class method on the instance (`job.max_runs` would resolve to the stored `int`, not the bound method), breaking the second call in Requirement 5's "last call wins" (`job.max_runs(5)` would raise `TypeError: 'int' object is not callable`). Store it as `self._max_runs`, mirroring the precedent: `.until()` stores its deadline as `self.cancel_after`, not `self.until` (schedule/__init__.py:576-642).

**Ambiguous spec sections — strict interpretation:**
- "`n` must be an integer >= 1; any other value raises `ValueError`": interpreted as `isinstance(n, int) and n >= 1`, no special-casing of `bool` (Python `bool` is an `int` subclass; the criteria does not mention booleans, so excluding them would be unrequested speculative robustness). `float`, `str`, `None`, `n < 1` all raise `ScheduleValueError`.
- "the last call wins": interpreted as plain reassignment — the second `.max_runs(n2)` call simply overwrites `self._max_runs` to `n2`; `self.run_count` (executions so far) is *not* reset, since the criteria only says the budget value is overwritten, not that the execution counter restarts. This is the literal, smallest-change reading; no evidence in the criteria calls for a counter reset.
- "the nth execution itself still runs normally": `job_func()` must actually be invoked and its return value computed on the nth run before the method returns `CancelJob` instead of that return value — mirrors the existing `.until()` "current execution time passed deadline" path (schedule/__init__.py:686-698), not the "already overdue, skip execution" path.
- "first-limit-wins" with `.until()`: both the existing `_is_overdue(self.next_run)` check and the new budget check live as independent conditions after `_schedule_next_run()` runs; whichever is true first still yields the identical `CancelJob` return, so no explicit priority/ordering logic is needed even if both happen to trigger on the same call.

**Known failure modes for this language/framework (Python):**
- Increment `run_count` *after* `job_func()` executes and *before* the budget comparison, mirroring where `self.last_run = datetime.datetime.now()` is already set (schedule/__init__.py:692) — an off-by-one here would either cancel one run too early or allow the (n+1)th run.
- The budget check must run after `_schedule_next_run()` is called (schedule/__init__.py:693), matching where the existing `.until()` overdue-check runs (schedule/__init__.py:695) — checking earlier would read a stale `next_run`/leave `next_run` unset for the `next_run`/`idle_seconds`-reflects-removal requirement (moot once `Scheduler.cancel_job()` removes the job, but `_schedule_next_run()` must still run unconditionally to match the existing method's control flow and avoid leaving `next_run` `None` if `CancelJob` is ever ignored by a caller that runs `Job.run()` directly, as several existing tests do).
- `ScheduleValueError` is a subclass of `ValueError` (schedule/__init__.py:59-62) and of `ScheduleError`; raise `ScheduleValueError` (matching `.until()`'s and `.at()`'s idiom), not a bare `ValueError`, per Constraint 3 — a bare `ValueError` would still satisfy a plain `assertRaises(ValueError, ...)` test but would break idiom consistency and any `assertRaises(ScheduleValueError, ...)` test.
- New instance attributes (`self.run_count`, `self._max_runs`) must be initialized in `Job.__init__` (schedule/__init__.py:227-255) so every job — even ones that never call `.max_runs()` — has a well-defined `self._max_runs = None` / `self.run_count = 0`, consistent with how `self.cancel_after: Optional[datetime.datetime] = None` is initialized for `.until()`.
- Attribute name collision: `self.max_runs` cannot be used for the budget-value instance state because `max_runs` is also the chainable setter method's name — `self.max_runs = n` would shadow the method on the instance, breaking every call after the first. Use `self._max_runs` instead (see Out-of-scope precedent bullet above). Confirmed no other existing `Job` attribute or method collides: `run_count` is free (only `.run()` exists, not `.run_count()`), and no existing attribute is named `_max_runs` (schedule/__init__.py, full read).

# Acceptance restatement

Verbatim copy of the generated criteria's `## Verification` block (`.devlyn/criteria.generated.md`):

```json
{
  "verification_commands": [
    { "cmd": "/opt/homebrew/bin/python3 -m pytest test_schedule.py -q", "expect_exit": 0 }
  ]
}
```
