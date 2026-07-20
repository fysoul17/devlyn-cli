# BUILD_GATE Log

Run against `harbor-tools` (Node.js), HEAD = `4c8e6b0` (`chore(pipeline): surface-close`), diff vs `cbd12da` = `bin/cli.js` (+224) and `tests/cli.test.js` (+125), 349 insertions / 0 deletions, 2 files changed.

## 1. Type check — SKIPPED
No `tsconfig.json` present in repo root.

## 2. Lint — SKIPPED
No ESLint/other lint config in repo root. `package.json` has a `lint:json` script referencing a non-existent `scripts/lint-json.js`; this is a pre-existing repo issue unrelated to this diff and out of scope for this run.

## 3. Test suite — PASS
Command: `npm test` (`node --test tests/`)

```
> harbor-tools@0.1.0 test
> node --test tests/

TAP version 13
# {"error":"orders must be an array"}
ok 1 - hello default
ok 2 - hello with --name
ok 3 - version prints package version
ok 4 - fulfill-wave accepts an order using FEFO lots from the nearest warehouse
ok 5 - fulfill-wave restores rejected stock and never combines warehouses for a single-warehouse line
ok 6 - fulfill-wave exits 2 with a JSON error object on stderr for invalid input
ok 7 - GET /health returns ok
ok 8 - GET /items returns list
ok 9 - GET /items/:id returns 404 for missing
1..9
# tests 9
# pass 9
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

Exit code: 0. All 9 tests pass, including the 3 new `fulfill-wave` tests (accepted allocation, rejected all-or-nothing with restore, invalid-input exit-2 contract). The `{"error":"orders must be an array"}` line on stderr is expected output from the invalid-input test case, not a failure.

## 4. Spec literal verification + risk probes — PASS
Command: `python3 ".claude/skills/_shared/spec-verify-check.py" --include-risk-probes`

```
[spec-verify] all 2 command(s) passed
```

Exit code: 0. Self-staged from `.devlyn/criteria.generated.md` (per `pipeline.state.json:source.criteria_path`, `source.type == "generated"`). The 2 `verification_commands` from criteria.generated.md both passed:
1. `npm test`
2. Invalid-JSON `fulfill-wave --input` exits with code 2

`authorized_surface` from `.devlyn/plan.md` (`["bin/cli.js", "tests/cli.test.js"]`) enforced against this run's diff/untracked delta — no `scope.out-of-scope-file` finding; confirmed independently via `git diff --stat HEAD~2 HEAD`, which shows only those 2 files changed.

`state.risk_profile.risk_probes_enabled` is `false` (demoted at PLAN time for small authorized surface) — no `.devlyn/risk-probes.jsonl` required, none checked.

## 5. Browser — SKIPPED
Diff touches only `bin/cli.js` and `tests/cli.test.js`; no web-surface files.

## Tooling-artifact-leak check
`git diff --stat HEAD~2 HEAD` shows exactly 2 files changed (`bin/cli.js`, `tests/cli.test.js`), 349 insertions, 0 deletions — no coverage HTML, `test-results/`, or other reporter artifacts leaked into the diff.

## Verdict
Zero CRITICAL/HIGH findings across all gates. **PASS**
