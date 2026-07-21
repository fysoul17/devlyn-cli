# BUILD_GATE log

Repo: `harbor-tools` / `bench-cli` (Node.js CLI). Diff under gate: `bin/cli.js`, `tests/cli.test.js` (commit `c3ded85`, "chore(pipeline): implement" — 288 insertions, 0 deletions).

## Detection

- `package.json` present → Node project shape.
- No `tsconfig.json` in repo → **type check skipped**.
- No eslint config file in repo → **lint skipped**.

## Gate 1 — Type check

Skipped (no `tsconfig.json`).

## Gate 2 — Lint

Skipped (no eslint config).

## Gate 3 — Test suite

Command: `node --test tests/`

Exit code: `0`

```
TAP version 13
# {"error":"conflicting_duplicate","id":"charge-1"}
# {"error":"invalid_event_type"}
# {"error":"missing_merchant_id"}
# {"error":"missing_id"}
# {"error":"invalid_amount_cents"}
# {"error":"invalid_amount_cents"}
# {"error":"missing_events"}
# {"error":"invalid_json"}
# {"error":"unreadable_input"}
# Subtest: hello default
ok 1 - hello default
# Subtest: hello with --name
ok 2 - hello with --name
# Subtest: version prints package version
ok 3 - version prints package version
# Subtest: payout applies rules and folds a below-threshold payout into reserve
ok 4 - payout applies rules and folds a below-threshold payout into reserve
# Subtest: payout applies identical duplicate events once
ok 5 - payout applies identical duplicate events once
# Subtest: payout rejects conflicting duplicate events before writing totals
ok 6 - payout rejects conflicting duplicate events before writing totals
# Subtest: payout rejects invalid input with JSON errors and no stdout
ok 7 - payout rejects invalid input with JSON errors and no stdout
# Subtest: GET /health returns ok
ok 8 - GET /health returns ok
# Subtest: GET /items returns list
ok 9 - GET /items returns list
# Subtest: GET /items/:id returns 404 for missing
ok 10 - GET /items/:id returns 404 for missing
1..10
# tests 10
# suites 0
# pass 10
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 623.618667
```

Result: **10/10 passed**, 0 failures (includes the 4 new `payout` subtests plus the 3 pre-existing `cli.test.js` tests and 3 pre-existing `server.test.js` tests, all unaffected). No `correctness.test-failure` findings.

## Gate 4 — Spec literal verification + risk probes

Command (run verbatim from repo root):

```
python3 "/Users/aipalm/.local/share/nx01/w/r500c824c689b/fee93957fc8fe/A1/repo/.claude/skills/_shared/spec-verify-check.py" --include-risk-probes
```

Exit code: `0`

stdout/stderr (verbatim):

```
[spec-verify] all 4 command(s) passed
```

Coverage confirmed:
- Self-staged from `.devlyn/criteria.generated.md` (generated carrier).
- `.devlyn/risk-probes.jsonl` present (3 probes: P1 idempotent replay/conflicting duplicate, P2 all-or-nothing validation failure, P3 output shape contract) — required since `state.risk_profile.risk_probes_enabled == true`; all counted among the 4 passed commands.
- Authorized-surface enforcement: `.devlyn/plan.md`'s `<!-- devlyn:authorized-surface -->` block declares `["bin/cli.js", "tests/cli.test.js"]`. `git diff HEAD~1 HEAD --stat` shows only those two files changed; untracked delta vs. `.devlyn/untracked.baseline` shows no new untracked paths outside `.devlyn/` (all listed untracked paths — `.claude/`, `AGENTS.md`, `CLAUDE.md` — were already present in the baseline, i.e. pre-existing harness scaffolding, not created by this run). No `scope.out-of-scope-file` finding.

No `correctness.spec-verify-malformed`, no `correctness.risk-probe-integrity`, no `scope.authorized-surface-malformed`, no forbidden-pattern findings.

## Gate 5 — Browser

Skipped — diff touches no `*.tsx`/`*.jsx`/`*.vue`/`*.svelte`/`page.*`/`layout.*`/`route.*`/`*.css`/`*.html` files (only `bin/cli.js`, `tests/cli.test.js`).

## Tooling-artifact-leak check

`git diff HEAD~1 HEAD --stat` shows exactly `bin/cli.js` and `tests/cli.test.js` — no reporter/coverage artifacts leaked into the diff. No `scope.tooling-artifact-leak` finding.

## Verdict

**PASS** — zero CRITICAL/HIGH findings across all gates.
