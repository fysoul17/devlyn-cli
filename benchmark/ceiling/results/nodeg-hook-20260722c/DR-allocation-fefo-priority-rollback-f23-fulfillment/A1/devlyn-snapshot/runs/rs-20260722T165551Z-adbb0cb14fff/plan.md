# Plan — `fulfill-wave` CLI command

<!-- devlyn:authorized-surface -->
## 1. Files to touch

| Path | Change | Rationale |
|---|---|---|
| `bin/cli.js` | edit | Add a `fulfill-wave` case to the existing `switch (command)` dispatcher (`bin/cli.js:46`), alongside a `--input` flag parser (mirrors the `parseNameFlag` shape at `bin/cli.js:27-36`, but see Risk below on exit-code divergence), the input validator, the allocation engine, and the stdout/stderr writer. Covers Requirements R1 (subcommand + schema), R2 (validation), R3 (global processing order + all-or-nothing rollback), R4 (`single_warehouse` constraint), R5 (warehouse/lot selection order), R6 (success output shape), R7 (invalid-input/error contract). |
| `tests/cli.test.js` | edit | Keep the 3 existing tests (`hello default`, `hello with --name`, `version prints package version`) untouched. Add **exactly 5** new `fulfill-wave` tests (3 + 5 = 8), covering R8 and directly exercising Verification commands 1-4 (see Risks for why the count is exactly 5, not "at least 2"). |

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

**Scope discipline**
- Only `bin/cli.js` and `tests/cli.test.js` are authorized. No new fixture files for test inputs — temp JSON files must be written at runtime inside the test (e.g. `fs.mkdtempSync(path.join(os.tmpdir(), ...))` + `fs.writeFileSync`), then cleaned up. `os` and `fs` are already-available Node built-ins, not new dependencies.
- Do not touch `hello`, `version`, `--help`, or the default/unknown-command branch (`bin/cli.js:56-59`) beyond leaving them working. Do not refactor `parseNameFlag` or `readPackageVersion`.
- No new npm dependencies (confirmed: `package.json` declares only `express`, unrelated to the CLI).

**Exit-code / output-channel contract is stricter than the existing pattern — do not reuse it verbatim**
- The existing `--name` failure path (`bin/cli.js:31-34`) does `console.error(...)` + `process.exit(1)` with a plain-text message, and the unknown-command path (`bin/cli.js:56-59`) writes `console.error` **and** the full `USAGE` block to stderr, exiting `1`. Neither pattern satisfies `fulfill-wave`'s contract: invalid input / file-read failure must exit **`2`**, write **nothing** to stdout, and write **exactly one parseable JSON object** (non-null, non-array) to stderr — no `USAGE` text, no extra lines. A missing/invalid `--input` flag value falls under this same "invalid input" contract (exit 2 + JSON stderr), not the existing exit-1/plain-text convention — this is the strict reading adopted for the ambiguous case "what if `--input` itself is malformed."
- On success, write **nothing** to stderr and **exactly one** JSON object to stdout (a single `console.log(JSON.stringify(result))` call — no other `console.log`/`console.error`/`process.stdout.write` call may execute on that path).
- Read + parse + schema-validate must be wrapped in one `try/catch` that, on failure, builds a real error object (e.g. `{ error: err.message }`) and writes it to stderr before `process.exit(2)` — never an empty catch block, never a catch that returns `null`/`undefined`/`''`/`{}` silently (explicit repo rule). No catch is added around the allocation engine itself: validation already guarantees well-formed input reaches it, and no observed failure mode justifies a second defensive layer there.

**Validation must reject cases naive parsing would silently accept**
- `expires` ("valid `YYYY-MM-DD` calendar date"): a regex match alone is insufficient — `new Date('2026-02-30')` auto-rolls over to March instead of throwing. Validate by regex-matching `YYYY-MM-DD`, extracting the numeric parts, and confirming they round-trip through `Date.UTC` (catches Feb 30, month 13, day 0, leap-year Feb 29 on non-leap years, etc.).
- `submitted_at` ("parses as an ISO date or timestamp"): schema types it as a string, so accept it if `Date.parse(value)` is not `NaN`, OR the string is purely numeric and `Number(value)` is finite (epoch-ms-as-string case). This is the strict interpretation adopted for the spec's otherwise ambiguous "or timestamps."
- `distance` / `priority` must be `typeof === 'number' && Number.isFinite(...)` — a numeric-looking string (e.g. `"1"`) is rejected, no implicit coercion.
- `qty` must be `Number.isInteger(v) && v > 0` — rejects 0, negatives, non-integers, non-numbers.
- ids/sku/lot: `typeof === 'string' && v.length > 0`.
- Order id uniqueness is checked across the full `orders` array as part of the single up-front validation pass, before any allocation starts — "validate before allocating anything" means the whole document, not per-order.

**Allocation engine must not mutate the parsed input**
- Do not deep-clone the parsed document to satisfy "do not mutate the input file." Instead, build an independent working-stock structure (new plain objects: per warehouse, lots grouped by sku and pre-sorted by `expires` ascending then `lot` id ascending) derived from the parsed input. The engine only ever reads/writes this derived structure, never the parsed input's own objects/arrays — this makes mutation structurally impossible rather than defending against it after the fact.
- Warehouse iteration order (distance ascending, then id ascending) and lot iteration order (expires ascending, then lot id ascending) must use plain code-unit string/number comparison (`a < b ? -1 : a > b ? 1 : 0`), not `localeCompare` — locale-sensitive collation would make ordering environment-dependent.
- Global order-processing sequence (priority descending, then `submitted_at` ascending by resolved timestamp, then id ascending) is a separate sort from input order; the `rejected` output must use **original input order** (track each order's original array index), while `accepted` uses **processing order** — conflating the two orderings is a distinct, easy-to-miss bug.
- All-or-nothing + rollback: track every tentative stock deduction made while attempting an order's lines (which lot, how much) in a per-order list. If any line in the order cannot be fully satisfied, add every recorded deduction back to the working stock before moving on, and do not add the order to `accepted`. If all lines succeed, the deductions are already applied — no further action needed, and later orders in processing order see the reduced stock.
- `single_warehouse: true` lines: sum a warehouse's own matching-sku stock only; a warehouse qualifies only if its own total (across its own lots) covers the line's `qty`, even if two warehouses combined would. Reject the whole order if no single warehouse qualifies, even though `single_warehouse: false` lines in the same input could straddle warehouses.
- Allocation rows for a given order must be appended in the exact sequence stock was drawn (warehouse-then-lot draw order as the engine consumes it) — never grouped/merged by sku or lot after the fact, even if two rows end up referencing the same lot from two different lines.
- **`rejected` order (insufficient stock, part of the normal success JSON, exit 0) is not the same thing as invalid input (exit 2, stderr JSON)** — this distinction must not be conflated in either the implementation or the tests. A rejected order is a valid, successful `fulfill-wave` run that happens to report one order as unfulfillable.

**Output shape**
- Success stdout: one JSON object with **only** keys `accepted`, `rejected`, `remaining` — no extra bookkeeping fields (e.g. internal warehouse/lot working-stock structures) may leak into the serialized rows.
- `remaining`: only lots with qty `> 0` after all processing, sorted by warehouse id, then sku, then `expires`, then lot id. Since `expires` is already `YYYY-MM-DD`, plain string comparison sorts it chronologically — no need to parse it as a `Date` for this sort.

**Test-count precision (mechanical gate, not a style choice)**
- Verification command 1 requires `node --test tests/` stdout to contain the literal substring `"# pass 8"` and `"# fail 0"`. There are 3 existing tests. The spec prose says "add at least two" `fulfill-wave` tests, but the mechanical gate fixes the total at exactly 8 — so exactly **5** new tests must be added (not 2, not 6+, which would print `# pass 9` etc. and fail the substring check). Suggested 5, each tied to a distinct acceptance criterion (no padding): (1) accepted allocation — mirrors Verification command 2; (2) rejected all-or-nothing / `insufficient_stock` — mirrors Verification command 3; (3) invalid-input contract (exit 2, empty stdout, one JSON object on stderr) — mirrors Verification command 4; (4) `single_warehouse: true` rejected when only *combined* cross-warehouse stock would suffice (no single warehouse alone qualifies) — the one business rule not exercised by commands 1-4; (5) multi-order priority-descending processing where a higher-priority order consumes stock a lower-priority order needed, proving rollback doesn't leak stock back to orders it shouldn't.
- Existing `run(args)` helper (`tests/cli.test.js:8-10`) calls `execFileSync` with no `{ shell: true }` and default behavior: it **throws** on non-zero exit status, embedding `stdout`/`stderr` on the thrown error object. The exit-2 test must wrap the call in `try/catch` (or pass `{ encoding: 'utf8' }` directly and inspect `err.status`/`err.stdout`/`err.stderr`) rather than calling the existing `run()` helper and expecting a return value — calling `run()` directly on an exit-2 invocation will throw and fail the test file, not return a result to assert on.

## 3. Acceptance restatement

Verbatim copy of `.devlyn/criteria.generated.md`'s `## Verification` block:

```json
{
  "verification_commands": [
    {
      "cmd": "node --test tests/",
      "stdout_contains": ["# pass 8", "# fail 0"]
    },
    {
      "cmd": "TMP=$(mktemp) && printf '%s' '{\"warehouses\":[{\"id\":\"W1\",\"distance\":1,\"lots\":[{\"sku\":\"SKU1\",\"lot\":\"L1\",\"qty\":10,\"expires\":\"2026-01-01\"}]}],\"orders\":[{\"id\":\"O1\",\"priority\":1,\"submitted_at\":\"2026-01-01T00:00:00Z\",\"lines\":[{\"sku\":\"SKU1\",\"qty\":5,\"single_warehouse\":false}]}]}' > \"$TMP\" && node bin/cli.js fulfill-wave --input \"$TMP\"; CODE=$?; rm -f \"$TMP\"; exit $CODE",
      "stdout_contains": ["\"accepted\"", "\"O1\"", "\"SKU1\"", "\"W1\"", "\"L1\""]
    },
    {
      "cmd": "TMP=$(mktemp) && printf '%s' '{\"warehouses\":[{\"id\":\"W1\",\"distance\":1,\"lots\":[{\"sku\":\"SKU1\",\"lot\":\"L1\",\"qty\":3,\"expires\":\"2026-01-01\"}]}],\"orders\":[{\"id\":\"O1\",\"priority\":1,\"submitted_at\":\"2026-01-01T00:00:00Z\",\"lines\":[{\"sku\":\"SKU1\",\"qty\":5,\"single_warehouse\":false}]}]}' > \"$TMP\" && node bin/cli.js fulfill-wave --input \"$TMP\"; CODE=$?; rm -f \"$TMP\"; exit $CODE",
      "stdout_contains": ["\"rejected\"", "\"insufficient_stock\"", "\"remaining\"", "\"qty\":3"]
    },
    {
      "cmd": "TMP=$(mktemp) && printf '%s' '{\"warehouses\":[],\"orders\":[{\"id\":\"\",\"priority\":1,\"submitted_at\":\"bad\",\"lines\":[]}]}' > \"$TMP\" && node bin/cli.js fulfill-wave --input \"$TMP\" >/tmp/fw-stdout.$$ 2>/tmp/fw-stderr.$$; CODE=$?; OUT=$(cat /tmp/fw-stdout.$$); ERR=$(cat /tmp/fw-stderr.$$); rm -f \"$TMP\" /tmp/fw-stdout.$$ /tmp/fw-stderr.$$; if [ \"$CODE\" -eq 2 ] && [ -z \"$OUT\" ] && [ -n \"$ERR\" ]; then echo INVALID_INPUT_OK; exit 0; else echo INVALID_INPUT_FAIL; exit 1; fi",
      "stdout_contains": ["INVALID_INPUT_OK"]
    }
  ]
}
```
