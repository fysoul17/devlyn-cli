# EQ3-MI1 / EQ3-AF1 contract audit

Read-only audit, 2026-10-10. Inspected both complete visible trees, task goals,
hidden predicates, gold/symptom patches and retained calibration records. No
participant outcomes were inspected, and no fixture or runner files changed.
Paths below are relative to `benchmark/executor-quality/tasks-0102/`.

**Conclusion:** AF1 has visible provenance for its hidden outcomes and is usable
as a diagnostic subject to predicate integrity checks. MI1's rejection semantics
are plausible, but two local representation requirements are insufficiently
explicit for robust binary admission. No newly invented persisted field was
found in either task. Retiring an ambiguous task preserves the evidence better
than changing its expectations after observing participant outputs.

## Predicate provenance

| Task / hidden predicate | Visible basis and limits |
| --- | --- |
| MI1 `local-a`, exact `local_result is False` (`hidden/oracle.py:42`) | `visible/checks/run_checks.py:20` requires falsiness; the original successful intake returns `True` at `visible/clerk/amendment_intake.py:22`. A boolean rejection is natural, but exact identity with `False` is narrower than the explicit public requirement. |
| MI1 `local-b`, rejected status and trail (`hidden/oracle.py:43`) | `visible/checks/continuance_rollback_test.py:17` explicitly requires the `rejected` trail entry. The `status` field exists (`visible/clerk/amendment_intake.py:9`) and accepted intake sets it to `accepted` (line 20). Setting it to `rejected` is semantically plausible, but that exact status is not expressly required by another visible assertion or consumer. |
| MI1 `remote-a`, sufficient notice (`hidden/oracle.py:44`) | Direct public assertion at `visible/checks/run_checks.py:21`; latest-filing calculation at `visible/calendar/hearing_scheduler.py:7–11`. |
| MI1 `remote-b`, continuance rollback (`hidden/oracle.py:45`) | Calls the visible regression `visible/checks/continuance_rollback_test.py:6–18`, which checks rejection, restored hearing date, preserved filings and activity trail. |
| MI1 `restore` (`hidden/oracle.py:46`) | Combines the same visible rejection, notice and filing-preservation requirements. |
| AF1 `local-a/b`, reserved unit and held/linked order (`hidden/oracle.py:49–50`) | Exact public assertions at `visible/qa/run_checks.py:14–15`. |
| AF1 `remote-a`, wrong pass retains hold and matching pass releases it (`hidden/oracle.py:52–54`) | `visible/intake/hold_intake.py:4,32–38` defines the reconciliation pass and records pass-specific events. `visible/matching/crossmatch_reserver.py:4–18` defines linked holds. Pass isolation is inferred from this interface; it is not a separate explicit prose assertion. |
| AF1 `remote-b`, order ready for matching (`hidden/oracle.py:56`) | Exact visible predicate at `visible/qa/expiry_release.py:4–8`, supported by the expiry-review contract comment at line 22. |
| AF1 `restore`, ready again and quarantined exactly once (`hidden/oracle.py:58–61`) | `visible/qa/expiry_release.py:11–19` explicitly defines one isolation entry, the quarantine-ledger tuple and quarantined unit state; matching readiness and absence of holds use the visible consumers above. |

AF1's expiry path exceeds the ticket's immediate intake symptom, but its visible
regression helpers and contract comment supply that repository invariant. A
missing invocation in the public smoke test does not make the requirement hidden.
MI1's weaker local provenance should likewise not be confused with a demonstrated
contradiction: it is an admission ambiguity, not proof that rejection status is
wrong.

## Calibration and required source integrity audit

`results/calibration-raw.json` records validator exit 0 for both tasks. The
validator (`benchmark/executor-quality/scripts/validate-discovery-task.py:432–438`)
requires gold `TTTTT`, symptom `TTFFF`, and local failures for pristine/noop.
These controls establish discrimination among supplied patches; they do not
prove that every assertion is justified by the participant contract.

MI1's symptom patch rejects after appending a filing; gold rejects before the
append. The visible notice and rollback checks explain that distinction. AF1's
symptom patch records the hold; gold additionally implements reconciliation.

Both hidden oracles execute predicates from the submitted visible tree:

- MI1 loads `checks/continuance_rollback_test.py` and calls
  `continuance_rollback_holds`; it also calls the submitted notice consumer.
- AF1 loads `qa/expiry_release.py` and calls `ready_for_match` and
  `isolated_once`; it also calls the submitted holding consumer.

The registered `visible/**` edit scope permits changes to those files. Before
using a pass as evidence, compare their evaluated snapshot bytes and diffs with
the frozen source hashes. Unchanged predicates retain the audited meaning.
Changed predicates need independent inspection for equivalent or stronger
semantics; a changed hash alone is not failure. A weakened or unresolved predicate
cannot certify its own result: mark the affected outcome unadjudicated rather
than count it as a pass. Do not retrofit expectations against observed outputs.
