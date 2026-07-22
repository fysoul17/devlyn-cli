<!-- devlyn:authorized-surface -->
## Files to touch

- `bin/cli.js` (edit) — add the `fulfill-wave` case to the existing `switch` in `main()`, plus the input-validation, allocation-engine, and JSON-output helper functions it needs (Requirements: subcommand invocation/reading, entire-input validation, no-mutation, global ordering pass, all-or-nothing rollback, split vs single-warehouse line rules, distance/FEFO draw order, stdout success contract, stderr/exit-2 invalid-input contract, no-silent-catch rule).
- `tests/cli.test.js` (edit) — add the two required `fulfill-wave` tests (one accepted-allocation case, one rejected all-or-nothing case) alongside the existing `hello`/`version` tests, without modifying those (Requirement: "Update tests/cli.test.js: keep all existing tests passing, and add at least two new fulfill-wave tests").

```json
{"authorized_surface": ["bin/cli.js", "tests/cli.test.js"]}
```

## Risks

**Out-of-scope expansions to refuse:**
- No new files, no new npm dependency, no `package.json` edit, no argument-parsing library — `--input` must be parsed the same manual `argv.indexOf(...)` way `parseNameFlag` already does it (bin/cli.js:27-36), just without that function's `process.exit(1)` shortcut (see below).
- No changes to the `hello`, `version`, `--help`/`-h` behavior, and no new flags on `fulfill-wave` beyond `--input` (Out of Scope: "Any command or behavior other than fulfill-wave and the two required test additions"). Any other flag passed is ignored, not validated (Assumption).
- No carrier selection, package dimensions, backorders, partial-order acceptance, or persistence beyond stdout (Out of Scope, Requirements list).

**Ambiguous spec sections to interpret strictly (per the spec's own Assumptions — treat as binding, do not re-litigate):**
- Within one order, lines are attempted in the array order given in `order.lines`.
- For a `single_warehouse: true` line, when multiple warehouses individually hold enough stock, pick the first warehouse in standard order (distance asc, then warehouse id asc) whose lots for that sku sum to ≥ required qty.
- A missing/absent `--input` value is invalid input → same JSON-on-stderr + exit-2 path as any other validation failure, not a different error shape and not `parseNameFlag`'s `process.exit(1)` pattern.
- Unknown flags to `fulfill-wave` are silently ignored.

**Known failure modes for this language/framework:**
- `new Date('2026-02-30')` silently rolls over to March instead of throwing — a regex-shaped `YYYY-MM-DD` check is not sufficient. Validate by parsing year/month/day as integers and round-tripping through `Date.UTC` (or equivalent), confirming `getUTCFullYear`/`getUTCMonth`/`getUTCDate` match the input components exactly, to reject e.g. `2026-02-30`.
- `submitted_at` accepts "an ISO date or timestamp" — must accept both an ISO string and a numeric timestamp, rejecting only values where the parse genuinely fails (`NaN`), not narrowing to one format.
- `JSON.parse` on a malformed file and `fs.readFileSync` on a missing/unreadable path both throw — both must be caught explicitly and converted into the same non-null/non-array stderr JSON object + exit 2 contract; letting either throw uncaught would print a raw stack trace to stderr, which is neither JSON nor "nothing to stdout, nothing extra."
- No `fs.writeFileSync`/`appendFileSync`/`truncateSync` etc. may ever target the `--input` path, on any branch (success, per-order rejection, or top-level validation failure) — the input must only ever be read once via `fs.readFileSync`.
- The success path must produce exactly one `stdout` write (the final JSON) and zero `stderr` writes; no incidental `console.log`/`console.error` debug output anywhere in the `fulfill-wave` path.
- Per-order all-or-nothing rollback: snapshot the mutable stock model (deep-cloned lot quantities) before attempting an order, restore the snapshot wholesale if any line in that order fails, rather than hand-rolling incremental undo bookkeeping per deduction — simpler and avoids a partial-undo workaround.
- `Array.prototype.sort` is stable in Node ≥12 (spec since ES2019; this repo requires `engines.node >= 18`), so the global ordering pass (priority desc, then submitted_at asc, then id asc) and the FEFO/remaining sorts can use a single multi-key comparator without an external stable-sort helper.
- Every `catch` added must build a real, non-empty error value and act on it (route to the stderr-JSON + exit-2 path for `fulfill-wave`) — no catch may swallow and return `null`/`undefined`/`''`/`{}`, and none may be empty (explicit Requirement).
- `rejected` output must preserve **original input order** of `orders`, while `accepted` output must preserve **processing order** (the sorted global-pass order) — these are two different orderings and must not be conflated.
- Validation must run to completion over the *entire* input before any allocation/deduction begins (Requirement: "Validate the entire input before allocating anything") — do not validate-then-allocate per order.

## Acceptance restatement

Verbatim copy of the spec's `## Verification` block:

```json
{
  "verification_commands": [
    {
      "cmd": "node bin/cli.js hello",
      "exit_code": 0,
      "stdout_contains": [
        "Hello, world!"
      ]
    },
    {
      "cmd": "node -e 'const fs=require(\"fs\");\nconst path=require(\"path\");\nconst os=require(\"os\");\nconst {execFileSync}=require(\"child_process\");\nconst cli=path.join(process.cwd(),\"bin\",\"cli.js\");\nconst tmp=path.join(os.tmpdir(),\"fulfill-wave-accept-\"+process.pid+\".json\");\nconst fixture={\n  warehouses:[{id:\"W1\",distance:1,lots:[{sku:\"SKU1\",lot:\"L1\",qty:10,expires:\"2027-01-01\"}]}],\n  orders:[{id:\"O1\",priority:5,submitted_at:\"2026-01-01T00:00:00Z\",lines:[{sku:\"SKU1\",qty:4,single_warehouse:false}]}]\n};\nconst raw=JSON.stringify(fixture);\nfs.writeFileSync(tmp,raw);\ntry{\n  const out=execFileSync(\"node\",[cli,\"fulfill-wave\",\"--input\",tmp],{encoding:\"utf8\"});\n  const after=fs.readFileSync(tmp,\"utf8\");\n  if(after!==raw){throw new Error(\"input file was mutated\")}\n  const data=JSON.parse(out);\n  const keys=Object.keys(data).sort().join(\",\");\n  if(keys!==\"accepted,rejected,remaining\"){throw new Error(\"unexpected top-level keys: \"+keys)}\n  if(data.rejected.length!==0){throw new Error(\"expected no rejections\")}\n  if(data.accepted.length!==1||data.accepted[0].id!==\"O1\"){throw new Error(\"unexpected accepted rows: \"+JSON.stringify(data.accepted))}\n  const allocs=data.accepted[0].allocations;\n  if(allocs.length!==1||allocs[0].sku!==\"SKU1\"||allocs[0].warehouse!==\"W1\"||allocs[0].lot!==\"L1\"||allocs[0].qty!==4){\n    throw new Error(\"unexpected allocation: \"+JSON.stringify(allocs));\n  }\n  if(data.remaining.length!==1||data.remaining[0].qty!==6||data.remaining[0].lot!==\"L1\"){\n    throw new Error(\"unexpected remaining: \"+JSON.stringify(data.remaining));\n  }\n  process.stdout.write(\"MECH_ACCEPT_OK\\n\");\n}finally{\n  fs.unlinkSync(tmp);\n}'",
      "exit_code": 0,
      "stdout_contains": [
        "MECH_ACCEPT_OK"
      ]
    },
    {
      "cmd": "node -e 'const fs=require(\"fs\");\nconst path=require(\"path\");\nconst os=require(\"os\");\nconst {execFileSync}=require(\"child_process\");\nconst cli=path.join(process.cwd(),\"bin\",\"cli.js\");\nconst tmp=path.join(os.tmpdir(),\"fulfill-wave-reject-\"+process.pid+\".json\");\nconst fixture={\n  warehouses:[{id:\"W1\",distance:1,lots:[{sku:\"SKU1\",lot:\"L1\",qty:5,expires:\"2027-01-01\"}]}],\n  orders:[{id:\"O2\",priority:5,submitted_at:\"2026-01-01T00:00:00Z\",lines:[\n    {sku:\"SKU1\",qty:3,single_warehouse:false},\n    {sku:\"SKU1\",qty:10,single_warehouse:false}\n  ]}]\n};\nfs.writeFileSync(tmp,JSON.stringify(fixture));\ntry{\n  const out=execFileSync(\"node\",[cli,\"fulfill-wave\",\"--input\",tmp],{encoding:\"utf8\"});\n  const data=JSON.parse(out);\n  if(data.accepted.length!==0){throw new Error(\"expected zero accepted rows: \"+JSON.stringify(data.accepted))}\n  if(data.rejected.length!==1||data.rejected[0].id!==\"O2\"||data.rejected[0].reason!==\"insufficient_stock\"){\n    throw new Error(\"unexpected rejected rows: \"+JSON.stringify(data.rejected));\n  }\n  const rejectedKeys=Object.keys(data.rejected[0]).sort().join(\",\");\n  if(rejectedKeys!==\"id,reason\"){throw new Error(\"unexpected rejected row keys: \"+rejectedKeys)}\n  if(data.remaining.length!==1||data.remaining[0].qty!==5){\n    throw new Error(\"stock was not fully restored after rejection: \"+JSON.stringify(data.remaining));\n  }\n  process.stdout.write(\"MECH_REJECT_OK\\n\");\n}finally{\n  fs.unlinkSync(tmp);\n}'",
      "exit_code": 0,
      "stdout_contains": [
        "MECH_REJECT_OK"
      ]
    },
    {
      "cmd": "node -e 'const fs=require(\"fs\");\nconst path=require(\"path\");\nconst os=require(\"os\");\nconst {spawnSync}=require(\"child_process\");\nconst cli=path.join(process.cwd(),\"bin\",\"cli.js\");\nconst tmp=path.join(os.tmpdir(),\"fulfill-wave-invalid-\"+process.pid+\".json\");\nconst fixture={\n  warehouses:[{id:\"W1\",distance:1,lots:[{sku:\"SKU1\",lot:\"L1\",qty:-5,expires:\"2027-01-01\"}]}],\n  orders:[]\n};\nfs.writeFileSync(tmp,JSON.stringify(fixture));\ntry{\n  const res=spawnSync(\"node\",[cli,\"fulfill-wave\",\"--input\",tmp],{encoding:\"utf8\"});\n  if(res.status!==2){throw new Error(\"expected exit 2, got \"+res.status)}\n  if(res.stdout&&res.stdout.length>0){throw new Error(\"expected empty stdout, got: \"+res.stdout)}\n  let parsed;\n  try{parsed=JSON.parse(res.stderr)}catch(e){throw new Error(\"stderr was not parseable JSON: \"+res.stderr)}\n  if(parsed===null||Array.isArray(parsed)||typeof parsed!==\"object\"){\n    throw new Error(\"stderr JSON must be a non-null, non-array object\");\n  }\n  process.stdout.write(\"MECH_INVALID_OK\\n\");\n}finally{\n  fs.unlinkSync(tmp);\n}'",
      "exit_code": 0,
      "stdout_contains": [
        "MECH_INVALID_OK"
      ]
    }
  ]
}
```

Additionally: `npm test` (runs `node --test tests/`) must exit 0 with all existing tests (`tests/cli.test.js`, `tests/server.test.js`) plus the two new `fulfill-wave` tests passing.
