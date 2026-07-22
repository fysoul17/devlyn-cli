# BUILD_GATE log — round 2

Repo: `/Users/aipalm/.local/share/nx01/w/rfe286ecefc19/ff10888c89791/A1/repo`
Detected: Node.js CLI ("harbor-tools"), npm. No `tsconfig.json` (type-check gate skipped). No eslint config (lint gate skipped). No web-surface files touched (browser gate skipped).

Context: round 1 FAILED with 1 CRITICAL finding (`BGATE-0001`, `correctness.spec-literal-mismatch`)
caused by `.devlyn/criteria.generated.md`'s `## Verification` JSON block using the wrong schema field
names (`expect_exit` / `expect_stdout_matches` instead of the script's canonical `exit_code` /
`stdout_contains`), which made the `--format yaml` exit-code expectation silently default to `0` and
mismatch the correct actual exit code of `1`. The orchestrator fixed `.devlyn/criteria.generated.md`
to use `exit_code` / `stdout_contains`; no source code changes were made or needed. This round
re-verifies from scratch, independently, using the same commands as round 1.

## Gate 1 — Test suite (`npm test`)

Command: `npm test` (repo root).

Exit code: 0. All 8 tests passed, 0 failures.

Raw output (tail):

```
> harbor-tools@0.1.0 test
> node --test tests/

TAP version 13
# Unsupported version format: yaml
# Subtest: hello default
ok 1 - hello default
  ---
  duration_ms: 33.81975
  ...
# Subtest: hello with --name
ok 2 - hello with --name
  ---
  duration_ms: 33.945584
  ...
# Subtest: version prints package version
ok 3 - version prints package version
  ---
  duration_ms: 29.611
  ...
# Subtest: version prints JSON when requested
ok 4 - version prints JSON when requested
  ---
  duration_ms: 28.889125
  ...
# Subtest: version rejects unsupported --format value
ok 5 - version rejects unsupported --format value
  ---
  duration_ms: 28.873375
  ...
# Subtest: GET /health returns ok
ok 6 - GET /health returns ok
  ---
  duration_ms: 12.397167
  ...
# Subtest: GET /items returns list
ok 7 - GET /items returns list
  ---
  duration_ms: 2.232375
  ...
# Subtest: GET /items/:id returns 404 for missing
ok 8 - GET /items/:id returns 404 for missing
  ---
  duration_ms: 1.506291
  ...
1..8
# tests 8
# suites 0
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 197.225
```

Findings: none.

## Gate 2 — Spec literal verification + risk probes + authorized-surface enforcement

Command:

```
python3 "/Users/aipalm/.local/share/nx01/w/rfe286ecefc19/ff10888c89791/A1/repo/.claude/skills/_shared/spec-verify-check.py" --include-risk-probes
```

Exit code: 0. All 4 verification commands passed.

Raw stdout:

```
[spec-verify] all 4 command(s) passed
```

Per-command results (`.devlyn/spec-verify.results.json`):

| # | cmd | expected_exit | actual_exit | stdout_contains | pass |
|---|-----|---------------|-------------|------|------|
| 0 | `npm test` | 0 | 0 | — | true |
| 1 | `node bin/cli.js version --format json` | 0 | 0 | `{"version":"0.1.0"}` | true |
| 2 | `node bin/cli.js version` | 0 | 0 | `0.1.0` | true |
| 3 | `node bin/cli.js version --format yaml` | 1 | 1 | `Unsupported version format` | true |

Command #4 now correctly expects `exit_code: 1` (read from the fixed `criteria.generated.md`) and the
actual exit code is `1` — the round-1 false-negative is resolved. This confirms round 1's diagnosis was
correct: the implementation was never wrong, only the criteria file's schema field names were.

`.devlyn/spec-verify-findings.jsonl` came back with 0 lines — no findings of any kind, including no
`correctness.spec-literal-mismatch` findings.

### Authorized-surface / scope enforcement

`plan.md` declares `authorized_surface: ["bin/cli.js", "tests/cli.test.js"]`.

Independently verified via `git log -1 --stat` against the implementation commit (`8b280a5`,
"chore(pipeline): surface-close"):

```
 bin/cli.js        | 2 +-
 tests/cli.test.js | 4 ++++
 2 files changed, 5 insertions(+), 1 deletion(-)
```

`git diff --stat HEAD` is empty (change already committed). Only `bin/cli.js` and `tests/cli.test.js`
were touched by the implementation — both inside the authorized surface. Remaining untracked paths
(`.claude/`, `.devlyn/`, `AGENTS.md`, `CLAUDE.md`) are pipeline/harness artifacts exempt via the
`.devlyn/` carve-out (and `AGENTS.md`/`CLAUDE.md` are not part of this change's diff). No
`scope.out-of-scope-file` findings were emitted.

### Risk probes

`--include-risk-probes` was passed; no risk-probe-specific findings were emitted (0 lines in
`spec-verify-findings.jsonl`).

## Summary

- Gate 1 (tests): PASS, 0 findings.
- Gate 2 (spec-verify + scope + risk probes): PASS, 0 findings.
- Combined verdict: **PASS** (0 CRITICAL/HIGH findings).
