# BUILD_GATE log

- base_ref: d059b43faf24e64eb7a560cc37cebd5ae30fe17b
- implement commit: 00d750c20bcf0fa8bf1098eefd93a075914b82f6
- diff under gate: `bin/cli.js` (+156), `tests/cli.test.js` (+62) -- matches authorized_surface in `.devlyn/plan.md`
- node: v20.19.0, npm: 10.8.2

## 1. Type check -- SKIPPED

No `tsconfig.json` in repo root. Project is plain JS. Confirmed via `ls tsconfig.json` (no such file).

## 2. Lint -- RAN (`npm run lint:json`)

`package.json` declares `"lint:json": "node scripts/lint-json.js"`. No ESLint config found in repo root (`.eslintrc*` / `eslint.config*` absent) and gate instructions say not to invent a JS linter, so only `lint:json` was run.

Command: `npm run lint:json`
Result: **FAIL** (exit 1)

```
node:internal/modules/cjs/loader:1215
  throw err;
  ^

Error: Cannot find module '.../repo/scripts/lint-json.js'
    at Module._resolveFilename (node:internal/modules/cjs/loader:1212:15)
    ...
code: 'MODULE_NOT_FOUND'
```

`scripts/lint-json.js` does not exist. Verified via `git ls-tree -r d059b43faf24e64eb7a560cc37cebd5ae30fe17b --name-only` that the `scripts/` directory was never part of the base commit -- this is a pre-existing gap in the repo, not something this diff introduced or touched. Outside `authorized_surface` (`bin/cli.js`, `tests/cli.test.js`), so not fixed inline. Recorded as finding `bg-001` (severity MEDIUM) rather than silently muted, per "configuration drift between this gate and CI is a defect; raise as a finding rather than soften this gate."

## 3. Test suite -- RAN (`npm test` == `node --test tests/`)

Result: **PASS** -- 8/8 tests, 0 failures.

```
# tests 8
# suites 0
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

Includes the 2 new tests added this run:
- `cart prices an input file` -- ok
- `cart reports a combined quantity that exceeds stock` -- ok

Pre-existing suites (`hello default`, `hello with --name`, `version prints package version`, 3x server tests) remain green -- untouched by this diff.

## 4. Spec literal verification + risk probes

Command: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes`
(`DEVLYN_SHARED_DIR=/Users/aipalm/.local/share/nx01/w/rfe286ecefc19/f38c9cf695c9e/A1/repo/.claude/skills/_shared`)

Result: **PASS** -- `[spec-verify] all 3 command(s) passed`

- cmd 0: `node --test tests/` -> exit 0, pass
- cmd 1: cart happy-path pricing (MUG x2, CA, no coupon) -> stdout `CART_OK`, exact JSON match, exit 0, pass
- cmd 2: cart stock-validation error contract (BAG qty 5 vs stock 4) -> stdout `STOCK_FAIL_OK`, exit code 2, exact stderr JSON match, exit 0, pass

`.devlyn/spec-verify-findings.jsonl` written and confirmed empty (0 lines) -- includes the authorized_surface enforcement check (diff + untracked delta against `bin/cli.js`, `tests/cli.test.js` from `.devlyn/plan.md`'s `devlyn:authorized-surface` block); zero `scope.out-of-scope-file` findings.

`state.risk_profile.risk_probes_enabled` = `false` (demoted by PLAN's small 2-path authorized surface) -- confirmed in `.devlyn/pipeline.state.json`; no `.devlyn/risk-probes.jsonl` required, none produced.

## 5. Browser -- SKIPPED

Diff touches only `bin/cli.js` (CLI) and `tests/cli.test.js` (test file) -- no web-surface files (`web/`, `server/`) changed.

## Scope / artifact leak check

`git diff --stat d059b43faf24e64eb7a560cc37cebd5ae30fe17b HEAD` shows exactly 2 files changed (`bin/cli.js`, `tests/cli.test.js`), matching authorized_surface. No BUILD_GATE reporter artifact leaked into the tracked diff (`.devlyn/` is untracked / exempt).

## Verdict

**PASS** -- zero CRITICAL/HIGH findings. One MEDIUM finding (`bg-001`, pre-existing broken `lint:json` script, unrelated to and outside the scope of this diff) recorded in `.devlyn/build_gate.findings.jsonl`.
