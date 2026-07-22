# BUILD_GATE log

Run timestamp: 2026-07-22T03:32:51Z
Repo: harbor-tools (Node.js, npm, no tsconfig.json)
Change under test: `POST /webhook` endpoint added to `server/index.js` (HMAC-SHA256 signature verification, body-shape validation, replay/duplicate-id detection) + 3 new tests in `tests/server.test.js` (on top of 3 pre-existing tests). Already committed as `5f18fcd chore(pipeline): implement`.

## Gate 1 — Lint

`package.json` scripts: `cli`, `start`, `test`, `lint:json`. `lint:json` (`node scripts/lint-json.js`) lints JSON files, not JS — inapplicable to `server/index.js` / `tests/server.test.js`. No general JS lint script exists in this repo.

**Verdict: SKIPPED (inapplicable) — no finding.**

## Gate 2 — Test suite (`npm test`)

Command: `npm test` (runs `node --test tests/`)

Raw output:

```
> harbor-tools@0.1.0 test
> node --test tests/

TAP version 13
# Subtest: hello default
ok 1 - hello default
  ---
  duration_ms: 31.79025
  ...
# Subtest: hello with --name
ok 2 - hello with --name
  ---
  duration_ms: 32.049416
  ...
# Subtest: version prints package version
ok 3 - version prints package version
  ---
  duration_ms: 28.853375
  ...
# Subtest: GET /health returns ok
ok 4 - GET /health returns ok
  ---
  duration_ms: 10.36225
  ...
# Subtest: GET /items returns list
ok 5 - GET /items returns list
  ---
  duration_ms: 1.94725
  ...
# Subtest: GET /items/:id returns 404 for missing
ok 6 - GET /items/:id returns 404 for missing
  ---
  duration_ms: 1.347083
  ...
# Subtest: POST /webhook accepts a valid signed event
ok 7 - POST /webhook accepts a valid signed event
  ---
  duration_ms: 8.563542
  ...
# Subtest: POST /webhook rejects a replayed event id
ok 8 - POST /webhook rejects a replayed event id
  ---
  duration_ms: 2.687333
  ...
# Subtest: POST /webhook rejects a tampered body with a stale signature
ok 9 - POST /webhook rejects a tampered body with a stale signature
  ---
  duration_ms: 1.268292
  ...
1..9
# tests 9
# suites 0
# pass 9
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 141.949666
```

Exit code: 0. 9/9 tests pass — the 3 pre-existing tests (`GET /health`, `GET /items`, `GET /items/:id`, plus the CLI tests `hello default`/`hello with --name`/`version`) are unmodified and green, and all 3 new webhook tests (happy path, replay 409, tampered-body 401) pass.

**Verdict: PASS — 0 findings.**

## Gate 3 — Spec literal verification + risk probes

Command (run exactly, from repo root):

```
python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes
```

Raw output:

```
[spec-verify] all 1 command(s) passed
```

Exit code: 0.

Staged contract (`.devlyn/spec-verify.json`, sourced from `.devlyn/plan.md`'s `<!-- devlyn:verification -->` block):

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "description": "run full test suite (existing tests + new webhook tests: happy path, replay 409, tampered-body 401)"
    }
  ]
}
```

`.devlyn/spec-verify-findings.jsonl`: empty (0 lines) — no literal-match or scope findings.

Authorized-surface enforcement: `.devlyn/plan.md`'s `<!-- devlyn:authorized-surface -->` block declares `["server/index.js", "tests/server.test.js"]`. The script diffs the current tree (git diff + untracked files, `.devlyn/` exempt) against this surface. Only `server/index.js` and `tests/server.test.js` were touched (per `git show --stat 5f18fcd`: `server/index.js | 40 ++++...`, `tests/server.test.js | 68 +++...`) — no `scope.out-of-scope-file` findings emitted.

Risk probes: `.devlyn/pipeline.state.json` → `state.risk_profile.risk_probes_enabled: false` (`risk_probes_explicit: false`) — auto-demoted at PLAN gate for this small two-file surface. No `.devlyn/risk-probes.jsonl` exists; per instructions this absence is expected, not a finding.

**Verdict: PASS — 0 findings.**

## Gate 4 — Browser validation

Diff touches only `server/index.js` and `tests/server.test.js` — no `*.tsx`/`*.jsx`/`*.vue`/`*.svelte`/`page.*`/`layout.*`/`route.*`/`*.css`/`*.html` files in scope.

**Verdict: SKIPPED (inapplicable) — no finding.**

## Overall

| Gate | Result |
|---|---|
| 1. Lint | skipped (inapplicable) |
| 2. Test suite | PASS (9/9) |
| 3. Spec literal verification + risk probes | PASS (0 findings) |
| 4. Browser | skipped (inapplicable) |

**BUILD_GATE verdict: PASS** — zero CRITICAL/HIGH findings across all applicable gates.
