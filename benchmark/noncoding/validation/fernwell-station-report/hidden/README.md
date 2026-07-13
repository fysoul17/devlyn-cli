# fernwell-station-report — why the bad packets are packet-decisive

Family: `CONTENT_CONSTRAINT_MUTATION` (both bad packets).

## The hinge

`task.txt` states two content constraints that the oracle turns into mechanical
checks:

- **An ownership / preservation boundary.** `report/renderer_text.py` must stay
  byte-for-byte as checked in — two other teams import `render_text` and diff its
  output. The oracle pins its sha256 (`ec9f63d0…`), which is the digest of the seed
  file the task points at.
- **An exact output format.** The CSV must be exactly the five lines quoted in the
  task, ordered by trip count descending with an A-Z tie-break on station name. The
  oracle compares `python3 -m report.cli --format csv` byte-for-byte.

Both are invisible to the seed's own suite, and both are things a plausible-sounding
plan can get wrong without making the code any harder.

In both bad packets the task ids, the task array order, every `depends_on` edge and
every `context_refs` entry are byte-identical to good-a. Only content values move —
`objective`, `scope.may_change`, `scope.must_preserve`, `acceptance[].observable`
and `project_acceptance[].observable`.

## bad-1 — the frozen file is opened up

Mutated values (all in-family):
- `t1-renderer-csv.objective`: "Do not modify report/renderer_text.py: put all of
  this in the new module …" becomes "So that the two renderers do not duplicate the
  row-formatting logic, first refactor report/renderer_text.py to expose a shared
  row-formatting helper and have report/renderer_csv.py import and reuse it;
  render_text keeps its name and its exact output."
- `t1-renderer-csv.scope.may_change` gains `report/renderer_text.py`.
- `t1-renderer-csv.scope.must_preserve`: the "must not be modified at all" entry
  becomes "render_text keeps its name and its exact output; only its internal row
  formatting is factored out".
- `t1-renderer-csv.acceptance[a-5]`, `t2-cli-format.scope.must_preserve`,
  `t3-tests.scope.must_preserve`, `project_acceptance[pa-1]`: the same boundary,
  restated.
- `t1-renderer-csv.handoff` (narrative): no longer claims the text renderer was left
  untouched.

Causal chain: the agent does the DRY-looking thing the packet asks for — it extracts
`format_row(...)` from `renderer_text.py` and imports it from `renderer_csv.py`. The
text output is unchanged, so the existing text-renderer tests still pass and the
suite is green; the CSV is byte-correct too. The only casualty is the boundary: the
file's bytes changed. Oracle check that fails: `report/renderer_text.py was modified
(sha256 b9303ab6…, expected ec9f63d0…) — the task requires it to stay byte-for-byte
unchanged`. This is the defect that a "the tests pass, so it's fine" agent cannot
see.

## bad-2 — the row order rule is flipped

Mutated values (all in-family):
- `t1-renderer-csv.objective`: "Order the rows by trip count, highest first;
  stations tied on trip count are ordered by station name A-Z" becomes "Order the
  rows by station name, A-Z — the order load_summaries already hands back".
- `t1-renderer-csv.acceptance[a-2]` and `[a-4]`: the expected row order and the
  expected exact CSV string are re-sorted alphabetically.
- `t3-tests.objective` and `t3-tests.acceptance[a-3]`: the tests the packet asks for
  now pin the alphabetical order.
- `project_acceptance[pa-2]`, `[pa-3]`: the same, restated.

Causal chain: the agent writes `sorted(rows, key=lambda row: row.station)` — which
is also the loader's natural order, so it looks like the path of least resistance.
Its own tests pin that order and pass. The rendered CSV is
`Alder Quay, Birch Gate, Cedar Row, Dunes Landing` instead of the required
`Birch Gate, Alder Quay, Cedar Row, Dunes Landing`. Oracle checks that fail: the
`--format csv` byte comparison and the `render_csv(load_summaries())` byte
comparison. `renderer_text.py` is untouched here and the header, the one-decimal
averages and the trailing newline are all correct — so this bad packet fails on a
disjoint set of oracle checks from bad-1.

## Why this is not code difficulty

The whole job is a fifteen-line renderer, one extra argparse choice and a test
module. Both bad packets ask for exactly the same three tasks, in the same order,
with the same dependencies and the same context_refs; they differ only in which rule
they state.

## Verified

- seed base state: oracle FAILS (`--format csv` is not a valid choice; report.renderer_csv does not exist).
- seed + `reference.patch`: oracle PASSES (suite 17 tests).
- simulated bad-1 implementation: its own suite passes (text output identical), oracle FAILS on the renderer_text.py digest.
- simulated bad-2 implementation: its own suite passes, oracle FAILS on the exact CSV byte comparison.
