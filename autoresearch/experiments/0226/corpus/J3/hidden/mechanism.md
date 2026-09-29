# J3 mechanism record

## Mandatory clause

The following is the requirement text reserved for `spec.md`:

> Rolling back a validation attempt must remove every artifact path collected during that attempt while preserving all artifact paths that existed at its start, including paths stored under an artifact id reused inside the attempt.

## Trigger

An artifact ID already has a retained path before a snapshot. A descendant in the speculative attempt appends another path to that same ID, then a later validation failure restores the snapshot.

## Causal code path

lib/validator.js → Mainstay.snapshot() stores artifact map → internals.finalize() calls artifacts.get(id).push(state.path) → lib/types/alternatives.js restores a losing localState → Mainstay.restore() reassigns the saved artifact map. The saved map must own its accumulated path lists.

## Incorrect behavior

The twin copies the Map but reuses each paths array. The speculative push therefore changes both live and saved maps' value. Restoring map membership drops new IDs, but cannot remove a path appended under an existing ID. J3-W leaves ['b', 'x'] beside the valid ['a'] even though the first b alternative was discarded.

## Executable witness

**J3-W**, defined with executable setup, action, and assertions in `hidden/oracle.md`. All other rows must pass on both variants.

## Near-miss exclusions

- Keeping paths from committed successful alternatives, including shared IDs, is required behavior.
- Keeping an object-valued artifact ID by identity is required; recursively cloning IDs is a different error.
- Dropping only brand-new artifact IDs correctly does not establish correct restoration of prior lists.
- Externally queued methods, warnings, and shadow state are separate bookkeeping mechanisms and should remain unchanged.
- Artifacts from an ordinary root validation failure with no existing restore operation are outside this request's transaction scope.
- A full map reset that loses earlier valid siblings is another defect, not the shallow-list snapshot mechanism.

## Public-check separation

The public tests and reference implementation sketch in `hidden/implementation.md` run the affected code while leaving this particular data interaction unasserted. Keep the public tests identical in the reference and twin, retain the 100% coverage threshold, and change only the specified mechanism. Do not add any hidden-oracle command to `spec.expected.json`.
