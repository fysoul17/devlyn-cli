# BUILD_GATE log — run-budget feature (`Job.max_runs(n)`)

Project shape detected: Python (`pyproject.toml`, no `package.json`). `pyproject.toml` declares no `[tool.ruff]` / `[tool.mypy]` / `[tool.pytest]` sections of its own — those tool declarations live only in `tox.ini` (`testenv.deps = pytest, pytest-cov, mypy, types-pytz`), which requires `tox`.

Sandbox constraints (pre-declared, not discovered mid-run): no network access; `pytest`, `mypy`, `ruff`, `black`, `tox` are not installed — verified below. Only stdlib Python 3.9.6 is available.

## Gate 1 — Type check

Command checked for: none. Verified absence:

```
$ which mypy
mypy not found
```

`pyproject.toml` has no `[tool.mypy]` section, and the only declared mypy invocation (`python -m mypy -p schedule --install-types --non-interactive`) lives in `tox.ini`'s `[testenv]`, which requires `tox` (not installed, no network to fetch it). Per the detection rule, no type-check tool is configured to run directly in this environment. **No finding emitted** — accurately reporting "no tool configured" rather than fabricating a substitute check.

## Gate 2 — Lint

Command checked for: none. Verified absence:

```
$ which ruff black
ruff not found
black not found
```

No `[tool.ruff]` in `pyproject.toml`; `black --check .` is declared only under `tox.ini`'s `[testenv:format]`, unreachable without `tox`. **No finding emitted**, same reasoning as Gate 1.

## Gate 3 — Test suite

`test_schedule.py` is plain `unittest.TestCase` (not pytest-specific), and `pytest` is not installed, so the gate command is:

```
$ python3 -m unittest test_schedule.py -v
...
----------------------------------------------------------------------
Ran 89 tests in 0.013s

OK (skipped=41)
```

Exit code: `0`. 89 passed, 41 skipped (`'pytz unavailable'` — pre-existing environment behavior from the optional `timezone` extra not being installed; not caused by this change, confirmed via git diff against `4f513d7` touching only `schedule/__init__.py` and `test_schedule.py`, no skip-count regression). **No finding emitted.**

## Gate 4 — Spec literal verification + risk probes + authorized-surface enforcement

```
$ DEVLYN_SHARED_DIR=.claude/skills/_shared
$ python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes
[spec-verify] all 1 command(s) passed
```

Exit code: `0`. The script self-staged from `.devlyn/criteria.generated.md`'s `<!-- devlyn:verification -->` block (free-form/generated mode — no `spec.expected.json` present) and ran the one declared verification command (`python3 -m unittest test_schedule.py -v`, `expect_exit_code: 0`), which matches Gate 3's result. `risk_probes_enabled: false` for this run (per task brief) — `--include-risk-probes` ran but no `.devlyn/risk-probes.jsonl` was produced/required, consistent with risk probes not being enabled. `.devlyn/spec-verify-findings.jsonl` written empty (0 bytes) — zero findings.

**Authorized-surface enforcement**: PLAN's `<!-- devlyn:authorized-surface -->` block declares `["schedule/__init__.py", "test_schedule.py"]`. `git diff --stat 4f513d7 HEAD` shows only those two files changed (26 and 110 lines respectively). `git status --porcelain` shows four untracked entries (`.claude/`, `.devlyn/`, `AGENTS.md`, `CLAUDE.md`) — all four are also listed verbatim in `.devlyn/untracked.baseline` (captured before this run started), confirming they pre-date the run and are not artifacts created during it (and `.devlyn/` is exempt regardless). No out-of-scope file found. **No finding emitted.**

## Gate 5 — Browser validation

Skipped. No web-surface files in the diff (no `.tsx`/`.jsx`/`.vue`/`.svelte`/`page.*`/`layout.*`/`route.*`/`.css`/`.html`) — this is a plain Python library change (`schedule/__init__.py`, `test_schedule.py`).

## Verdict

**PASS** — zero CRITICAL/HIGH findings across all gates. `.devlyn/build_gate.findings.jsonl` is empty (valid: zero findings).
