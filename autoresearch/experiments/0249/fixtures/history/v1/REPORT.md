# 0249 original ownership and recovery fixtures

Ready for independent review and pinned evaluator calibration. No native model
CLI, authentication operation, network access, candidate wording, or native
repair outcome was used. Work is confined to this fixtures subtree.

## Packages

- `OR1/task.json`: Folio transactional document workspace. Public contracts cover
  recursive snapshot ownership, independently opened workspaces and transactions,
  optimistic commit, disjoint rebase, conflict preservation, storage failure and
  retry, and transaction closure. Product modules are `visible/folio/*.py`;
  permitted repair scope is `visible/folio/**` and `visible/checks/**`.
- `OR2/task.json`: Relay async keyed loader. Public contracts cover coalescing,
  detached values, independent caller cancellation, invalidation generations,
  stale completion isolation, retry after error/backend cancellation, and shutdown
  ownership including retired operations and concurrent cleanup. Repair scope is
  `visible/relay/**` and `visible/checks/**`.

Each package contains a normal repair request, visible documentation, an ordinary
consumer example, a two-test public smoke suite, a full replacement `gold/` tree,
`hidden/oracle.py`, and `contract-map.json`. Each manifestation has exact visible
contract quotations and line numbers. Gold differs only in `folio/workspace.py`
or `relay/loader.py`; `GOLD.md` records this mapping.

## Final calibration

| Task | Baseline public | Baseline oracle | Gold public | Gold oracle | Fault control |
| --- | --- | --- | --- | --- | --- |
| OR1 | 2/2 | 2/10 | 2/2 | 10/10 | 9/10 |
| OR2 | 2/2 | 3/12 | 2/2 | 12/12 | 10/12 |

The OR1 fault retains the supplied `put` object; only
`recursive-ownership-boundaries` fails. The OR2 fault drops the successful-load
generation publication guard; only `stale-success-keeps-new-flight` and
`out-of-order-generations` fail. All fault smoke checks still pass. Final outcomes
match the predictions recorded before execution.

Final evidence is in `calibration/final/`: `prediction.json`, `summary.json`,
12 raw public/oracle records containing exact command, cwd, timestamps, stdout,
stderr, input hashes and before/after source checks, gold consumer records,
`edge-after.json`, and `fixture-verification.json`. Commands:

```
python3 -B calibrate.py --output calibration/final
python3 -B calibration/edge_probe.py
python3 -B calibration/consumer_check.py OR1/gold
python3 -B calibration/consumer_check.py OR2/gold
python3 -B verify_fixtures.py
```

`calibrate.py` refuses to replace existing records/controls; use a new output
directory with a prospectively written prediction if a further revision is
approved. Final control trees are `calibration/final/controls/OR1` and `OR2`.

Initial calibration remains at `calibration/` and is not relabeled as final.
The final audit independently predicted and reproduced two contract violations:
invalid UTF-8 escaped as UnicodeDecodeError, and concurrent close interrupted
async cleanup. `edge-prediction.json` and `edge-before.json` retain this evidence.
The shared FileStore error boundary and gold shutdown were corrected and the
existing corresponding oracle rows strengthened. Original full source bytes
were retained in the first fault trees; `calibration/initial-sources/` contains
baseline/gold reconstructions verified against every initial source hash, with
explicit reconstruction provenance. No initial raw result was overwritten.

## Evaluator interface

`hidden/oracle.py <visible-root>` prints one JSON object containing the full
`manifestations: [{id, passed, detail?}]` list. A valid verdict exits 0 even when
some rows fail. This follows the parent's revised instruction and the actual
0237 Runner.evaluate / 0222 check.last_json parser: any nonzero exit discards JSON
and produces aggregate failure. Nonzero exit therefore denotes an oracle or
apparatus failure. Public checks use normal 0/1 success/failure exit codes and
print their own JSON summary after standard unittest output.

The OR1 backend fake implements the documented `read`/`compare_and_swap` protocol
and injects only public pre-commit failures or a competing public commit. OR2
fakes own public futures and events. Oracles never inspect product internals,
patch evaluated source, use private SQL/storage details, consult process-global
state, or require elapsed-time races. Async three-second watchdogs detect a stuck
scenario; success ordering comes from event barriers and explicitly settled
futures. Each source tree's hashes are verified unchanged across evaluation.

## Limits and seal

These are compact behavioral repair fixtures, not an empirical claim about
native repair difficulty. Independent review and the pinned production evaluator
remain with the root/integration agents. Folio deliberately supports serialized
calls in one process, not cross-process locking or crash/power-loss guarantees.
Relay supports one asyncio loop and cooperative cancellation. Finite oracle
coverage is not exhaustive; for example abandoned-failure event-loop reporting is
specified and handled by gold but not asserted through garbage-collection timing.
No old CF behavior assertion or implementation was copied; existing fixtures
and evaluator code were inspected only to understand packaging and verdict shape.

`fixture-manifest.json` seals all 38 package files with per-file SHA-256 hashes
and supplies the exact visible-prefix `runner_source_sha256` dictionaries.
Manifest SHA-256: `d398372f7da50144c285281a1572417fc58ca0affd96f8a1d198d74866303c38`.
