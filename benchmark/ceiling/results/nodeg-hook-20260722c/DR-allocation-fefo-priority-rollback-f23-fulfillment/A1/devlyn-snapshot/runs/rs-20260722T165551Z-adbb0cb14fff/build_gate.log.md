# BUILD_GATE log

## Detection

- Node.js repo (`package.json` present, no `tsconfig.json`, no `.eslintrc*` at repo root).
- Diff scope (`git diff --name-only cbd12da HEAD`): `bin/cli.js`, `tests/cli.test.js` only.
- No `.tsx/.jsx/.vue/.svelte/page.*/layout.*/route.*/*.css/*.html` touched — browser tier skipped.

## Gate 1 — Type check

Skipped: no `tsconfig.json` in repo.

## Gate 2 — Lint

Skipped: no `.eslintrc*` at repo root. `package.json` declares `lint:json` → `scripts/lint-json.js`, which does not exist in this repo. Pre-existing repo gap unrelated to this diff (diff touches only `bin/cli.js` and `tests/cli.test.js`); not created here per Subtractive-first / Goal-locked scope discipline.

## Gate 3 — Test suite (`npm test` → `node --test tests/`)

Exit code: `0`. 11/11 tests passed, 0 failures.

```
> harbor-tools@0.1.0 test
> node --test tests/

TAP version 13
# {"error":"order id must be a non-empty string"}
ok 1 - hello default
ok 2 - hello with --name
ok 3 - version prints package version
ok 4 - fulfill-wave allocates stock in warehouse and FEFO order
ok 5 - fulfill-wave rejects an all-or-nothing order without consuming stock
ok 6 - fulfill-wave reports invalid input as one stderr JSON object with exit 2
ok 7 - fulfill-wave rejects single-warehouse lines that require combined warehouse stock
ok 8 - fulfill-wave processes priority first and rolls back failed lower-priority draws
ok 9 - GET /health returns ok
ok 10 - GET /items returns list
ok 11 - GET /items/:id returns 404 for missing
1..11
# tests 11
# suites 0
# pass 11
# fail 0
# cancelled 0
# skipped 0
# todo 0
```

(The stray `# {"error":"order id must be a non-empty string"}` line is TAP-diagnostic output emitted by the CLI's own stderr JSON contract while the invalid-input test exercises `fulfill-wave`'s exit-2 path — expected, not a failure; the corresponding subtest still reports `ok`.)

No test in `tests/cli.test.js` failed. No environment-only failures (e.g. `server.test.js` socket-bind `EPERM`) were observed in this run.

## Gate 4 — Spec literal verification

Command: `python3 "/Users/aipalm/.local/share/nx01/w/rb50d3c291c96/f99dbe9386580/A1/repo/.claude/skills/_shared/spec-verify-check.py" --include-risk-probes`

Exit code: `0`.

```
[spec-verify] all 4 command(s) passed
```

Per-command detail from `.devlyn/spec-verify.results.json` (all `pass: true`):
1. `node --test tests/` → stdout contains `"# pass 11"`, `"# fail 0"` — pass.
2. Accepted-allocation fixture → stdout contains `"accepted"`, `"O1"`, `"SKU1"`, `"W1"`, `"L1"` — pass.
3. Rejected/insufficient-stock fixture → stdout contains `"rejected"`, `"insufficient_stock"`, `"remaining"`, `"qty":3` — pass.
4. Invalid-input fixture → exit 2, empty stdout, non-empty stderr → `INVALID_INPUT_OK` — pass.

`authorized_surface` enforcement (`.devlyn/plan.md` → `["bin/cli.js", "tests/cli.test.js"]`) against the diff and created-during-run untracked files (vs `.devlyn/untracked.baseline`, `.devlyn/` exempt): no scope findings emitted. `.devlyn/spec-verify-findings.jsonl` is 0 bytes after this run.

## Gate 5 — Browser

Skipped: no web-surface files (`.tsx/.jsx/.vue/.svelte/page.*/layout.*/route.*/*.css/*.html`) touched by this diff.

## Verdict

**PASS** — zero CRITICAL/HIGH findings across all gates.
