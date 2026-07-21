# BUILD_GATE log

- Base ref: `d059b43faf24e64eb7a560cc37cebd5ae30fe17b`
- HEAD: `db34c3a562b7eaef9b8deb6bdf6b472683b201bf` (`chore(pipeline): implement`)
- Diff: `bin/cli.js` (+141), `tests/cli.test.js` (+74/-1) — matches PLAN's declared `authorized_surface` (`bin/cli.js`, `tests/cli.test.js`).
- Project shape: Node.js (`package.json`), no `tsconfig.json`, no project-wide lint config.

## Gate 1 — Type check
Skipped: no `tsconfig.json` present. N/A for this project shape.

## Gate 2 — Lint
`package.json` declares `"lint:json": "node scripts/lint-json.js"` only — not a project-wide linter.
Ran `npm run lint:json`:
```
Error: Cannot find module '/Users/aipalm/.local/share/nx01/w/r500c824c689b/f38c9cf695c9e/A1/repo/scripts/lint-json.js'
```
`scripts/lint-json.js` does not exist in the repo tree, confirmed pre-existing at base commit
`d059b43` (`git show d059b43:package.json` already references it; `git ls-tree -r d059b43` has no
`scripts/` entry at all). Not caused by this diff — this diff touches only `bin/cli.js` and
`tests/cli.test.js`, and `data/catalog.json` is untouched (declared read-only input, out of scope
per PLAN/criteria). No project-wide lint gate is applicable; no finding raised for a pre-existing,
out-of-scope repo condition.

## Gate 3 — Test suite
`npm test` (`node --test tests/`):
```
# tests 8
# pass 8
# fail 0
# cancelled 0
# skipped 0
# todo 0
```
Exit code 0. Includes the 3 pre-existing tests (`hello default`, `hello with --name`, `version
prints package version`), the 2 new `cart` tests, and 3 pre-existing `tests/server.test.js` tests
(untouched, out of scope, expected to run and pass).

## Gate 4 — Spec literal verification + risk probes
`state.risk_profile.risk_probes_enabled = false` → no `.devlyn/risk-probes.jsonl` required; none present.
No sibling `spec.expected.json` next to `.devlyn/criteria.generated.md` → script self-staged from the
legacy inline `<!-- devlyn:verification -->` carrier in `.devlyn/criteria.generated.md`.

```
python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes
[spec-verify] all 3 command(s) passed
```
Exit code 0. All 3 verification commands passed:
1. `npm test` — exit 0.
2. Cart smoke test (`OR`, `MUG` qty 1, no coupon) — `CART_SMOKE_OK`, exact key set and values matched.
3. Cart stock-error test (`CA`, `TEE` qty 7 + qty 5 = combined 12 > stock 10) — `CART_STOCK_ERR_OK`,
   exit 2, empty stdout, exact stderr JSON shape matched.

Authorized-surface enforcement (same invocation) passed: diff (`bin/cli.js`, `tests/cli.test.js`) and
untracked delta (`git status --porcelain` vs `.devlyn/untracked.baseline`) both fall entirely inside
PLAN's declared `authorized_surface`. No `scope.out-of-scope-file` / `scope.authorized-surface-malformed`
findings.

`.devlyn/spec-verify-findings.jsonl` written: 0 bytes (zero findings).

## Gate 5 — Browser
Skipped: diff touches only `bin/cli.js` and `tests/cli.test.js` — no `*.tsx/*.jsx/*.vue/*.svelte/
page.*/layout.*/route.*/*.css/*.html` file in the diff. Not applicable.

## Manual formula cross-check
Independently re-derived the `cart combines duplicate items and applies pricing rules` test's expected
values from `data/catalog.json` and the criteria's formula ledger (TEE buy_x_get_y_free 2-for-1,
BAG per-unit discount, ORDER10 coupon, CA tax 0.0825, free-shipping threshold) — all six top-level
amounts and both item rows match `bin/cli.js`'s `priceCart` implementation exactly. Validation order in
`priceCart` (missing_items → unknown_sku full scan → invalid_qty full scan → unknown_coupon →
unknown_state → combine-then-stock) matches PLAN's mandated two-pass ordering literally.
`process.exit()` confirmed (via isolated `node -e` probe) to terminate synchronously with no further
JS executing in the current call stack, so `cartError`'s `process.exit(2)` after a caught
`JSON.parse` failure in `readCart` cannot fall through into a second, conflicting error write.

## Verdict
Zero CRITICAL / HIGH findings. **PASS**.
