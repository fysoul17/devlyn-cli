# BUILD_GATE log

- run_id: rs-20260720T111620Z-d55e9412e513
- base_ref: master @ 17fce0afa9c75bad4fee0d4b139240fbde99e41c
- executed_at: 2026-07-20T11:30:37Z
- diff surface: `bin/cli.js`, `tests/cli.test.js` (matches `.devlyn/plan.md` authorized_surface exactly)

## Detection

- Node.js project (`package.json` present).
- No `tsconfig.json` -> type-check gate skipped.
- No ESLint config and no `lint` script (`lint:json` only targets JSON files) -> lint gate skipped, nothing configured for JS.
- `npm test` runs `node --test tests/`.

## 1. Type check -- SKIPPED

No TypeScript in this project.

## 2. Lint -- SKIPPED

No lint tool configured for JS in this repo (`package.json` scripts: `cli`, `start`, `test`, `lint:json` only; `lint:json` is JSON-only and out of scope for a JS gate).

## 3. Test suite -- PASS

Command: `npm test` (`node --test tests/`)
Exit code: 0

```
TAP version 13
# {"error":"invalid_event"}
ok 1 - hello default
ok 2 - hello with --name
ok 3 - version prints package version
ok 4 - payout calculates merchant balances and ignores identical duplicates
ok 5 - payout emits a JSON error for invalid events
ok 6 - GET /health returns ok
ok 7 - GET /items returns list
ok 8 - GET /items/:id returns 404 for missing
1..8
# tests 8
# suites 0
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 147.804708
```

(The `# {"error":"invalid_event"}` line is expected stderr output captured by test 5, which asserts the CLI's JSON-error-on-stderr contract for an invalid event.)

0 failing tests -> 0 `correctness.test-failure` findings.

## 4. Spec literal verification + risk probes -- PASS

Command: `python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes`
Exit code: 0
Stderr: `[spec-verify] all 4 command(s) passed`

Self-staged from `.devlyn/pipeline.state.json:source.criteria_path` = `.devlyn/criteria.generated.md`. All 4 `verification_commands` from the inline `<!-- devlyn:verification -->` block passed:

| # | command | expected exit | actual exit | stdout_contains | result |
|---|---|---|---|---|---|
| 0 | `npm test` | 0 | 0 | -- | PASS |
| 1 | payout success-path fixture (fee/reserve/payout math + duplicate-dedupe cross-check against `data/payout-rules.json`) | 0 | 0 | `SUCCESS_CHECK_OK` | PASS |
| 2 | payout conflicting-duplicate fixture (same id, differing payload) | 0 | 0 | `CONFLICT_CHECK_OK` | PASS |
| 3 | payout invalid-JSON input fixture | 0 | 0 | `INVALID_JSON_CHECK_OK` | PASS |

Full results: `.devlyn/spec-verify.results.json`. Findings stream: `.devlyn/spec-verify-findings.jsonl` (0 lines -- empty, valid).

**Authorized-surface enforcement** (`.devlyn/plan.md`'s `<!-- devlyn:authorized-surface -->` block: `{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}`): manually cross-checked against `git diff --stat` (only `bin/cli.js`, `tests/cli.test.js` changed) and `git status --porcelain` diffed against `.devlyn/untracked.baseline` (no new untracked paths outside `.devlyn/` appeared during this run; `.devlyn/` is exempt per the gate contract). No `scope.out-of-scope-file` findings.

**Risk probes**: `state.risk_profile.risk_probes_enabled` is `false` for this run (demoted at PLAN time -- authorized surface is only 2 plain paths, see `.devlyn/pipeline.state.json:risk_profile.reasons`). `.devlyn/risk-probes.jsonl` is absent, as expected; not treated as a defect.

## 5. Browser -- SKIPPED

`git diff --stat 17fce0afa9c75bad4fee0d4b139240fbde99e41c..HEAD` touches only `bin/cli.js` and `tests/cli.test.js` -- no `*.tsx`/`*.jsx`/`*.vue`/`*.svelte`/`page.*`/`layout.*`/`route.*`/`*.css`/`*.html` files.

## Reporter-artifact scan

`.gitignore` contains only `node_modules`, `dist`, `*.log` -- `.devlyn/` is not covered, so `git status` shows every file this gate (and prior phases) wrote under `.devlyn/`, including this run's own `spec-verify.json`, `spec-verify.results.json`, `spec-verify-findings.jsonl`, `build_gate.findings.jsonl`, `build_gate.log.md`. Flagged as `bg-001` (`scope.tooling-artifact-leak`, MEDIUM) in `.devlyn/build_gate.findings.jsonl`.

## Verdict

**PASS** -- 0 CRITICAL, 0 HIGH, 1 MEDIUM (`bg-001`), 0 LOW.
