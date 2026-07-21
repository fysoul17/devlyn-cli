# BUILD_GATE log — run rs-20260721T081212Z-c94ab0b2a11f

Repo: `/Users/aipalm/.local/share/nx01/w/r500c824c689b/f99dbe9386580/A1/repo`
Node: v20.19.0, npm: 10.8.2

## Gate 1 — Type check

Skipped. No `tsconfig.json` in the repo; project is plain JS (`package.json` has no TypeScript dependency).

## Gate 2 — Lint

`package.json` declares `"lint:json": "node scripts/lint-json.js"`, but `scripts/lint-json.js` does not exist in this repo — it was never present in the initial snapshot commit `cbd12da` (`git ls-tree -r cbd12da --name-only` has no `scripts/` entries) and is not part of this run's changed files (`bin/cli.js`, `tests/cli.test.js`). No ESLint config (`.eslintrc*`, `eslint.config.*`) is present either. Skipped — no applicable/working linter for the changed files. Not a finding: the missing script is a pre-existing repo condition outside `authorized_surface` (`["bin/cli.js", "tests/cli.test.js"]`) and outside this run's goal (`fulfill-wave` command).

## Gate 3 — Test suite

Command: `npm test` (== `node --test tests/`)

Exit code: 0

```
# tests 9
# suites 0
# pass 9
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 364.334167
```

All 9 tests passed: 3 pre-existing CLI tests (`hello default`, `hello with --name`, `version prints package version`), 3 new `fulfill-wave` tests (accept + FEFO ordering, all-or-nothing rollback, single-warehouse rejection when only combined stock suffices), and 3 pre-existing `server/` tests (`GET /health`, `GET /items`, `GET /items/:id`). No failures — zero `correctness.test-failure` findings.

## Gate 4 — Spec literal verification + risk probes

Command:

```
DEVLYN_SHARED_DIR="/Users/aipalm/.local/share/nx01/w/r500c824c689b/f99dbe9386580/A1/repo/.claude/skills/_shared"
python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes
```

Exit code: 0
stderr: `[spec-verify] all 2 command(s) passed`

Results (`.devlyn/spec-verify.results.json`):

| # | cmd | expected exit | actual exit | stdout_contains | pass |
|---|---|---|---|---|---|
| 0 | `npm test` | 0 | 0 | — | true |
| 1 | `node bin/cli.js --help` | 0 | 0 | `fulfill-wave` | true |

Both `## Verification` commands from `.devlyn/criteria.generated.md` (source type `generated`, `criteria_sha256` matches state) passed. `.devlyn/spec-verify-findings.jsonl` was written empty (0 bytes) by the script — no findings, including no `authorized_surface` scope violations. `risk_profile.risk_probes_enabled` is `false` for this run (demoted at PLAN time — small 2-path authorized surface), so `--include-risk-probes` ran with no `.devlyn/risk-probes.jsonl` required/produced; nothing to reconcile.

Independently confirmed the scope check: `git diff --stat cbd12da -- . ':!.devlyn' ':!.claude' ':!AGENTS.md' ':!CLAUDE.md'` shows only `bin/cli.js` (+236) and `tests/cli.test.js` (+115) changed, matching PLAN's `authorized_surface: ["bin/cli.js", "tests/cli.test.js"]` exactly. No other tracked/untracked deltas.

## Gate 5 — Browser

Skipped per BUILD_GATE instructions — diff touches only `bin/cli.js` and `tests/cli.test.js` (CLI + test files), no web-surface files.

## Tooling-artifact leak check

`git status --porcelain=v1` shows only `.claude/`, `.devlyn/`, `AGENTS.md`, `CLAUDE.md` untracked — the devlyn pipeline's own machine-local scaffolding, present before this gate ran (not test-reporter output). No `coverage/`, `test-results/`, `.nyc_output/`, or similar directories present. No `scope.tooling-artifact-leak` finding.

## Tally

| Gate | Result |
|---|---|
| Type check | skipped (no TS) |
| Lint | skipped (no linter applicable to changed files; `scripts/lint-json.js` pre-existing-missing, out of scope) |
| Test suite | PASS — 9/9 |
| Spec verify + risk probes | PASS — 2/2 commands, 0 findings |
| Browser | skipped (no web-surface files) |

**Findings: 0 CRITICAL, 0 HIGH, 0 MEDIUM, 0 LOW.**

Verdict: **PASS**
