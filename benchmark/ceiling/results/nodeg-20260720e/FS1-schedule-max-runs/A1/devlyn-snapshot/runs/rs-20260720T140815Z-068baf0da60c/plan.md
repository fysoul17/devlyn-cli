<!-- devlyn:authorized-surface -->
## Files to touch

- `schedule/__init__.py` — edit — add `Job.max_runs(n)` setter, the two run-budget instance attributes, and the `Job.run()` enforcement check that cancels the job after its `n`-th execution (Requirements 1, 2, 3, 4, 5, 6, 7).
- `test_schedule.py` — edit — add test coverage for validation, last-call-wins, chain-position independence, execution-only counting, `run_pending()`/`run_all()` enforcement, first-limit-wins vs `.until()`, `next_run`/`idle_seconds` reflecting removal, and per-job independence (Requirements 1–7; existing tests are contract per `<quality_bar>` and must keep passing unmodified).
- `docs/examples.rst` — edit — add a short usage example for `.max_runs()` next to the existing "Run a job until a certain time" / "Run a job once" sections (Requirement 8/documentation bullet).

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py", "docs/examples.rst"]}
```

## Risks

- **Attribute/method name collision (critical, must avoid).** `Job.max_runs` is a *method*. The run budget must be stored under a **different** attribute name (e.g. `self._max_runs`), never `self.max_runs = n`. Assigning `self.max_runs = n` inside the method would create an instance attribute that shadows the class method (`schedule/__init__.py:227`-`255` is where `Job.__init__` sets all other instance state, e.g. `self.cancel_after` for `.until()` at line 252, `self.tags` for `.tag()` at line 254 — every existing setter stores under a differently-named attribute, never its own method name). Getting this wrong breaks the explicit "last call wins" requirement (a second `.max_runs()` call would try to call an `int`, raising `TypeError: 'int' object is not callable`) and is the single highest-risk mistake for this task.
- **Counter must increment only on actual execution.** Increment the run-count inside `Job.run()` (`schedule/__init__.py:674`-`698`) immediately after `ret = self.job_func()` (line 691), not in `_schedule_next_run()`, `should_run`, or anywhere in the scheduler. `run_pending()` (line 89) only calls `_run_job` for jobs where `job.should_run` is true, and `run_all()` (line 103) calls `_run_job` unconditionally once per job — both funnel through `Job.run()`, so a single increment site there satisfies Requirement 4 (both entry points) without touching `Scheduler`.
- **First-limit-wins vs `.until()` — do not add a pre-run guard for max_runs.** The existing `_is_overdue` check runs both *before* `job_func()` (line 686, guards against clock drift between scheduling and execution) and *after* recomputing `next_run` (line 695, guards future scheduling). A run-count budget cannot "drift" the same way — it only changes synchronously inside `run()` — so the correct, minimal mirror is a single **post**-execution check (`self._max_runs is not None and self._run_count >= self._max_runs`) added alongside the existing post-execution `_is_overdue(self.next_run)` check (line 695-698), returning `CancelJob` on either condition. Adding a redundant pre-execution max_runs guard is unnecessary: once `run()` returns `CancelJob`, `Scheduler._run_job` (line 172-175) removes the job before any scheduler path can invoke it again, so an (n+1)-th execution is already structurally impossible. Do not add speculative extra guards — the existing `_is_overdue` pre-check at line 686 must be left untouched (regression risk called out explicitly by Requirement 5).
- **Validation error type is settled by the criteria, not open to reinterpretation.** Raise `ScheduleValueError` (already imported/defined at line 59, subclasses `ValueError`) for invalid `n`, matching the sibling pattern in `Job.until` (lines 494, 506, 514, 519, 525, 625, 639) and `Job.at`. Do not raise a bare `ValueError` directly (inconsistent with every other validator in this class) and do not add a new exception subclass (no cited failure mode requires one).
- **`bool` is a subclass of `int` — do not special-case it.** `isinstance(n, int)` is `True` for `True`/`False`; the criteria explicitly says to use plain `isinstance(n, int)` semantics and let `n >= 1` do the filtering (`True` passes as `n=1`, `False` fails as `n=0`). Do not add an `isinstance(n, bool)` exclusion — that would be unrequested behavior narrowing.
- **Do not touch `docs/reference.rst`.** It already documents `Job` via `.. autoclass:: schedule.Job` + `:members:` (`docs/reference.rst:31-32`) with no explicit per-method list, so a docstring on the new method is picked up automatically. Editing that file would be an out-of-scope, unnecessary change.
- **No changelog file exists in this repo** (confirmed: no `CHANGES*`/`HISTORY*` file at repo root). Do not create one — Out of Scope explicitly excludes unrelated additions, and no requirement asks for it.
- **Everything stays inside the existing single module.** No new files, no new `Scheduler` methods, no new public module-level shortcut function — `Job.max_runs` is a chainable `Job` instance method exactly like `.until()`/`.tag()`; the existing `Scheduler._run_job` / `cancel_job` removal path already covers every scheduler-side consequence (Requirement 6, 7), so nothing in `Scheduler` needs to change.
- **Per-job independence is already structural, not something to build.** Each `Job` has its own instance attributes and its own `Scheduler._run_job` call; as long as the budget/counter live on `self` (not on the class or the scheduler), Requirement 7's independence falls out for free — no shared/global counter, no cross-job bookkeeping.
- **Ambiguous phrase "callable anywhere in the fluent chain."** `Job.max_runs` must not depend on `self.unit`/`self.interval`/`self.at_time` being set yet (unlike `.at()`, which validates `self.unit` at line 493) — it must work whether called before `.seconds`/`.do()` or after, since it only touches the independent `_max_runs`/`_run_count` attributes. Do not add any ordering validation that isn't in the criteria.

## Acceptance restatement

## Verification

```json
{
  "verification_commands": [
    { "cmd": "python3 -m unittest test_schedule -v", "description": "Full existing unittest suite (repo's runnable test entrypoint; pytest is declared in tox.ini but not installed in this environment, and test_schedule.py is unittest.TestCase-based so unittest runs it directly) must keep passing with the new tests included." }
  ]
}
```
