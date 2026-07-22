# BUILD_GATE log

Run: rs-20260722T035950Z-c3acbf542470
Timestamp: 2026-07-22T04:26:36Z
base_ref: cbd12daedd7f2d22c62110faf097f12797e7dda6
HEAD (implement_passed_sha): 09ae5061860820d78a62aa53d5d2773c81a9a5f4

## Project shape detection

Node.js project (`package.json` present). No `tsconfig.json` -> type-check gate skipped.
No ESLint config and no `lint` script (only `lint:json`, unrelated to this diff's file types) -> lint gate skipped.
Diff (`git diff --name-only cbd12da...HEAD`): `bin/cli.js`, `tests/cli.test.js` only -> no `*.tsx/*.jsx/*.vue/*.svelte/page.*/layout.*/route.*/*.css/*.html` touched -> Browser gate skipped.

## Gate 1: Type check — SKIPPED (no tsconfig.json)

## Gate 2: Lint — SKIPPED (no eslint/lint script for JS)

## Gate 3: Test suite — `npm test` (`node --test tests/`)

```
TAP version 13
# Subtest: hello default
ok 1 - hello default
# Subtest: hello with --name
ok 2 - hello with --name
# Subtest: version prints package version
ok 3 - version prints package version
# Subtest: fulfill-wave accepts an allocation and leaves the input file unchanged
ok 4 - fulfill-wave accepts an allocation and leaves the input file unchanged
# Subtest: fulfill-wave rejects an order and restores tentative stock deductions
ok 5 - fulfill-wave rejects an order and restores tentative stock deductions
# Subtest: GET /health returns ok
ok 6 - GET /health returns ok
# Subtest: GET /items returns list
ok 7 - GET /items returns list
# Subtest: GET /items/:id returns 404 for missing
ok 8 - GET /items/:id returns 404 for missing
1..8
# tests 8
# pass 8
# fail 0
# cancelled 0
# skipped 0
```

Result: 8/8 passed, 0 failed. Existing `hello`/`version`/server tests untouched and green; both new `fulfill-wave` tests (accepted-allocation, rejected all-or-nothing) pass.

## Gate 4: Spec literal verification + risk probes

Command: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes`
(`state.risk_profile.risk_probes_enabled = false`, auto-demoted at PHASE 0 because the PLAN-declared surface was only 2 files — `.devlyn/risk-probes.jsonl` correctly absent and not required.)

```
[spec-verify] all 4 command(s) passed
```
Exit code: 0.

The same invocation also runs the forbidden-patterns check (`spec.expected.json`/source-carrier `forbidden_patterns`) and the PLAN authorized-surface scope check (`.devlyn/plan.md`'s `<!-- devlyn:authorized-surface -->` block: `{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}`) against this run's diff + untracked delta. Output findings file `.devlyn/spec-verify-findings.jsonl` is present and empty (0 lines) -> no CRITICAL findings from spec-verify, forbidden-patterns, or scope checks. Confirmed independently: `git diff --name-only` shows only `bin/cli.js` and `tests/cli.test.js` (both inside the declared surface), and `git status --porcelain --untracked-files=all` shows no untracked files outside the pipeline's own `.devlyn/`/`.claude/`/`AGENTS.md`/`CLAUDE.md` (pipeline-created, exempt).

## Gate 5: Browser — SKIPPED (no UI/page/route/style files in diff)

## Verdict

**PASS** — zero CRITICAL/HIGH findings across all gates run.
