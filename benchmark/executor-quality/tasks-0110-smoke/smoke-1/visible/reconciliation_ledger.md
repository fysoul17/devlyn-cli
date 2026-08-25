# Reconciliation ledger — dispatch report

Control ID: **RECON-53**

Recorded finding: **approved dispatch amount reconciles to 12 units**.

The ledger documents the arithmetic review used by the evening shift. It is
synthetic operational material, but it follows the same separation as the
production process: source entries remain visible, while the approved report
uses only entries whose state is approved.

| Ledger line | Source reference | State | Amount | Report treatment | Review note |
| --- | --- | --- | ---: | --- | --- |
| RL-001 | D-01 | archived | 0 | omit | historical reference only |
| RL-002 | D-02 | archived | 0 | omit | historical reference only |
| RL-003 | D-03 | archived | 0 | omit | historical reference only |
| RL-004 | D-04 | archived | 0 | omit | route record only |
| RL-005 | D-05 | archived | 0 | omit | route record only |
| RL-006 | D-06 | archived | 0 | omit | route record only |
| RL-007 | D-07 | archived | 0 | omit | route record only |
| RL-008 | D-08 | archived | 0 | omit | capacity record only |
| RL-009 | D-09 | archived | 0 | omit | capacity record only |
| RL-010 | D-10 | archived | 0 | omit | capacity record only |
| RL-011 | D-11 | archived | 0 | omit | handoff record only |
| RL-012 | D-12 | archived | 0 | omit | handoff record only |
| RL-013 | D-13 | archived | 0 | omit | handoff record only |
| RL-014 | D-14 | approved | 8 | include | first approved sample row |
| RL-015 | D-15 | pending | 5 | omit | waiting for state change |
| RL-016 | D-16 | cancelled | 3 | omit | cancellation is final here |
| RL-017 | D-17 | approved | 4 | include | second approved sample row |
| RL-018 | D-18 | archived | 0 | omit | route record only |
| RL-019 | D-19 | archived | 0 | omit | route record only |
| RL-020 | D-20 | archived | 0 | omit | route record only |
| RL-021 | D-21 | archived | 0 | omit | route record only |
| RL-022 | D-22 | archived | 0 | omit | route record only |
| RL-023 | D-23 | archived | 0 | omit | route record only |
| RL-024 | D-24 | archived | 0 | omit | route record only |
| RL-025 | D-25 | archived | 0 | omit | route record only |
| RL-026 | D-26 | archived | 0 | omit | route record only |
| RL-027 | D-27 | archived | 0 | omit | route record only |
| RL-028 | D-28 | archived | 0 | omit | route record only |
| RL-029 | D-29 | archived | 0 | omit | route record only |
| RL-030 | D-30 | archived | 0 | omit | route record only |

## Reconciliation method

1. Read the source record state before considering its amount.
2. Include the amount only for an approved record.
3. Preserve pending and cancelled lines in the ledger as evidence, but exclude
   them from the report arithmetic.
4. Compare the included values: eight units from D-14 plus four units from
   D-17 yields the twelve-unit approved dispatch amount.
5. Record the outcome under RECON-53 so the shift handoff can confirm that the
   implementation and narrative summary agree.

The result is intentionally modest: a correction to a single calculation and
a summary that makes the source reasoning inspectable. It must not be replaced
with a hard-coded twelve, because future source data needs the same approved
state filter to produce its own correct total.

## Supporting review trail

| Review step | Source consulted | Result | Why it matters |
| --- | --- | --- | --- |
| R-01 | README.md | approved-only rule found | establishes task intent |
| R-02 | records.py | broad sum found | identifies seeded defect |
| R-03 | sample_records.json | D-14 approved for 8 | first included value |
| R-04 | sample_records.json | D-15 pending for 5 | excluded by state |
| R-05 | sample_records.json | D-16 cancelled for 3 | excluded by state |
| R-06 | sample_records.json | D-17 approved for 4 | second included value |
| R-07 | report.py | function output displayed | verifies call path |
| R-08 | allocation_review.md | ALLOC-47 recorded | context is operational |
| R-09 | capacity_window.log | CAP-31 recorded | reserve is not approval |
| R-10 | exception_register.md | EXC-88 recorded | pending requires exclusion |
| R-11 | handoff_notes.md | HAND-62 recorded | cancellation requires exclusion |
| R-12 | this ledger | RECON-53 recorded | eight plus four equals twelve |
| R-13 | source states | two approved rows | general filter must select both |
| R-14 | source states | two non-approved rows | general filter must reject both |
| R-15 | summary.txt | source inventory required | reviewer can retrace inputs |
| R-16 | summary.txt | control findings required | reviewer can retrace context |
| R-17 | hidden oracle | code behavior checked | prevents narrative-only fix |
| R-18 | hidden oracle | empty approved set checked | prevents accidental fallback |

The supporting trail is a review aid, not a second implementation contract. It
shows why the correct program is a simple state predicate. Every line reaches
the same conclusion: include an amount when and only when the source record is
approved. The additional operational material supplies the context required by
the smoke session without broadening the code change beyond that predicate.

## Nearby-case ledger notes

- An approved record that is temporarily held for a route issue still has an
  approved state. Its later operational handling does not change how the
  calculation treats its current amount.
- A pending record with a completed scan still has a pending state. A scan is
  evidence of physical progress, not a substitute for the approval workflow.
- A cancelled record with a historical amount remains a source row for audit.
  Keeping it visible is exactly why the calculation must filter rather than
  assume every listed amount is reportable.
- A record approved after this fixture's snapshot can be included when that
  later source input is processed. The function should inspect the row it is
  given and should not infer a future state from any operational note.
- A record whose owner, route, or destination changes retains the same report
  treatment unless its explicit state also changes. This is the generality that
  the seeded defect lacks when it simply sums every amount.

For the current four rows, the audit arithmetic stays compact: 8 plus 4 is 12;
5 is excluded because pending; and 3 is excluded because cancelled. The larger
ledger context exists so the summary can distinguish the arithmetic source from
the operational surrounding material while still accounting for every file
provided to the smoke task.
