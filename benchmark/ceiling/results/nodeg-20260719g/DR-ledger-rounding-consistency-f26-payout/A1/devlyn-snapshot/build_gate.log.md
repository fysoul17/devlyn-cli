# BUILD_GATE log

run_id: rs-20260719T113259Z-2eafd899612b
base_ref.sha: 17fce0afa9c75bad4fee0d4b139240fbde99e41c
diff scope (git diff --stat vs base_ref.sha): `bin/cli.js` (+151), `tests/cli.test.js` (+94) — matches PLAN's `authorized_surface`.

## 1. Type check — SKIPPED

No `tsconfig.json` in repo root. Gate does not apply.

## 2. Lint — SKIPPED

`package.json` `devDependencies` is empty (`{}`); no eslint/similar linter configured. The `lint:json` script (`node scripts/lint-json.js`) is a custom JSON-schema validator, not a general-purpose code linter, so it does not count as "eslint/similar" per the gate contract. Gate does not apply (not invented).

## 3. Test suite — PASS

Command: `node --test tests/`

```
1..9
# tests 9
# suites 0
# pass 9
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 292.147542
```

All 9 tests passed, including the 3 new `payout` tests in `tests/cli.test.js`:
- `payout calculates merchant totals` — ok
- `payout rejects invalid events` — ok
- `payout rejects conflicting duplicate ids` — ok

Pre-existing `hello`/`version` CLI tests (3) and `server.test.js` tests (3) unaffected.

## 4. Spec literal verification + risk probes — PASS

Command: `python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes`

```
[spec-verify] all 3 command(s) passed
```

Exit code: 0. Detail (`.devlyn/spec-verify.results.json`):

| # | cmd | expected_exit | actual_exit | pass |
|---|---|---|---|---|
| 0 | `node --test tests/` | 0 | 0 | true |
| 1 | `node .devlyn/probes/P1.js` | 0 (stdout contains `P1 PASS`) | 0 | true |
| 2 | `node .devlyn/probes/P2.js` | 0 (stdout contains `P2 PASS`) | 0 | true |

- Source: generated-criteria mode, self-staged from `pipeline.state.json:source.criteria_path` (`.devlyn/criteria.generated.md`).
- Risk probes (`.devlyn/risk-probes.jsonl`, required since `state.risk_profile.risk_probes_enabled == true`): P1 (valid-payout shape contract) and P2 (conflicting-duplicate idempotency/error contract) both passed.
- `.devlyn/spec-verify-findings.jsonl`: 0 lines — no findings, no `scope.out-of-scope-file` violations. `authorized_surface` (`["bin/cli.js", "tests/cli.test.js"]`) enforced against the diff + untracked delta since `base_ref.sha`; no violation (`.devlyn/` is exempt and is the only other untracked delta).

## 5. Browser — SKIPPED

Diff touches only `bin/cli.js` and `tests/cli.test.js` — no `*.tsx`/`*.jsx`/`*.vue`/`*.svelte`/`page.*`/`layout.*`/`route.*`/`*.css`/`*.html`. Gate does not apply.

## Tooling-artifact-leak check

`git diff --stat 17fce0afa9c75bad4fee0d4b139240fbde99e41c` shows only `bin/cli.js` and `tests/cli.test.js` — no `.devlyn/` reporter artifacts leaked into the tracked diff (untracked `.devlyn/` files do not appear in `diff --stat`). No `scope.tooling-artifact-leak` finding.

## Verdict

**PASS** — zero CRITICAL/HIGH findings across all gates. `.devlyn/build_gate.findings.jsonl` is empty.
