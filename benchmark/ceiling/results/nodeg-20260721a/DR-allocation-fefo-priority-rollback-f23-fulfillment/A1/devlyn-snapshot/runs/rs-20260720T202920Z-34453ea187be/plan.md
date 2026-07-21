# Plan — `fulfill-wave` command

## Source
`.devlyn/criteria.generated.md` (generated criteria, complexity: medium). Base sha `cbd12daedd7f2d22c62110faf097f12797e7dda6`.

<!-- devlyn:authorized-surface -->
## 1. Files to touch

| Path | Change | Rationale |
|---|---|---|
| `bin/cli.js` | edit | Add the `fulfill-wave` command per Requirement bullet 1 ("Add a `fulfill-wave` command to `bin/cli.js` invoked as `bench-cli fulfill-wave --input <path>`"). Currently `main()` (`bin/cli.js:38-61`) dispatches via `switch (command)` with cases `'hello'` (`bin/cli.js:47-51`) and `'version'` (`bin/cli.js:52-54`), falling through to `default:` (`bin/cli.js:56-59`) which prints `Unknown command` and exits 1. A new `case 'fulfill-wave':` must be added before `default` so the command is recognized. `USAGE` (`bin/cli.js:8-19`) must gain a `fulfill-wave --input <path>` line, matching the Constraints bullet "Follow the existing CLI pattern already in `bin/cli.js` (command dispatch in `main()`'s `switch`, `USAGE` text update)". All validation, allocation, and output-formatting logic lives in this file (helper functions alongside `readPackageVersion`/`parseNameFlag`, `bin/cli.js:21-36`) — no new files, per Constraint "Only touch `bin/cli.js` and `tests/cli.test.js`". |
| `tests/cli.test.js` | edit | Keep the 3 existing tests (`bin/cli.js:12-25` — `hello default`, `hello with --name`, `version prints package version`) passing unmodified, and add >=2 new tests per Requirement bullet 12: one accepted-allocation case and one rejected-all-or-nothing case. Tests reuse the existing `run(args)` helper (`tests/cli.test.js:8-10`, `execFileSync`) and existing `path`/`CLI` setup (`tests/cli.test.js:1-6`). Since only these two files may be touched, input JSON fixtures cannot live in a new `tests/fixtures/*.json` file — each new test must synthesize its input via `fs.mkdtempSync(...)` + `fs.writeFileSync(...)` (Node core `fs`/`os`, no new dependency) and pass the temp path via `--input`. |

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## 2. Risks

**Out-of-scope expansions to refuse:**
- No new npm dependencies (Constraint bullet 2) — use only `fs`, `path`, `os`, `node:test`, `node:assert`, `node:child_process`, all already in use or core modules.
- No new files (fixture JSON, docs, config) — authorized surface is exactly `bin/cli.js` and `tests/cli.test.js`.
- No carrier selection, package dimensions, backorders/partial-order acceptance, or persistence beyond stdout (Out of Scope bullet).
- No extra CLI flags beyond `--input` (e.g. no `--output`, `--dry-run`) — not requested.
- Do not touch the `hello`/`version`/`--help` code paths beyond appending the `fulfill-wave` line to `USAGE` and adding one `case` — no refactor of `parseNameFlag`/`readPackageVersion`.
- Add exactly the two required new tests (accepted + rejected-all-or-nothing); do not speculatively add a broad validation-matrix test suite — not requested by the spec's "at least two" minimum, and extra untested-by-spec assertions risk asserting on unprescribed stderr/stdout shapes.

**Ambiguous spec sections — strict interpretation to lock in before IMPLEMENT:**
- **`rejected` reason scope.** Validation failures (bad input shape) never reach the `rejected` array — they exit 2 with a stderr JSON object, before any allocation attempt. `rejected` (with `reason: "insufficient_stock"`) is populated only for orders that pass validation but fail allocation (global insufficient stock, or a `single_warehouse` line whose one candidate warehouse can't cover it). This is the only rejection reason, consistent with the literal schema `{ "id": string, "reason": "insufficient_stock" }`.
- **Rollback granularity.** Process an order's `lines` in the given array order; deduct tentatively from warehouse/lot state as each line is fulfilled. If any line in the order cannot be fully allocated, restore every unit tentatively deducted for that order (all prior successful lines in that order included) before moving to the next order. Stock deducted by *earlier accepted orders* is never restored.
- **Warehouse/lot selection is live, not precomputed.** Because each order's deductions affect stock visible to later orders (and later lines within the same order), warehouse/lot candidate lists must be evaluated against current mutable state at the time each line is processed, not against a snapshot taken once at the start.
- **`single_warehouse: true` selection.** Iterate warehouses sorted by `distance` asc, `id` asc; pick the first warehouse whose own lots (summed) can fully cover the line's qty; draw FEFO (`expires` asc, `lot` id asc) only from that warehouse. If no single warehouse suffices, the line fails (and the order rejects) even if the cross-warehouse sum would be enough — do not fall back to splitting.
- **`single_warehouse: false` selection.** Walk warehouses sorted by `distance` asc, `id` asc; within each, draw lots FEFO until the line qty is met or that warehouse's stock for the sku is exhausted, then continue to the next warehouse. If total available across all warehouses is insufficient, the line fails.
- **Allocation row granularity/order ("exact sequence stock was consumed").** Emit one allocation row per individual (warehouse, lot) draw at the moment it is consumed, in the order lines are processed within the order and warehouses/lots are visited within each line. Do not merge two draws from the same warehouse+lot into one row even if they arise from two different lines in the same order — each draw is its own row, in sequence.
- **`remaining` completeness.** After all orders are processed, emit one row per (warehouse, lot) pair whose post-processing qty is > 0 — including lots nothing was ever drawn from — sorted by `warehouse` id asc, then `sku` asc, then `expires` asc, then `lot` id asc. Lots drained to exactly 0 are omitted.
- **`submitted_at` "ISO date or timestamp".** Validate via a check that rejects non-string and unparseable values (e.g. `typeof v === 'string' && !Number.isNaN(Date.parse(v))`); do not additionally require a specific ISO subformat — `Date.parse` is the standard-library primitive for this per "best practice" (Core Principle 5), avoiding a hand-rolled ISO regex.
- **`expires` "valid YYYY-MM-DD calendar date".** `new Date('YYYY-MM-DD')` silently rolls invalid dates over (e.g. `2024-02-30` → `2024-03-01`), so format-regex alone is insufficient. Must round-trip: parse year/month/day as integers, construct via `Date.UTC`, and confirm `getUTCFullYear`/`getUTCMonth`/`getUTCDate` match the parsed components — otherwise reject.
- **Non-empty string ids/skus/lots.** `typeof v === 'string' && v.length > 0`. No trim/whitespace-only rejection requirement stated — do not add one (avoids unrequested validation per Goal-locked discipline).
- **`distance`/`priority` "are numbers".** `typeof v === 'number' && !Number.isNaN(v)`. Spec does not require positivity — do not add a positivity check that isn't asked for.
- **Missing/invalid `--input` flag or unreadable file.** Treated identically to "invalid input" per Requirement bullet 6 ("On invalid input **or a file-read failure**") — exit 2, nothing on stdout, one JSON object on stderr. No crash/stack-trace leakage.
- **"Do not mutate the input file on disk."** Trivially satisfied by only ever calling `fs.readFileSync` on the input path — never `writeFileSync`/`appendFileSync` to it. IMPLEMENT must not introduce any write to the `--input` path.

**Known failure modes for this language/framework:**
- Aliasing bugs: rollback must not share array/object references between "tentative" and "committed" stock state — deep-enough cloning or explicit delta-tracking (e.g. record `{warehouse, lot, qty}` deltas applied per order, then reverse them on rejection) is required, not a shallow copy that still shares nested lot objects.
- Key order in emitted JSON objects matters for readability/diffing even though `JSON.parse` on the test side is order-insensitive for `assert.deepStrictEqual` on parsed objects — construct each row's object literal with keys in the exact prescribed order (`id, allocations` / `sku, warehouse, lot, qty` / `id, reason` / `warehouse, sku, lot, qty, expires`) to match the literal schemas in the Requirements verbatim.
- `console.log`/`console.error` both append a trailing newline, which is fine for "one parseable JSON value" (parsers tolerate trailing whitespace) — but any stray `console.log`/debug output on the success path must be avoided, since Requirement bullet 10 requires stdout to contain exactly one JSON object and nothing else.
- The new `case 'fulfill-wave':` must come before `default:` in the `switch` (`bin/cli.js:46-60`) — trivial but easy to break by pattern-matching the wrong insertion point.
- Test side: `execFileSync` throws on non-zero exit. The "rejected all-or-nothing" test case is still an exit-0 run (the order is rejected in the *output*, not a process failure) — the test must not wrap that call in a try/catch; only a genuinely invalid-input test (not required, and per Risks above not being added) would need to catch the thrown `Error` with `.status`/`.stderr`. Do not add unnecessary try/catch scaffolding for the two required tests.
- Temp-file isolation: use `fs.mkdtempSync(path.join(os.tmpdir(), 'fulfill-wave-'))` per test (or per call) so concurrent/rerun test invocations never collide on a fixed filename.

## 3. Acceptance restatement

### Verbatim `## Verification` block from criteria

```json
{
  "verification_commands": [
    { "cmd": "node --test tests/", "exit_code": 0 }
  ]
}
```

### Plain-language restatement of every Requirement bullet

1. **Command surface.** `bin/cli.js` must gain a `fulfill-wave` command invoked as `bench-cli fulfill-wave --input <path>`. Input file is one JSON object: `{ warehouses: Warehouse[], orders: Order[] }`, `Warehouse = { id: string, distance: number, lots: Lot[] }`, `Lot = { sku: string, lot: string, qty: number, expires: "YYYY-MM-DD" }`, `Order = { id: string, priority: number, submitted_at: string, lines: Line[] }`, `Line = { sku: string, qty: number, single_warehouse: boolean }`.
2. **Full up-front validation, no partial allocation on bad input.** Before any allocation: all ids/SKU/lot identifiers must be non-empty strings; all quantities positive integers; every lot `expires` a real `YYYY-MM-DD` calendar date; every `submitted_at` parseable as an ISO date/timestamp; every `distance`/`priority` a number; `warehouses`/`orders`/`lots`/`lines` must each be arrays; order ids must be unique across the input. The input file must never be mutated on disk.
3. **Global order processing with all-or-nothing + rollback.** Orders are processed in one global sequence ordered by `priority` desc, then `submitted_at` asc, then `id` asc. An order is accepted only if every one of its lines can be fully allocated; if any line fails, the whole order is rejected and every tentative deduction made for that order (across all its lines) is rolled back. Accepted orders' deductions persist and reduce stock for subsequently processed orders; rejected orders leave stock exactly as it was.
4. **`single_warehouse` semantics.** A line with `single_warehouse: false` may be split across multiple warehouses and multiple lots. A line with `single_warehouse: true` must be filled entirely from one warehouse (though it may draw multiple lots within that warehouse), and must be rejected if no single warehouse alone holds enough stock — even if the sum across warehouses would be enough.
5. **Selection ordering.** Choose warehouses in `distance` ascending order, tie-broken by warehouse `id` ascending. Within a chosen warehouse, choose lots FEFO: `expires` ascending, tie-broken by `lot` id ascending. The `allocations` rows for an order must appear in the exact sequence stock was actually consumed.
6. **Success output contract.** On success: stdout gets exactly one parseable JSON object and nothing else; stderr gets nothing; process exits 0. The object has exactly the keys `accepted`, `rejected`, `remaining`.
   - `accepted`: in processing order; each row exactly `{ "id": string, "allocations": Allocation[] }`, `Allocation = { "sku": string, "warehouse": string, "lot": string, "qty": number }`.
   - `rejected`: in original input order; each row exactly `{ "id": string, "reason": "insufficient_stock" }`.
   - `remaining`: only lots with positive leftover qty, sorted by warehouse id, then sku, then expiry, then lot id; each row exactly `{ "warehouse": string, "sku": string, "lot": string, "qty": number, "expires": "YYYY-MM-DD" }`.
7. **Failure output contract.** On invalid input or a file-read failure: exit code 2; nothing on stdout; exactly one parseable JSON value on stderr that is a non-null, non-array object (member names not prescribed). No catch block may silently swallow the error and return `null`/`undefined`/`''`/`{}`; no empty catch blocks.
8. **Test updates.** `tests/cli.test.js` must keep all existing tests passing and gain at least two new `fulfill-wave` tests: one exercising an accepted allocation, one exercising a rejected all-or-nothing order.

## Verdict: PASS
