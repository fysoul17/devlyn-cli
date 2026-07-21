# Plan — run-budget feature (`Job.max_runs(n)`)

<!-- devlyn:authorized-surface -->
## Files to touch

- `schedule/__init__.py` — `edit`. Add per-job run-budget state to `Job.__init__` (mirrors `self.cancel_after`/`self.tags` init pattern, `schedule/__init__.py:252-254`), add the chainable `Job.max_runs(n)` setter next to `Job.until()` (`schedule/__init__.py:576-642`), add a private `_is_run_budget_exhausted()` predicate mirroring `_is_overdue()` (`schedule/__init__.py:819-820`), and wire the post-execution check into `Job.run()` (`schedule/__init__.py:674-698`) so budget exhaustion returns `CancelJob` exactly like `.until()` does today — reusing the existing `Scheduler._run_job` cancellation flow (`schedule/__init__.py:172-175`) with no scheduler-side changes. Satisfies Requirements 1-8 (chainable setter, execution counting, both dispatch paths, until()-interaction, next_run/idle_seconds fallout, validation, overwrite semantics, per-job isolation) and Requirement 9's docstring (autodoc'd via `:members:` on `schedule.Job`, confirmed at `docs/reference.rst:31-33` — no separate doc-page edit needed).
- `test_schedule.py` — `edit`. Add new test methods to `SchedulerTests` covering: chainability at both chain positions, validation errors, execution-count-based cancellation via `run_all()` (style matches `test_cancel_job`, `test_schedule.py:1503-1523`), last-call-wins overwrite, first-limit-wins interaction with `.until()` in both directions (style matches `test_until_time`, `test_schedule.py:312-338`), per-job independence with two differently-budgeted jobs, and `Scheduler.next_run`/`idle_seconds` reflecting removal after exhaustion.

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py"]}
```

## Risks

- **Attribute/method name collision (real bug, not speculative).** The setter is named `max_runs`; storing state on `self.max_runs` would shadow the bound method on the instance after the first call, breaking any second call (`int` is not callable). Codebase precedent (`tag()`→`self.tags`, `to()`→`self.latest`, `until()`→`self.cancel_after`) always uses a distinct noun for stored state. Plan uses `self.run_limit` (the budget) and `self.run_count` (executions so far) — public, non-underscored, consistent with the class's existing public-attribute convention. Do not name either `max_runs`.
- **Out-of-scope expansion to refuse**: no changes to `docs/examples.rst`, `docs/reference.rst`, `HISTORY.rst`/`docs/changelog.rst`, or `README.rst` — the spec explicitly says the docstring alone suffices (Requirement 9), and none of these are in Requirements. Do not add a changelog/history entry "for completeness."
- **Do not touch `.until()`'s own validation, string-parsing, timezone, or `_is_overdue` semantics** — only add a sibling predicate and OR it into the single post-run check in `Job.run()`. `_is_overdue` itself stays untouched (Constraint: "Do not change `.until()`'s own ... behavior").
- **No scheduler-side bookkeeping.** `Scheduler.run_pending`/`run_all`/`_run_job` (`schedule/__init__.py:89-120, 172-175`) already funnel every dispatch path through `Job.run()` → `CancelJob` → `cancel_job()`. Do not add a parallel counter or cancellation check in `Scheduler`; that would violate Constraint 2 (integrate via `Job.run()`, not parallel scheduler-side bookkeeping) and is redundant since both `run_pending()` and `run_all()` already call `_run_job`.
- **Pre-run vs post-run check placement.** `.until()` has both a pre-run check (deadline already passed before running) and a post-run check (deadline passed after computing next run). The run-budget only ever needs the post-run check — a job already at its budget is removed from `self.jobs` before it could be dispatched again, so there is no "already exhausted" pre-run state to detect. Adding a pre-run budget check would be dead code (unreachable: the job can't still be in `scheduler.jobs` after exhaustion). Do not add one.
- **Validation must raise builtin `ValueError`, not `ScheduleValueError`.** This is a deliberate, literal divergence from the codebase's usual setter-validation convention (Requirement 6) — do not "fix" it to `ScheduleValueError` for consistency; that would contradict the explicit spec text.
- **Boolean/float inputs to `max_runs(n)`**: spec says "n must be an integer >= 1; any other value raises ValueError." Plan implements the literal check (`isinstance(n, int) and n >= 1`, else `ValueError`) without a special-case bool exclusion (`bool` is an `int` subclass in Python, and the spec does not call out booleans) — avoids inventing an unrequested edge case per the no-overengineering principle. Not covered by a dedicated test since it is not a distinguished requirement.
- **`repeat()` decorator**: out of scope per spec; it already works unchanged because `max_runs()` is chainable and returns the `Job` instance passed into `repeat()`. No test added for `repeat()` × `max_runs()` combination — out of scope, would be speculative coverage.
- **Test determinism**: reuse `run_all()` (unconditional dispatch, no time mocking needed) for pure execution-count tests, matching `test_cancel_job`'s existing style — avoids introducing new time-mocking machinery for cases that don't need it. Use `mock_datetime` only for the `.until()`-interaction test, matching `test_until_time`'s existing style.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md`:

```json
{
  "verification_commands": [
    { "cmd": "python3 -m unittest test_schedule.py -v", "expect_exit_code": 0 }
  ]
}
```

Additional acceptance implied by Requirements (not separately mechanically checked beyond the command above, but must hold for the command to pass once new tests are added): the full existing suite (81 passing / 41 skipped for missing pytz) keeps passing, and new tests in `test_schedule.py` cover chainable-anywhere-in-chain usage, execution-count-based auto-cancellation (nth run executes, n+1th never happens), both `run_pending()`/`run_all()` dispatch paths, first-limit-wins interaction with `.until()`, `ValueError` on invalid `n`, last-call-wins overwrite, per-job independence, and `next_run`/`idle_seconds` reflecting removal.
