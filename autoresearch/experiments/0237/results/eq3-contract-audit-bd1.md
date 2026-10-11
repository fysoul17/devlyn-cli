# EQ3-BD1 contract audit

2026-10-10. Read-only audit of the existing fixture; no model calls, fixture edits,
participant-output inspection or historical regrading. Root requested this audit
after finding a provenance problem in another EQ3 task.

## Finding

**The `local-b` oracle row contains an unsupported acceptance requirement:**
`len(second["bumped"]) == 1`. The list exists in the visible initial manifest,
but no visible consumer reads it and no visible contract requires populating it.
A consistent, repeat-safe implementation can satisfy the stated goal and both
visible contract fragments while leaving this unused list empty. Therefore this
clause cannot reliably distinguish incomplete work from a valid implementation.

Base paths below are relative to
`benchmark/executor-quality/tasks-0102/EQ3-BD1/`.

## Assertion provenance

The owner receives `task.json`'s `goal` plus `visible/`, not its hidden `invariant`
or contract-binding metadata. The goal asks for consistent overweight check-in
and a gate close that can be repeated safely.

| Hidden assertion (`hidden/oracle.py`) | Visible provenance | Assessment |
| --- | --- | --- |
| L24: the vehicle has state `bumped` | `visible/stowage/deck_load_balancer.py:13` selects bumped records; the goal identifies an overweight vehicle removed from the current sailing. | Supported by a real consumer. |
| L25: fare charged exactly once | `visible/verification/bumped_vehicle_test.py:14–15` explicitly computes exactly one receipt; the goal requires repeat safety. | Supported. |
| L25: `len(second["bumped"]) == 1` | Only initialization at `visible/gate/vehicle_checkin.py:13`, as an empty list. Full `visible/` inspection found no reader or statement defining its required population. | Unsupported as a mandatory acceptance clause. A field name alone is not sufficient provenance. |
| L26: recomputed reserve equals the vehicle's booking units | `visible/stowage/deck_load_balancer.py:4–5,8–16` specifies recomputation from recorded bumped-vehicle weight classes; `visible/gate/vehicle_checkin.py:8,15` supplies overweight class and a three-unit booking. | Supported for this fixture's unchanged booking. |
| L27: position retained in the next sailing | Explicit contract and executable helper at `visible/verification/bumped_vehicle_test.py:4,7–11`; original slot is 1 at `visible/gate/vehicle_checkin.py:8`. | Supported. |
| L28: `restore` conjunction | Repeats reserve, position and fare predicates above. | Its component requirements are supported, but it does not inject a failure or test a restoration operation. It is not an independent recovery scenario. |

The five entries in `hidden/manifests.json` repeat the same two contract quotes.
Neither quote supplies the missing `bumped`-list obligation.

## Counterexample

Prediction, recorded to root before the experiment: an implementation retaining
the recorded weight class, moving the truck out of the current sailing to its
original next-sailing position, charging once and making repeats no-ops will
satisfy the visible contracts but fail `local-b` if it leaves the unused list
empty.

The following alternative was executed **in memory only**, loading the original
`open_manifest`, reserve consumer and regression helpers from their visible
files. No original or participant file was changed.

```python
def close_gate(manifest, vehicle_id):
    record = manifest["vehicles"][vehicle_id]
    if record["state"] != "queued":
        return manifest
    if record["weight_class"] == "overweight":
        record["state"] = "bumped"
        manifest["current_sailing"].remove(vehicle_id)
        manifest["next_sailing"].insert(record["queue_slot"], vehicle_id)
        manifest["fare_ledger"].append(vehicle_id)
    else:
        record["state"] = "boarded"
    return manifest
```

Actual output from the read-only Python probe:

```text
Public scenario: {'state': 'bumped', 'report': {'reserve_units': 3}}
Visible contracts: {'position_kept': True, 'fare_once': True, 'removed_from_current': True, 'repeat_unchanged': True, 'recorded_weight_class': 'overweight'}
Exact hidden row predicates: {'local-a': True, 'local-b': False, 'remote-a': True, 'remote-b': True, 'restore': True}
Unused list: []
```

`repeat_unchanged` compares a deep copy of the first result with the second
result. Hidden predicates were evaluated verbatim in the probe using the loaded
visible functions; the original oracle file was not changed or executed against
a modified disk fixture.

## Other coverage limits

- `first` and `second` can alias because the API mutates the manifest. The
  `local-a` assertion runs after both calls, so it does not independently prove
  correct state immediately after the first call.
- The public runner at `visible/verification/run_checks.py:19–21` prints a
  scenario; it has no assertion and does not itself invoke the position or fare
  helper. A successful public process alone cannot establish completion.
- Reserve comparison uses the returned manifest's mutable booking value,
  rather than an independent original-value witness.

## Consequence

Preserve all raw observations and the existing frozen fixture. Do not interpret
failure of the unsupported clause alone as a demonstrated source-quality loss,
and do not silently remove it from an in-progress or historical decision rule.
A future corrected fixture needs an explicit visible obligation or a revised
oracle that accepts the visible-contract counterexample, then fresh calibration,
registration and measurement. This audit does not admit any candidate.
