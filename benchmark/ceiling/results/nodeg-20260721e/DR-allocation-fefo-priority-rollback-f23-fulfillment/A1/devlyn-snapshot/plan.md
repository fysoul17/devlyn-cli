# Plan — `fulfill-wave` command

<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` — edit. Add the `fulfill-wave` case to the `switch` in `main()` (existing dispatch pattern at `bin/cli.js:46-60`), an `--input <path>` flag parser (mirrors `parseNameFlag` at `bin/cli.js:27-36`), input-JSON validation, the global allocation algorithm, and success/error output. Also add `fulfill-wave` to `USAGE` (`bin/cli.js:8-19`) per Requirement 1 and the Constraints note that usage-text is the only allowed touch to existing commands.
- `tests/cli.test.js` — edit. Keep the three existing tests (`hello default`, `hello with --name`, `version prints package version`, `tests/cli.test.js:12-25`) unmodified, and add at least two `fulfill-wave` tests: one accepted-allocation case and one rejected all-or-nothing case, per Requirement 5. Tests will need a way to feed a JSON fixture file to `--input` (e.g. write a temp file under `os.tmpdir()` or an inline fixture path) — the existing `run()` helper (`tests/cli.test.js:8-10`) already shells out via `execFileSync`, so a `fulfill-wave` test can reuse it and parse stdout as JSON.

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

- **Out-of-scope expansions to refuse** (per goal + Out of Scope section): no carrier selection, no package-dimension logic, no backorders, no partial order acceptance, no persistence of results beyond stdout. Do not touch `server/`, `package.json`, `scripts/`, or modify `hello`/`version` behavior — the only allowed edit to existing commands is adding `fulfill-wave` to the `USAGE` text.
- **Validate before allocating, not during.** Requirement 1 says "Fully validate ... before allocating anything." A single validation pass over the whole parsed object must run and fail-fast (exit 2) before any stock mutation begins — do not interleave validation with allocation.
- **Never mutate the input file on disk.** `fs.readFileSync` only; never call any `fs.write*`. Allocation must work on an in-memory deep-enough copy (or read-only traversal with local qty counters) so warehouse/lot objects are not mutated destructively if that would be observable — since nothing is written back to disk this is lower risk, but stock deductions during a rejected order's attempt must be fully reversible in memory (see next point).
- **All-or-nothing rollback.** For a `single_warehouse: false` line that spans multiple warehouses/lots, or for later lines within the same order, a failure on any line must roll back every tentative deduction made for that order — including deductions made by earlier lines of the *same* order. Track deductions per in-progress order (e.g. a list of `{warehouse, lot, qty}` decrements) and restore them all before moving to the next order if any line fails. Do not deduct incrementally and forget to restore on the failing line itself (partial-line deductions must also be undone).
- **FEFO tie-break ordering.** Sort candidate lots by `expires` ascending, then lot `id` ascending, and consume in that exact order — an off-by-one or unstable sort here silently reorders `allocations` rows, which Requirement 4 pins to "the exact sequence stock was chosen." Use a stable, explicit comparator; do not rely on input array order.
- **Warehouse selection ordering.** Sort candidate warehouses by `distance` ascending, then `id` ascending, before attempting a line. For a `single_warehouse: true` line, evaluate each warehouse's *own* total matching stock (summed across its own lots only) against the line qty — reject only if no single warehouse individually has enough, even though summed cross-warehouse stock might suffice.
- **Global order processing order.** Sort orders once, globally, by `priority` descending, then `submitted_at` ascending, then `id` ascending — this is a single pass across all orders, not per-warehouse or per-line. `submitted_at` must be parsed as a comparable timestamp (`Date.parse` per the validation rule that it "parses as an ISO date or timestamp"), not compared as a raw string, since two different ISO representations of the same instant must tie-break consistently by `id`.
- **Output key discipline.** Success stdout object has exactly `accepted` / `rejected` / `remaining` — no extra debug/meta keys. `accepted` rows are exactly `{id, allocations}` with allocation rows exactly `{sku, warehouse, lot, qty}`; `rejected` rows exactly `{id, reason: "insufficient_stock"}` in *original input order* (not processing order); `remaining` only includes lots with qty > 0 (Requirement 4: "positive leftover"), sorted by warehouse id, then sku, then expiry, then lot id, each row exactly `{warehouse, sku, lot, qty, expires}`. Emit via a single `process.stdout.write(JSON.stringify(...))` (or `console.log`) call — nothing else may write to stdout on the success path.
- **Error contract.** On any validation failure or file-read failure (missing file, invalid JSON, ENOENT, etc.): write nothing to stdout, write exactly one parseable JSON object (non-null, non-array — e.g. `{ "error": "<message>" }`) to `stderr`, and `process.exit(2)`. No silently-swallowing `catch` — a `catch` block that only returns `null`/`undefined`/`""`/`{}` or is empty is explicitly forbidden; every catch must translate the failure into the stderr JSON object and exit 2. `fs.readFileSync`/`JSON.parse` failures must be caught and routed through this same path, not left to crash with a raw stack trace (that would violate "write exactly one parseable JSON object to stderr").
- **`--help` interaction.** `main()` currently checks `!command || command === '--help' || command === '-h'` before the `switch` (`bin/cli.js:41-44`) and returns the full `USAGE`. `fulfill-wave --help` is not called out by any Requirement, so no special-case handling is needed beyond adding the command line to `USAGE`; do not add a per-command `--help` flag (unrequested, would be speculative robustness).
- **Ambiguous spec point resolved strictly:** "quantities are positive integers" applies to lot `qty`, line `qty`, and any allocation `qty` — reject zero, negative, or non-integer (e.g. float) values during validation. `distance`/`priority` "are numbers" (not restricted to integers) — allow floats/negatives there since the Requirement doesn't restrict them further.

## Acceptance restatement

Verbatim from `.devlyn/criteria.generated.md` `## Verification`:

```json
{
  "verification_commands": [
    {
      "cmd": "npm test",
      "exit_code": 0
    },
    {
      "cmd": "node bin/cli.js --help",
      "exit_code": 0,
      "stdout_contains": ["fulfill-wave"]
    }
  ]
}
```
