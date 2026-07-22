<!-- devlyn:authorized-surface -->
## Files to touch

- `schedule/__init__.py` — edit — Requirements 1–8 require the public fluent setter, per-instance state, validation in the existing exception family, and `Job.run()` to return `CancelJob` after the final actual callback execution; the existing central cancellation path is `Scheduler._run_job()` at `schedule/__init__.py:172-175`, while deadline checks and rescheduling are in `Job.run()` at `schedule/__init__.py:635-658`.
- `test_schedule.py` — edit — Requirements 1–8 require coverage for both fluent positions, validation/MRO, repeated configuration, per-job isolation, `run_pending()`, `run_all()`, deadline interaction, and removal-derived next-run/idle state, using the existing `make_mock_job` and `mock_datetime` helpers at `test_schedule.py:33-93` and the cancellation/deadline patterns at `test_schedule.py:312-388` and `test_schedule.py:1503-1535`.
- `docs/examples.rst` — edit — Requirement 1 and the documentation constraint require a runnable, titled `.max_runs()` worked example matching the `.until()` section at `docs/examples.rst:205-239`; `docs/reference.rst` is intentionally untouched because `schedule.Job` members are autodocumented there at `docs/reference.rst:31-33`.

```json
{"authorized_surface": ["schedule/__init__.py", "test_schedule.py", "docs/examples.rst"]}
```

## Risks

- Preserve the single cancellation mechanism: `run_pending()` and `run_all()` both route jobs through `_run_job()` (`schedule/__init__.py:99-101`, `118-120`), whose `CancelJob` result triggers `cancel_job()`. Do not add a parallel removal path or special-case either runner.
- The budget must advance only after `job_func()` is invoked, then after `_schedule_next_run()` in the existing `Job.run()` sequence (`schedule/__init__.py:648-651`). Preserve the pre-run deadline guard so an already-expired `.until()` deadline runs no callback, and keep the post-reschedule deadline test ahead of—or otherwise semantically equal to—the budget exhaustion result, so the first reached limit cancels the job and existing `.until()` behavior remains unchanged.
- Add distinct internal fields for configured limit and completed executions; assigning `self.max_runs` would shadow the method and violate the criteria. Repeated configuration replaces only the limit, not the completed-execution counter. State belongs to each `Job.__init__` instance (`schedule/__init__.py:227-255`), never the scheduler or module.
- Reconcile validation through `ScheduleValueError`, whose current hierarchy is only `ScheduleError -> Exception` (`schedule/__init__.py:53-68`), so max-runs validation remains catchable as `ScheduleValueError` and is also a `ValueError`. Reject values that are not a positive integer (including booleans, which are not meaningful run budgets) without a disconnected bare `ValueError`.
- Do not manually edit `docs/reference.rst`, change `CancelJob`/`Scheduler.cancel_job`, add reset/introspection APIs, alter timezone logic, or weaken existing deadline tests. Test removal through the public module-level `next_run()` and `idle_seconds()` shortcuts, which delegate to scheduler state at `schedule/__init__.py:900-911`.

## Acceptance restatement

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
