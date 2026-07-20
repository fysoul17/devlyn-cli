<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `schedule/__init__.py` — `edit` — add `Job._remaining_runs` state, the `Job.max_runs(n)` chainable setter, and a decrement/cancel check in `Job.run()`; satisfies Requirements 1–3 (chainable setter, validation, self-cancel on the nth execution via existing `CancelJob`).
- `test_schedule.py` — `edit` — add tests for `.max_runs()` validation, chaining position (`every(5).seconds.max_runs(3)` and `every().max_runs(3).seconds`), self-cancel through `run_pending()` and `run_all()`, "last call wins" re-invocation, interaction with `.until()` (first-limit-wins both directions), and `next_run`/`idle_seconds` reflecting removal; existing tests (`test_cancel_job`, `test_cancel_jobs`, `test_until_time`, `test_idle_seconds`) are extended in place, not weakened, per Requirements 3–5.
- `docs/examples.rst` — `edit` — add a short `max_runs()` usage example directly after the existing "Run a job until a certain time" example (lines 219–245), satisfying the doc Constraint.

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py", "docs/examples.rst"]}
```

`docs/reference.rst` is intentionally **not** in the authorized surface: `docs/reference.rst:31-33` already does `.. autoclass:: schedule.Job` with `:members:` and `:undoc-members:`, so a docstring on the new `Job.max_runs` method is picked up automatically — editing this file would be a no-op addition against the Constraint's own wording ("picked up by docs/reference.rst's autoclass").

## 2. Risks

- **Attribute/method name collision (concrete bug risk).** The setter is named `max_runs`, per Requirement 1. Storing the budget as `self.max_runs = n` inside `def max_runs(self, n)` would shadow the bound method with an int on that instance — a second `.max_runs(...)` call would then raise `TypeError: 'int' object is not callable`, breaking Requirement 2's "last call wins." IMPLEMENT must use a distinct internal field (e.g. `self._remaining_runs`, initialized to `None` in `Job.__init__`, `schedule/__init__.py:227-255`) — never an attribute literally named `max_runs`.
- **`bool` is an `int` subclass — do not add special-casing.** Requirement 2 lists the rejected inputs explicitly ("non-int, `0`, negative, `None`, float, etc.") and never mentions `bool`. Under Python's actual type system `isinstance(True, int)` is `True` and `True >= 1`, so a plain `isinstance(n, int) and n >= 1` check accepts `True` (as `n=1`) and rejects `False` (fails `>= 1`) with zero extra code. Adding an explicit `isinstance(n, bool)` exclusion is unrequested speculative robustness (Goal-locked drift pattern 3) — refuse it; the strict literal reading of "int >= 1" is what ships.
- **Do not touch `Scheduler`.** Requirement 3 and Constraint 2 both point at reusing `Job.run()` → `CancelJob` → `Scheduler._run_job` (`schedule/__init__.py:172-175`). `Scheduler.run_pending()` (`:89-101`) and `Scheduler.run_all()` (`:103-120`) both already route every execution through `_run_job`, so they need zero changes — this is what makes the "every execution path" requirement free. Out-of-Scope explicitly bars new public `Scheduler` methods; do not add a `Scheduler`-level counter or a second cancellation path.
- **`next_run`/`idle_seconds` reflect removal "for free."** `Scheduler.get_next_run`/`next_run` (`:177-195`) and `idle_seconds` (`:197-206`) already compute from `self.jobs` (via `get_jobs`), and cancellation already removes the job from that list (`cancel_job`, `:150-160`) — identical to how `.until()` cancellation already satisfies this today (see `test_idle_seconds`, `test_schedule.py:1491-1501`, and the `.until()` cancellation assertions in `test_until_time`, `test_schedule.py:366-388`). No new code is needed for Requirement 5; do not add a bespoke `next_run` recompute.
- **Decrement timing.** The budget must count *actual invocations of `job_func`* (Requirement 3), not scheduling attempts. Decrement only after `ret = self.job_func()` succeeds inside `Job.run()` (`schedule/__init__.py:674-698`), mirroring where `self.last_run` is already set (`:692`) — not before the overdue guard at the top of `run()` (`:686-688`), which can return `CancelJob` without ever calling `job_func`.
- **First-limit-wins ordering is a non-issue, not a design decision.** Both the existing `_is_overdue(self.next_run)` check (`:695-697`) and the new remaining-runs check return `CancelJob` unconditionally when tripped; whichever `if` is written first only affects which debug log line fires, never the observable outcome. Do not add priority/ordering logic between the two — Requirement 4 is satisfied by two independent sequential checks, exactly the shape the `.until()` code already uses for its own two checks (top-of-`run()` overdue vs. post-run overdue).
- **Placement of `max_runs()`.** Insert it next to `.until()` (after `until()`, before `do()`, `schedule/__init__.py:642-644`) to match Constraint 1's "match the existing builder-pattern style" and to keep it visually adjacent to the other cancellation-configuring setter, consistent with the docs placement Constraint (example goes "alongside the existing until() example").
- **Ambiguous spec section, interpreted strictly:** "usable at any point in the fluent chain" (Requirement 1) means `max_runs()` must not depend on `self.unit`/`self.interval` being set yet — it only touches `self._remaining_runs` and returns `self`, so it is trivially chain-position-independent. No unit/interval validation belongs inside `max_runs()`.
- **Refuse:** touching `.at()`, `.to()`, tagging, timezone handling, or `HISTORY.rst` (release-numbered changelog, not mentioned in the Constraints doc list) — all explicitly Out-of-Scope or absent from the spec's documentation Constraint.

## 3. Acceptance restatement

<!-- devlyn:verification -->
## Verification

```
python3 -m unittest test_schedule
```
