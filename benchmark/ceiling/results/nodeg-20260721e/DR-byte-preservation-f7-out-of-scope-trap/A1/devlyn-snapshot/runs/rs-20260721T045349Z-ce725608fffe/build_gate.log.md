# BUILD_GATE log

Run from repo root: `/Users/aipalm/.local/share/nx01/w/r500c824c689b/ff10888c89791/A1/repo`

## Detection

Node project (`package.json` present, no `tsconfig.json`, no `.eslintrc*`). No type-check or lint gate applies. Package manager npm. Test script `node --test tests/` (whole `tests/` directory: `tests/cli.test.js` + `tests/server.test.js`).

## Gate 1 — Type check

N/A, skipped (no `tsconfig.json`).

## Gate 2 — Lint

N/A, skipped (no ESLint config).

## Gate 3 — Test suite

Command: `node --test tests/`

Result: **PASS** — 8/8 tests passed, 0 failed.

```
TAP version 13
# Subtest: hello default
ok 1 - hello default
# Subtest: hello with --name
ok 2 - hello with --name
# Subtest: version prints package version
ok 3 - version prints package version
# Subtest: version prints JSON with --format json
ok 4 - version prints JSON with --format json
# Subtest: version rejects unsupported --format value
ok 5 - version rejects unsupported --format value
# Subtest: GET /health returns ok
ok 6 - GET /health returns ok
# Subtest: GET /items returns list
ok 7 - GET /items returns list
# Subtest: GET /items/:id returns 404 for missing
ok 8 - GET /items/:id returns 404 for missing
1..8
# tests 8
# suites 0
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 263.063375
```

Exit code: 0.

## Gate 4 — Spec literal verification + risk probes

Command: `python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes`

Result: **FAIL** — 1/4 verification commands failed; 1 CRITICAL finding written to `.devlyn/spec-verify-findings.jsonl`.

```
[spec-verify] 1/4 command(s) failed; 1 finding(s) written to /Users/aipalm/.local/share/nx01/w/r500c824c689b/ff10888c89791/A1/repo/.devlyn/spec-verify-findings.jsonl
```

Exit code: 1.

Raw finding (`.devlyn/spec-verify-findings.jsonl`):

```json
{"id": "BGATE-0001", "rule_id": "correctness.spec-literal-mismatch", "level": "error", "severity": "CRITICAL", "confidence": 1.0, "message": "Verification command #3 failed: expected exit 0, got 1.", "file": ".devlyn/spec-verify.json", "line": 1, "phase": "build_gate", "criterion_ref": "spec-verify://verification_commands/2", "fix_hint": "See .devlyn/spec-verify.results.json for the captured output. Update implementation so `node bin/cli.js version --format yaml` matches the contract (exit_code=0, contains=[], not_contains=[]).", "status": "open"}
```

Captured command results (`.devlyn/spec-verify.results.json`):

| # | cmd | expected_exit | actual_exit | pass |
|---|---|---|---|---|
| 0 | `node bin/cli.js version` | 0 | 0 | true |
| 1 | `node bin/cli.js version --format json` | 0 | 0 | true |
| 2 | `node bin/cli.js version --format yaml` | 0 | 1 | **false** |
| 3 | `node --test tests/cli.test.js` | 0 | 0 | true |

**Root-cause evidence (verified, not guessed) — the finding is a false positive from a contract-authoring defect, not an implementation defect:**

- The schema for verification commands (`.claude/skills/_shared/expected.schema.json:17-25`) defines the exit-code field as `exit_code` (item schema has `additionalProperties: false`, so unknown keys are silently ignored by consumers that use `.get()`).
- `.devlyn/criteria.generated.md:32-35` (mirrored in `.devlyn/plan.md:24-28`) authored all four `verification_commands` entries using the key `expect_exit` instead of `exit_code`. For command #3 this was `{"cmd": "node bin/cli.js version --format yaml", "expect_exit": 1}` — clearly intending exit 1.
- `spec-verify-check.py:4117` reads `expected_exit = vc.get("exit_code", 0)`. Since `expect_exit` is not `exit_code`, every command in this run's self-staged contract silently defaulted to `exit_code: 0` (confirmed in `.devlyn/spec-verify.json:5,9,13,17`, all read back as `"expect_exit": ...` literally — i.e. the staged file itself still carries the wrong key, so the runner's `.get("exit_code", 0)` never saw a `1` for command #3).
- Direct verification: `node bin/cli.js version --format yaml` exits 1 and prints `Unsupported version format: yaml` — exactly the criteria requirement ("`--format yaml` (or any other unsupported value) exits 1 with an error message"). The corresponding new test `version rejects unsupported --format value` (`tests/cli.test.js`) passes under `node --test tests/` (see Gate 3 output above, `ok 5`).
- Conclusion: `bin/cli.js` and `tests/cli.test.js` correctly implement the spec. The CRITICAL finding traces to `.devlyn/criteria.generated.md:34` (and `.devlyn/plan.md:27`) using a non-schema key name, not to the authorized-surface files. BUILD_GATE does not fix this (detection-only role); see `fix_hint` in `.devlyn/build_gate.findings.jsonl`.

### Authorized-surface check

`spec-verify-check.py` also enforces PLAN's `authorized_surface` (`["bin/cli.js", "tests/cli.test.js"]`) against this run's diff/untracked delta. No `scope.out-of-scope-file` finding was emitted — only the one `correctness.spec-literal-mismatch` finding above appears in `.devlyn/spec-verify-findings.jsonl`. Pre-existing untracked harness files (`.claude/`, `.devlyn/`, `AGENTS.md`, `CLAUDE.md`) are recorded in `.devlyn/untracked.baseline` and correctly excluded.

## Gate 5 — Browser tier

N/A, skipped — diff touches only `bin/cli.js` and `tests/cli.test.js`, no web-surface files.

## Verdict

**FAIL** — 1 CRITICAL finding (`BGATE-0001`, `correctness.spec-literal-mismatch`), root-caused above to a contract key-name defect (`expect_exit` vs. schema-canonical `exit_code`) in `.devlyn/criteria.generated.md` / `.devlyn/plan.md`, not to `bin/cli.js` or `tests/cli.test.js`.
