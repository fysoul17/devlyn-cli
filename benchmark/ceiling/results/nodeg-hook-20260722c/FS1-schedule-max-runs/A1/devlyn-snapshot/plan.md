# Plan — `Job.max_runs(n)` run-budget feature

<!-- devlyn:authorized-surface -->
## 1. Files to touch

- `schedule/__init__.py` — edit — Req 1,2,3,4,5,6,7,8: add the `Job.max_runs(n)`
  chainable setter (with `ValueError` validation, `schedule/__init__.py:227-255`
  `Job.__init__` for attribute init, alongside the `.until()` precedent at
  `schedule/__init__.py:576-642`), plus a two-line decrement/cancel check in
  `Job.run()` (`schedule/__init__.py:674-698`) so the budget is enforced through
  the single existing `CancelJob` return path that `Scheduler._run_job`
  (`schedule/__init__.py:172-175`) already handles for both `run_pending()`
  and `run_all()` — no `Scheduler` code changes needed (Req 3, 5 fall out of
  the existing `CancelJob`/`cancel_job` removal path for free).
- `test_schedule.py` — edit — Req 1-8 verification: add
  `unittest.TestCase`-style tests (matching the existing style, e.g.
  `test_cancel_job` at `test_schedule.py:1503-1523`, `test_until_time` at
  `test_schedule.py:312-350`) covering chainability in both call orders,
  budget enforcement through both `run_pending()` and `run_all()`, the
  `.until()` first-limit-wins interaction in both orderings, per-job
  independence, last-call-wins on repeated `.max_runs()` calls, and the
  `ValueError` validation matrix (non-int, `bool`, `0`, negative, non-integral
  float).
- `docs/examples.rst` — edit — Req 9: add a `Job.max_runs` usage example
  directly alongside the existing `.until()` example (`docs/examples.rst:219-245`),
  matching that section's style (heading, code-block, one-line explanation).

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py", "docs/examples.rst"]}
```

## 2. Risks

- **Attribute/method name collision (real bug, must avoid).** The setter must
  be named `max_runs` (Req 1), but Python instance attributes shadow class
  methods of the same name. If the backing state were stored as
  `self.max_runs = n` inside `def max_runs(self, n)`, the *first* call would
  silently replace the method on that instance with an `int`, and a *second*
  `.max_runs(...)` call (Req 7 explicitly requires repeat calls to work) would
  raise `TypeError: 'int' object is not callable`. Store the budget under a
  distinctly-named attribute (e.g. `max_runs_remaining`), matching the existing
  precedent where `.until(...)` (method) sets `self.cancel_after` (attribute) —
  never the same name.
- **Bool rejection without special-casing (Req 6 + Assumption 2).** `bool` is
  a subclass of `int`, so `isinstance(n, int)` accepts `True`/`False`. The spec
  requires bool to be rejected but explicitly says not to add a dedicated
  `isinstance(n, bool)` branch, citing the (absent-but-implied) precedent that
  other integer params don't special-case bool. The correct, non-special-casing
  implementation is a strict type check — `type(n) is not int` — which excludes
  `bool` as a side effect of Python's type system rather than an explicit bool
  check. Do not write `isinstance`; do not write an explicit bool branch.
- **No new exception handling around `job_func()` (Assumption 1).** The budget
  decrement must be placed after `ret = self.job_func()` returns, in the same
  position as the existing `self.last_run` / `self._schedule_next_run()`
  bookkeeping (`schedule/__init__.py:691-693`). Do not wrap the call in
  `try`/`finally` to "guarantee" counting on exception — that is new exception
  handling the spec explicitly excludes, and it would change today's behavior
  (an exception from `job_func()` already propagates out of `run()` unmodified,
  aborting `next_run` scheduling too; that is pre-existing, out-of-scope
  behavior, not a regression to fix here).
- **Do not touch `Scheduler`.** Req 3 and 5 read as if they need `Scheduler`
  changes, but both `run_pending()` and `run_all()` already funnel through
  `Scheduler._run_job`, which already removes any job whose `.run()` returns
  `CancelJob` (`schedule/__init__.py:172-175`), and `next_run`/`idle_seconds`
  already recompute from `self.jobs` on every call. Adding a parallel check
  inside `Scheduler` would be pure-addition with no cited failure mode —
  refuse it.
- **First-limit-wins is order-independent, not order-dependent.** Req 4 does
  not require picking which check "wins" within a single `run()` call — both
  the budget check and the existing `_is_overdue(self.next_run)` check
  independently return `CancelJob`, and `_run_job` treats any `CancelJob`
  identically. Do not add priority/tie-break logic between them; do add tests
  exercising both orderings (budget expires before deadline, deadline expires
  before budget) to confirm neither check regresses the other.
- **Last-call-wins needs no extra state (Req 7).** Because the setter stores
  the *remaining* count (not a fixed total plus a separate executed-count),
  each call to `.max_runs(n)` simply overwrites `max_runs_remaining = n`. No
  accumulation logic, no "reset" branch, no separate executed-count field is
  needed or should be added — adding one would be unrequested complexity.
- **Out-of-scope refusals to hold the line on:** no new public module-level
  function/class (Constraint 2 — this is `Job`-scoped only); no change to
  `.until()`'s own deadline semantics beyond the interaction already described;
  no unrelated `Scheduler`/`Job` refactors; no new doc page (Assumption 3 — the
  docstring + one `docs/examples.rst` block is the whole doc surface).

## 3. Acceptance restatement

### Requirements

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

### Verification

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
