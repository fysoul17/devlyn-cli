# 0249 ownership/recovery fixtures — revision 2

Ready for pinned evaluator calibration. Independent review reports SHIP with no
HIGH/MEDIUM findings in the changed lines; the original review's malformed-JSON
finding is closed. No native model CLI, authentication operation, network access,
candidate wording, or native repair outcome was used by the fixture author.

## Scope and package format

- OR1 is Folio, a synchronous document editing workspace over a shared JSON file.
  It covers detached snapshots, independent handles/transactions, optimistic
  commits, disjoint rebase, conflict preservation, storage failure/retry, and
  transaction lifecycle. Repair scope: `visible/folio/**`, `visible/checks/**`.
- OR2 is Relay, an asynchronous keyed loader. It covers coalescing, detached
  results, cancellation isolation, invalidation generations, stale completions,
  failure/backend-cancellation retry, and shutdown ownership/cleanup. Repair
  scope: `visible/relay/**`, `visible/checks/**`.

Each `<ID>/` contains `task.json`, `visible/`, a complete replacement `gold/`,
`hidden/oracle.py`, `GOLD.md`, and `contract-map.json`. Every hidden manifestation
maps to exact visible contract quotations and line numbers. Public consumer
examples and normal two-test smoke suites are included. Gold differs from visible
only in `folio/workspace.py` or `relay/loader.py`; storage is shared substrate.

## Revision 2 change and retained revision 1

Before editing, all 142 existing fixture-subtree files were copied to
`history/v1/`. `history/v1-snapshot.json` records every retained hash. The original
manifest SHA-256 remains
`d398372f7da50144c285281a1572417fc58ca0affd96f8a1d198d74866303c38`;
all 38 originally sealed package files and all 142 retained files were reverified.
Original reports, predictions, controls, sources, and raw calibration remain
unchanged. Canonical `OR1/`, `OR2/`, `fixture-manifest.json`, and `REPORT.md` now
represent revision 2; explicit `fixture-manifest-v2.json` and `REPORT-v2.md` are
identical copies of the current manifest/report.

The only changed sealed files are OR1 visible/gold `folio/storage.py` and
`hidden/oracle.py`. `json.loads` now uses a named `parse_constant` callback that
raises ValueError for NaN, Infinity, and -Infinity literals; the existing boundary
normalizes that to StorageError. The existing malformed-file oracle row checks
public read/refresh rejection, unchanged bytes and prior view, valid-file repair,
and a subsequent no-edit commit. No new manifestation, numeric magnitude policy,
contract clause, or private fault injection was introduced. Exact changes are in
`calibration/v2/source-diff.patch`.

The independent recheck is `../results/fixture-review-v2.md`; it reports SHIP,
M1 closed, and zero HIGH/MEDIUM changed-line findings. Its separate public probe
also verifies that quoted constant strings and ordinary finite nested values work.
Its start/end hashes match the current seal. This is a bounded review, not a
claim of exhaustive numeric representation coverage.

## Calibration and evidence

| Task | Baseline public | Baseline oracle | Gold public | Gold oracle | Fault oracle |
| --- | --- | --- | --- | --- | --- |
| OR1 | 2/2 | 2/10 | 2/2 | 10/10 | 9/10 |
| OR2 | 2/2 | 3/12 | 2/2 | 12/12 | 10/12 |

All fault public checks pass 2/2. OR1 fault retains the `put` argument and fails
only `recursive-ownership-boundaries`. OR2 fault drops the success-publication
generation guard and fails only `stale-success-keeps-new-flight` and
`out-of-order-generations`. All outcomes match prospective predictions.

Current raw evidence is `calibration/v2/`: `prediction.json`, `summary.json`, 12
public/oracle records with exact commands, cwd, timestamps, stdout/stderr, source
hashes and before/after checks; `constants-before.json`, two after-fix constant
records, and `fixture-verification.json`. Final fault trees are
`calibration/v2/controls/OR1` and `OR2`. Commands:

```
python3 -B calibrate.py --output calibration/v2
python3 -B calibration/v2/constant_probe.py OR1/visible
python3 -B calibration/v2/constant_probe.py OR1/gold
python3 -B verify_fixtures.py
```

Calibration refuses to overwrite previous controls/results. Earlier stages remain
at `calibration/` and `calibration/final/`, and are also in the v1 snapshot. Gold
consumer checks and the earlier UTF-8/concurrent-close predictions and evidence
remain there; this revision does not relabel those results as new runs.

## Evaluator semantics and limitations

Oracle invocation is `hidden/oracle.py <visible-root>`. Valid source outcomes
always exit 0 with the full `manifestations: [{id, passed, detail?}]` list.
Public unittest checks retain ordinary 0/1 exit codes. This matches the parent's
revised convention and the actual 0237/0222 parser: nonzero oracle exits discard
JSON and may appear as aggregate FAIL. Operators must inspect raw exit status and
stderr to distinguish apparatus failure; aggregate FAIL alone is insufficient.

Faults occur only at supported public boundaries. OR1's adapter implements
read/compare-and-swap and rejects before commit or performs a competing public
commit. OR2 uses public asyncio futures/events owned by its fake backend. No
private product state or storage internals are inspected; evaluated trees stay
unchanged. Event barriers determine ordering; three-second async watchdogs detect
deadlocks, not successful latency. Gold and controls use fresh interpreters.

Folio is scoped to serialized calls in one process, without cross-process locking
or power-loss guarantees. Relay uses one event loop and cooperative cancellation.
These are finite behavioral fixtures, not an empirical claim about native repair
difficulty or exhaustive conformance. Abandoned-failure logging is handled in gold
but is not tested using garbage-collection timing. Pinned evaluator admission and
all native comparisons remain outside this author's completed work.

## Seal

`fixture-manifest-v2.json` seals all 38 package files and includes exact
visible-prefix `runner_source_sha256` dictionaries. SHA-256:
`d246a3212afb190b4a3dc608fd3e6797ebe571c5362bf91da970088ac83f895a`.

The changed storage module SHA-256 (visible and gold) is
`69f1a876669f78a3f394f028e89de2c3f8f59a1d6aa0bb8dedf8c9c415da9b5d`;
OR1 oracle SHA-256 is
`616987477897d0234e78c7749879ba2ba039eca0524498042fd763cbe4d0678c`.
