# BUILD_GATE log — Round 2 (re-verification)

Date: 2026-07-18
Working directory: `/Users/aipalm/.local/share/nx01/w/r19d8684a2e44/ff10888c89791/A1/repo`

## Context

Round 0 found 1 CRITICAL finding (`BGATE-0001`): `.devlyn/criteria.generated.md`'s
verification JSON used the key `expect_exit` instead of the schema's canonical
`exit_code`, causing `spec-verify-check.py` to silently default every command's
expected exit code to 0 — flagging `node bin/cli.js version --format yaml`
(which correctly exits 1) as a false-positive mismatch. That was a
criteria-authoring bug, not an implementation bug.

The orchestrator fixed `.devlyn/criteria.generated.md` (renamed `expect_exit` →
`exit_code` for all 4 `verification_commands`) and updated
`state.source.criteria_sha256` accordingly. No code in `bin/cli.js` or
`tests/cli.test.js` changed since round 0.

This round re-runs every gate from a clean findings file to confirm the fix
resolved the CRITICAL and that nothing regressed.

## Detection

Node project (`package.json`, no `tsconfig.json`) → type-check skipped.

## Gate 1 — Type check

N/A — skipped (no `tsconfig.json`).

## Gate 2 — Lint (`npm run lint:json`)

**FAIL**, same as round 0: `Error: Cannot find module
'.../scripts/lint-json.js'` (`MODULE_NOT_FOUND`). Confirmed
`scripts/lint-json.js` has never existed in this repo (pre-existing defect,
not in the authorized_surface `["bin/cli.js", "tests/cli.test.js"]`).
Recorded as **MEDIUM**, non-blocking — `BGATE-LINT-0001` (unchanged from
round 0).

## Gate 3 — Test suite (`npm test`)

**PASS.** All 8 tests pass (`node --test tests/`):

- `hello default`
- `hello with --name`
- `version prints package version`
- `version prints JSON when requested`
- `version rejects unsupported --format value`
- `GET /health returns ok`
- `GET /items returns list`
- `GET /items/:id returns 404 for missing`

No test failures. 0 findings.

## Gate 4 — Spec literal verification + risk probes

Command run:

```
python3 "/Users/aipalm/.local/share/nx01/w/r19d8684a2e44/ff10888c89791/A1/repo/.claude/skills/_shared/spec-verify-check.py" --include-risk-probes
```

Output: `[spec-verify] all 4 command(s) passed`, exit 0.

| # | Command | Expected exit | Actual exit | Result |
|---|---|---|---|---|
| 0 | `node bin/cli.js version` | 0 | 0 | pass |
| 1 | `node bin/cli.js version --format json` | 0 | 0 | pass — stdout `{"version":"0.1.0"}` |
| 2 | `node bin/cli.js version --format yaml` | 1 | 1 | **pass** — stdout `--format must be json`, exits 1 (was the round-0 false positive; now correctly expected) |
| 3 | `npm test` | 0 | 0 | pass |

`.devlyn/spec-verify-findings.jsonl` is empty (0 lines) — zero findings this
round, confirming the criteria-file fix (`expect_exit` → `exit_code`)
resolved `BGATE-0001`.

**Authorized-surface enforcement**: `spec-verify-check.py` runs
`authorized_surface_findings()` automatically in `build_gate` phase whenever
`state.base_ref.sha` is present (it is: `e5a20d983f63e62ad264174c025fad97769e9fc5`).
It contributes to the same (empty) findings file, so it produced **zero
violations**. Cross-checked directly: `git diff e5a20d9 HEAD --stat` shows
only `bin/cli.js` (+20/-2) and `tests/cli.test.js` (+13) changed — exactly
`.devlyn/plan.md`'s declared `authorized_surface`
(`["bin/cli.js", "tests/cli.test.js"]`), no other file touched.

`.devlyn/criteria.generated.md` sha256 (`d912e26af43778e5f2720caa958285aaf170c9d5ef4a8de05a3266733a9ec424`)
matches `state.source.criteria_sha256` — confirms the orchestrator's fix is
the version actually exercised by this round.

## Gate 5 — Browser

N/A — skipped (no matching file types in the diff).

## Verdict

**PASS** — 0 CRITICAL, 0 HIGH findings. 1 non-blocking MEDIUM finding
(`BGATE-LINT-0001`, pre-existing, outside authorized_surface, unchanged from
round 0).

The criteria-file fix resolved the round-0 CRITICAL false positive
(`BGATE-0001`) without any change to `bin/cli.js` or `tests/cli.test.js`,
confirming the round-0 root cause diagnosis (criteria-authoring bug, not an
implementation bug) was correct.
