# BUILD_GATE log

Diff under gate: `git diff 4f513d7ae2598e737ef8dcd82cfed0d44ebc1be8 HEAD` (commit `7a37cf7`) — `docs/examples.rst`, `schedule/__init__.py`, `test_schedule.py`.

Correction to <detection>: the sandbox does in fact have network access. `pip3 install --quiet mypy types-pytz` and `pip3 install --quiet black` both succeeded (exit 0), so gates 1 and 2 ran for real instead of being skipped.

## 1. Type check — `python3 -m mypy -p schedule`

Ran (mypy 1.19.1, installed this run via pip3 — no pre-existing installation).

```
Success: no issues found in 1 source file
```

Exit 0. No findings.

## 2. Lint — `python3 -m black --check .`

Ran (black 25.11.0, installed this run via pip3 — no pre-existing installation).

Repo-wide `--check .` reports 7 files needing reformatting, but all 7 are pre-existing files this diff never touched (`.claude/skills/_shared/collect-codex-findings.py`, `.claude/skills/_shared/archive_run.py`, `docs/conf.py`, `.claude/skills/_shared/finish-gate.py`, `.claude/skills/_shared/verify-merge-findings.py`, `.claude/skills/_shared/state-phase-write.py`, `.claude/skills/_shared/spec-verify-check.py`). Per `<quality_bar>`, pre-existing formatting drift outside this diff is not a finding for this diff.

Scoped re-check on the two changed Python files:

```
$ python3 -m black --check schedule/__init__.py test_schedule.py
All done! (2 files would be left unchanged)
```

Exit 0. No findings for this diff's changed files.

## 3. Test suite — `python3 -m unittest test_schedule -v`

```
Ran 87 tests in 0.012s

OK (skipped=41)
```

Exit 0. All non-skipped tests pass, including all 6 new `test_max_runs_*` tests. The 41 skips are the expected `pytz unavailable` skips (pre-existing, unrelated to this diff). No findings.

## 4. Spec literal verification + risk probes — `spec-verify-check.py --include-risk-probes`

```
$ python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes
[spec-verify] all 1 command(s) passed
```

Exit 0. The single declared verification command (`python3 -m unittest test_schedule -v`) passed. Diff stat (`docs/examples.rst`, `schedule/__init__.py`, `test_schedule.py`) matches `.devlyn/plan.md`'s `authorized_surface` exactly. Untracked files (`.claude/`, `AGENTS.md`, `CLAUDE.md`) match `.devlyn/untracked.baseline` with no additions (`.devlyn/` itself exempt). No findings.

## 5. Browser gate

Not applicable — diff touches no `*.tsx/*.jsx/*.vue/*.svelte/page.*/layout.*/route.*/*.css/*.html`.

## Reporter-artifact leak check

`git diff --stat` shows only the 3 authorized source files — no coverage HTML or other tooling artifacts leaked into the diff.

## Summary

0 CRITICAL / 0 HIGH / 0 MEDIUM findings. `.devlyn/build_gate.findings.jsonl` is empty (0 lines).
