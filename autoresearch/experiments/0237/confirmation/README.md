# Independent confirmation fixtures

These two fresh maintenance tasks were authored without viewing experiment candidate
instructions, iterations, existing evaluation results, or another author's fixtures.
Only the tasks-0102 schema example and the discovery validator were inspected for
packaging patterns. No model or network calls were used during fixture authoring.
The problems and source trees are original; neither is a rewritten EQ3 scenario.

- **CF-LEASE**: durable SQLite outbox ownership, producer idempotency, retry scheduling,
  worker error propagation, and recovery across connections. 18 visible files,
  4 public smoke tests, 13 hidden manifestations.
- **CF-CONFIG**: recursive configuration merging, relative include graphs, dependency
  freshness, detached snapshots, transactional reload publication, and recovery.
  19 visible files, 5 public smoke tests, 12 hidden manifestations.

Only `visible/` and the corresponding `goal.md` may be supplied to an evaluated
model. `hidden/`, `gold/`, `patches/`, predictions, controls, and this inventory
are evaluator-only artifacts. Gold trees preserve all public tests and docs;
patches contain production Python repairs only. Requirements tested by the oracle
have exact quotation and SHA-256 bindings to visible documentation.

Run the deterministic offline controls with:

```sh
python3 -B validate.py
python3 -B audit_controls.py
```

Python 3.11+ and its standard library suffice. Each control runs in a fresh copied
source tree and writes temporary files below `controls/scratch/`. The validator
checks inventories, requirement bindings, patch/reference consistency, public
smoke suites, manifestation inventories, and exact baseline/gold predictions.
Raw stdout, stderr, commands, and exit statuses are retained in `controls/*.json`.

The predictions were recorded before executing any public or hidden tests and
were not changed. All predictions matched: CF-LEASE baseline 4/13, gold 13/13;
CF-CONFIG baseline 1/12, gold 12/12. All public controls passed. An earlier
artifact-only preflight rejected incorrectly normalized patch context lines;
`controls/preflight-01.json` preserves that issue and its repair. Baseline and gold production behavior stayed unchanged after registration.

The independent audit found two fixture defects before model dispatch: the
original read-once oracle counted calls to one Python convenience method, and
a public test used an unresolved temporary path in canonical-path expectations.
Revision 2 observes file opens independently of the reader convenience method
and resolves the public test root. The complete original bundle and audit
reproduction are retained under `history/revision-1/`. New predictions were
registered in `predictions-revision-2.json` before revised controls. They all
matched: gold implementations using read_text, read_bytes, or builtin open
score 12/12; removing per-load memoization scores 11/12, failing only the
read-once check. Public tests pass with deliberately symlinked TMPDIR paths.
Baseline and gold fixture scores remain unchanged. `controls/audit-summary.json`
and individual logs retain these additional results.

`manifest.json` inside each task inventories its frozen task artifacts. The
root `confirmation-manifest.json` additionally binds predictions, validator,
raw controls, and this provenance note. Hashes are SHA-256 of exact file bytes.
