# Criteria (generated — free-form large mode)

recommend: /devlyn:ideate first — this spec was synthesized from a free-form goal without interactive elicitation; review the Assumptions section below before trusting the shipped behavior.

## Requirements

- Add a `fulfill-wave` subcommand to `bin/cli.js`, invoked as `bench-cli fulfill-wave --input <path>`, reading one JSON object `{ "warehouses": Array<Warehouse>, "orders": Array<Order> }` from the given file path.
- Validate the entire input before allocating anything: `id`/`sku`/`lot` strings non-empty; `qty` values positive integers; lot `expires` a valid real `YYYY-MM-DD` calendar date (reject e.g. `2026-02-30`); order `submitted_at` parseable as an ISO date or timestamp; `distance` and `priority` numeric; `warehouses`/`orders`/`lots`/`lines` arrays; order `id` values unique across the input. Any violation is invalid input.
- Never mutate the input file on disk, on any code path (success, rejection, or validation failure).
- Process orders in one global pass ordered by `priority` descending, then `submitted_at` ascending, then `id` ascending.
- Treat each order as all-or-nothing: if any line cannot be fully allocated, reject the whole order and roll back every tentative stock deduction made while attempting it; accepted orders' deductions persist and reduce stock available to later orders.
- A line with `single_warehouse: false` may split its required qty across multiple warehouses and lots.
- A line with `single_warehouse: true` must be fully satisfied by lots within a single warehouse (that warehouse's lots may still be combined); reject the line (and thus the order) if no single warehouse holds enough stock, even if the sum across warehouses would.
- Choose warehouses by `distance` ascending then `id` ascending; within a chosen warehouse, consume matching lots FEFO (`expires` ascending, then `lot` id ascending); allocation rows must appear in the exact sequence stock was drawn.
- On success, write exactly one parseable JSON object to stdout (only keys `accepted`, `rejected`, `remaining`), write nothing to stderr, and print no other text:
  - `accepted`: processing order; each row exactly `{ "id", "allocations": [{ "sku", "warehouse", "lot", "qty" }] }`.
  - `rejected`: original input order; each row exactly `{ "id", "reason": "insufficient_stock" }`.
  - `remaining`: positive leftover lot quantities only, sorted by warehouse id, then sku, then expiry, then lot id; each row exactly `{ "warehouse", "sku", "lot", "qty", "expires" }`.
- On invalid input or a file-read failure, exit `2`, write nothing to stdout, and write exactly one parseable JSON value to stderr that is a non-null, non-array object.
- Update `tests/cli.test.js`: keep all existing tests passing, and add at least two new `fulfill-wave` tests — one accepted-allocation case and one rejected all-or-nothing case.
- No catch block may silently return `null`/`undefined`/an empty string/an empty object, and no catch block may be empty.

## Constraints

- Only touch `bin/cli.js` and `tests/cli.test.js`.
- No new npm dependencies (`package.json` dependencies/devDependencies unchanged).
- Match the existing CLI's style in `bin/cli.js` (plain `switch`-based command dispatch, `fs`/`path` only, no argument-parsing library).

## Out of Scope

- Carrier selection, package dimensions, backorders, partial order acceptance, and persistence beyond stdout.
- Any command or behavior other than `fulfill-wave` and the two required test additions.

## Assumptions

(Every assumption below is scope-narrowing and reversible; flagged for user review since this spec was synthesized from a free-form goal.)

- Within one order, lines are attempted in the array order given in the order's `lines` list; this only resolves an otherwise-undetermined intra-order consumption sequence and does not change any documented tie-break rule.
- For a `single_warehouse: true` line, when more than one warehouse individually holds enough stock, the warehouse chosen is the first one in the standard order (distance ascending, then warehouse id ascending) whose lots for that sku sum to at least the required qty.
- `fulfill-wave` accepts no flags beyond `--input <path>`; a missing or absent `--input` value is treated as invalid input and exits `2` with a JSON object on stderr, consistent with the file-read-failure contract.
- Any flag other than `--input` passed to `fulfill-wave` is ignored rather than validated, keeping the change scoped to the described contract.

<!-- devlyn:verification -->
## Verification

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
