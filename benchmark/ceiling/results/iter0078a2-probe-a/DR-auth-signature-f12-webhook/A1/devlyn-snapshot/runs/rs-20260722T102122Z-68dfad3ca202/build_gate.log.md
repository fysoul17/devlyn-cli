# BUILD_GATE log

Repo root: `/Users/aipalm/.local/share/nx01/w/rfe4a3450fa47/f08d6b52f5d4d/A1/repo`
base_ref.sha: `d5e479312b6f9573373bd2057e630bba7d22c608`

## Gate 1 — Type check

**Skipped.** No `tsconfig.json` present in the repo.

## Gate 2 — Lint

**Skipped.** No `.eslintrc*` (or other lint config) present. `npm run lint:json` is a JSON-file linter, not a code-style linter, and is out of scope for this gate.

## Gate 3 — Test suite

Command: `node --test tests/`

Exit code: `0`

Raw output:

```
TAP version 13
# Subtest: hello default
ok 1 - hello default
  ---
  duration_ms: 36.548625
  ...
# Subtest: hello with --name
ok 2 - hello with --name
  ---
  duration_ms: 32.96325
  ...
# Subtest: version prints package version
ok 3 - version prints package version
  ---
  duration_ms: 28.755542
  ...
# Subtest: GET /health returns ok
ok 4 - GET /health returns ok
  ---
  duration_ms: 9.7705
  ...
# Subtest: GET /items returns list
ok 5 - GET /items returns list
  ---
  duration_ms: 1.981
  ...
# Subtest: GET /items/:id returns 404 for missing
ok 6 - GET /items/:id returns 404 for missing
  ---
  duration_ms: 1.412791
  ...
# Subtest: POST /webhook accepts a valid signed event
ok 7 - POST /webhook accepts a valid signed event
  ---
  duration_ms: 8.781167
  ...
# Subtest: POST /webhook rejects a replayed event id
ok 8 - POST /webhook rejects a replayed event id
  ---
  duration_ms: 2.496166
  ...
# Subtest: POST /webhook rejects a tampered body with its original signature
ok 9 - POST /webhook rejects a tampered body with its original signature
  ---
  duration_ms: 3.306917
  ...
# Subtest: POST /webhook rejects a validly signed body that fails the shape check
ok 10 - POST /webhook rejects a validly signed body that fails the shape check
  ---
  duration_ms: 4.230417
  ...
1..10
# tests 10
# suites 0
# pass 10
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 163.653042
```

Result: **10/10 pass, 0 fail.** No `correctness.test-failure` findings.

## Gate 4 — Spec literal verification + risk probes

`state.risk_profile.risk_probes_enabled` = `false` (confirmed in `.devlyn/pipeline.state.json`), so `.devlyn/risk-probes.jsonl` is not required for this run and was not generated.

Command:

```bash
DEVLYN_SHARED_DIR="/Users/aipalm/.local/share/nx01/w/rfe4a3450fa47/f08d6b52f5d4d/A1/repo/.claude/skills/_shared"
python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes
```

Exit code: `0`

Raw output:

```
[spec-verify] all 1 command(s) passed
```

### Authorized-surface scope check

PLAN's `<!-- devlyn:authorized-surface -->` block (`.devlyn/plan.md`) declares:

```json
{"authorized_surface": ["server/index.js", "tests/server.test.js"]}
```

Tracked diff vs base_ref (`git diff --stat d5e479312b6f9573373bd2057e630bba7d22c608..HEAD`):

```
 server/index.js      |  45 ++++++++++++++++++-
 tests/server.test.js | 119 +++++++++++++++++++++++++++++++++++++++++++++++++++
 2 files changed, 163 insertions(+), 1 deletion(-)
```

→ Exactly the two authorized files; no other tracked file changed.

Untracked-file delta: compared current `git status --porcelain=v1 --untracked-files=all` untracked list against `.devlyn/untracked.baseline` (captured at PLAN time, before IMPLEMENT ran). The only new untracked paths since baseline are all under `.devlyn/` (run artifacts: `criteria.generated.md`, `engines.json`, `goal.raw.txt`, `goal.txt`, `implement.*`, `pipeline.state.json`, `plan.md`, `surface-close.*`, `untracked.baseline` itself) — `.devlyn/` is exempt per the gate contract. No out-of-scope untracked files.

Result: **no `scope.out-of-scope-file` findings.**

## Gate 5 — Browser

**Skipped.** Diff touches only `server/index.js` and `tests/server.test.js`; no web-surface files changed.

## Reporter-artifact leak check

`git diff --stat` shows only the two authorized source files — no coverage HTML or other tooling-generated artifacts leaked into the diff. No `scope.tooling-artifact-leak` finding.

## Verdict

**PASS** — 0 CRITICAL, 0 HIGH findings. `.devlyn/build_gate.findings.jsonl` is empty (0 bytes).
