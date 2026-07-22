# BUILD_GATE log — round 1 (re-verification after fix for bg-001)

Repo: harbor-tools (Node.js; no `tsconfig.json`). Diff under gate: `bin/cli.js` + `tests/cli.test.js` vs base `17fce0a` (adds the `payout` subcommand per `.devlyn/criteria.generated.md`), plus the round-1 fix commit `0a08c13` (4-line shape guard in `runPayout`, right after the `JSON.parse` try/catch). Full gate set re-run from scratch, not just the bg-001 repro.

## 1. Type check — SKIPPED
No `tsconfig.json` in repo root (confirmed via `ls tsconfig.json` → not found). Not applicable.

## 2. Lint — SKIPPED
`package.json` scripts: `start`, `test`, `cli`, `lint:json`. No `lint` script. `lint:json` is a narrow existing JSON-linting utility (`scripts/lint-json.js`), unrelated to this diff's code paths. Skipped, noted.

## 3. Test suite — PASS
Command: `npm test` (== `node --test tests/`)

```
# tests 8
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

All 8 tests pass (hello ×2, version, server health/items ×3, both payout tests), exit 0. No findings.

## 4. Spec literal verification — PASS
Command: `python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes`

Output: `[spec-verify] all 5 command(s) passed` (exit 0).

All 5 `verification_commands` from `.devlyn/criteria.generated.md`'s `## Verification` block matched expected `exit_code`/`stdout_contains`: `npm test`; successful payout (`total_payout_cents`/`87363`/`9707`/`2930` present); minimum-payout clamp (`941`/`59` present); conflicting-duplicate rejection (exit 2, `conflicting_duplicate`/`e1`); missing-`events` rejection (exit 2). `.devlyn/spec-verify-findings.jsonl` is empty — 0 findings from the script.

Authorized-surface enforcement (`.devlyn/plan.md`'s `["bin/cli.js", "tests/cli.test.js"]`) also ran as part of this script and passed. Independently confirmed via `git diff --stat 17fce0a -- .` (excluding `.devlyn/`): only `bin/cli.js` (+141/-0) and `tests/cli.test.js` (+49/-1) changed; `git status --porcelain=v1 | grep '^??'` shows only pre-existing untracked harness dirs (`.claude/`, `.devlyn/`, `AGENTS.md`, `CLAUDE.md`), none of which are payout-related surface. No `scope.out-of-scope-file` findings.

`state.risk_profile.risk_probes_enabled` is `false` (demoted at PLAN time) — `.devlyn/risk-probes.jsonl` correctly not required.

## 5. Browser — SKIPPED
Diff touches only `bin/cli.js` and `tests/cli.test.js` — no web-surface files (`server/`, `web/` untouched). Not applicable.

## bg-001 re-verification — FIXED

Reproduction command:

```
$ printf '%s' 'null' > /tmp/bg-null-r1.json && node bin/cli.js payout --input /tmp/bg-null-r1.json; echo "exit:$?"
exit:2
stdout: (empty)
stderr: {"error":"invalid_json"}
```

The fix (commit `0a08c13`, `bin/cli.js` lines 66-69) adds `if (ledger === null || typeof ledger !== 'object' || Array.isArray(ledger)) { payoutError('invalid_json'); return; }` immediately after the `JSON.parse` try/catch and before the `hasOwnProperty` call that previously threw. Top-level JSON `null` now exits 2 with a single JSON error object on stderr and nothing on stdout, matching Requirement 16 (`criteria.generated.md`). No crash. **bg-001 is fixed — no finding recorded.**

## Additional pass — other uncaught-exception-shaped gaps in the payout validation path

Targeted reproduction of adjacent shapes that could plausibly bypass the new guard or hit an unguarded property access, using the same `payout --input <path>` entry point (in-scope surface only; `data/payout-rules.json` not touched or validated, per Out of Scope):

| Input | Result | Crash? |
|---|---|---|
| `--input` (no value) | `{"error":"missing_input"}`, exit 2 | No |
| `--input .` (directory) | `{"error":"input_unreadable"}`, exit 2 | No |
| `--input --foo` (flag-shaped value) | `{"error":"missing_input"}`, exit 2 | No |
| top-level `[1,2,3]` (JSON array) | `{"error":"invalid_json"}`, exit 2 | No |
| `{"events":[null]}` (null event entry) | `{"error":"invalid_event"}`, exit 2 | No |
| `amount_cents` beyond `Number.MAX_SAFE_INTEGER` | succeeds, exit 0, imprecise totals (float precision, not a crash) | No |

No new uncaught-exception-shaped gap reproduced. The `Object.prototype.hasOwnProperty.call`-style access at the per-event validation site is already preceded by a `typeof event !== 'object' || Array.isArray(event)` guard, covered the same way the new top-level guard now covers `ledger`. The float-precision case is a pre-existing, spec-silent behavior (Assumptions explicitly rule out adding epsilon-correction) — not a crash, not reproducing any cited failure mode, so no finding per the additional-check instruction to only record what's concretely reproducible.

## Verdict

**PASS** — 0 CRITICAL/HIGH findings. Test suite green (8/8), spec literal verification green (5/5 commands + authorized-surface enforcement), bg-001 confirmed fixed at its exact repro command, and a targeted adjacent-shape sweep found no further uncaught-exception-shaped gaps in the touched surface.
