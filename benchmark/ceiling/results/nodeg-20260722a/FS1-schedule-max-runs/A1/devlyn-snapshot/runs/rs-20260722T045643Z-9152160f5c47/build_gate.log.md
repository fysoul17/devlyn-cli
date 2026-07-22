# BUILD_GATE log — run rs-20260722T045643Z-9152160f5c47

Base sha `4f513d7ae2598e737ef8dcd82cfed0d44ebc1be8`, IMPLEMENT commit `34f399f1b405ad0203d6a6a58d7febd155a4a204`.
Diff scope (matches `.devlyn/plan.md` authorized surface exactly): `schedule/__init__.py`, `test_schedule.py`, `docs/examples.rst`.

## Detection

`pyproject.toml` present, no `[tool.ruff]`/`[tool.mypy]`/`[tool.pytest.ini_options]` sections of its own. `tox.ini` + `.github/workflows/*.yml` are the actual CI contract: 4 jobs — `test` (`tox` → pytest+coverage, then mypy), `docs` (`tox -e docs` → sphinx `-W`), `formatting` (`tox -e format` → `black --check .` with `requirements-dev.txt`-pinned `black==20.8b1`), `setuppy` (`tox -e setuppy` → `setup.py check --strict --metadata --restructuredtext`). Environment initially had no pytest/mypy/black/sphinx; `pip install` succeeded quickly (network available), so all four CI environments' underlying commands were run directly (not via `tox` itself, since multi-Python-version matrix isn't relevant to a single-interpreter gate check) rather than approximated via stdlib-only fallback.

## Gates run

1. **Type check — `python3 -m mypy -p schedule --install-types --non-interactive`** (mirrors `tox.ini` `[testenv]`)
   → `Success: no issues found in 1 source file`. PASS, 0 findings.

2. **Lint/format — `python3 -m black --check .`** using CI-pinned `black==20.8b1` (installed via `pip install -r requirements-dev.txt`, mirrors `tox.ini` `[testenv:format]` / CI job `formatting`)
   → `8 files would be reformatted, 4 files would be left unchanged.` Of the 8, 7 are pre-existing files under `.claude/skills/_shared/` — untracked pipeline-harness tooling, not part of the `schedule` package or this diff's authorized surface, and not covered by this repo's own CI (`.claude/` isn't a tracked path) — not reported as findings. The 8th, **`test_schedule.py`**, is in this diff's authorized surface and the two long-form `.do(\n    mock_job\n)` calls added by `test_max_runs_and_until_cancel_at_the_first_limit` collapse to one line under black. **2 findings (bg-001, bg-002), severity MEDIUM** — see `.devlyn/build_gate.findings.jsonl`.
   Note: also tried black's latest release (25.11.0) first, which additionally flagged pre-existing untouched `docs/conf.py` — a version-drift false positive on a file outside the diff, dropped once the CI-pinned version was installed and used for the reported findings above.

3. **Test suite:**
   - `python3 -m pytest test_schedule.py schedule -v --cov schedule --cov-report term-missing` (mirrors `tox.ini` `[testenv]`) → `46 passed, 41 skipped in 0.41s`, coverage 94% (`schedule/__init__.py` 396 stmts, 23 miss — pre-existing gaps at 505-512/677/768-770/779/812-841, none in the new `max_runs` code paths). PASS.
   - `python3 -m unittest test_schedule -v` (the literal command declared in `.devlyn/criteria.generated.md` / `plan.md`'s `## Verification` block) → `Ran 87 tests in 0.045s — OK`. PASS. (46 run + 41 `pytz unavailable` skips under pytest == 87 total under unittest, consistent — pytest's default skip reporting differs from unittest's, same underlying suite.)
   0 test failures. 0 findings.

4. **Spec literal verification + risk probes — `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes`**
   → `[spec-verify] all 1 command(s) passed` (exit 0). Authorized-surface check against `.devlyn/plan.md`'s `authorized_surface` (`schedule/__init__.py`, `test_schedule.py`, `docs/examples.rst`) passed silently (no `scope.out-of-scope-file` / `scope.authorized-surface-malformed` emitted); confirmed independently via `git status` — untracked set unchanged from baseline (`.claude/`, `.devlyn/`, `AGENTS.md`, `CLAUDE.md`, all pre-existing/exempt), `git diff --stat` clean (IMPLEMENT's commit is the full diff). See `.devlyn/spec-verify.results.json` for the raw per-command result. 0 findings.

5. **Docs build — `sphinx-build -W -b html -d <tmp>/doctrees . <tmp>/html`** (mirrors `tox.ini` `[testenv:docs]`, relevant since `docs/examples.rst` is in the diff)
   → `build succeeded.` No warnings-as-errors triggered by the new `.max_runs()` section. PASS. 0 findings.

6. **Package metadata — `python3 setup.py check --strict --metadata --restructuredtext`** (mirrors `tox.ini` `[testenv:setuppy]`)
   → `running check`, exit 0. PASS. 0 findings.

7. **Browser** — skipped per detection: no `.tsx`/`.jsx`/`.vue`/`.svelte`/`page.*`/`layout.*`/`route.*`/`.css`/`.html` in this diff (pure Python library + docs change).

## Tooling-artifact-leak check

`git status` shows no new untracked files beyond the run's own `.devlyn/`/`.claude/` (pre-existing) — no coverage HTML or other reporter artifacts leaked into the working tree. 0 findings.

## Verdict

**PASS** — 0 CRITICAL, 0 HIGH findings. 2 MEDIUM findings (bg-001, bg-002: `test_schedule.py` black formatting) are real and diff-introduced — they would fail CI's `formatting` job as-is and should be fixed (`black test_schedule.py`) before merge — but per this gate's stated PASS/FAIL rule ("PASS if zero CRITICAL/HIGH findings; FAIL otherwise") they do not block this gate.
