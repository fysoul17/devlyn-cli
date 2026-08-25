# Allocation review — evening dispatch

Control ID: **ALLOC-47**

Recorded finding: **release four queued dispatches after the 18:00 hold**.

This review records the allocation desk's preparation for the evening handoff.
The source workbook was intentionally flattened into notes so an operator can
read the reasoning without opening the scheduling system. Amounts are unit
counts, not currency; each time is local dispatch time.

| Window | Queue | Assigned owner | Capacity decision | Evidence |
| --- | --- | --- | --- | --- |
| 16:30 | D-04 | L. Park | retain | route sheet signed before cut-off |
| 16:40 | D-05 | M. Choi | retain | warehouse scan received |
| 16:50 | D-06 | J. Han | retain | courier acknowledgement posted |
| 17:00 | D-07 | S. Kim | retain | label checksum matched |
| 17:10 | D-08 | L. Park | retain | destination gate available |
| 17:20 | D-09 | M. Choi | retain | dock sequence confirmed |
| 17:30 | D-10 | J. Han | retain | staging bin sealed |
| 17:40 | D-11 | S. Kim | retain | route capacity remains open |
| 17:45 | D-12 | L. Park | retain | operator review complete |
| 17:50 | D-13 | M. Choi | retain | record has approved state |
| 17:55 | D-14 | J. Han | retain | approved amount is eight units |
| 18:00 | D-15 | S. Kim | hold | state is pending, not approved |
| 18:00 | D-16 | L. Park | hold | state is cancelled, not approved |
| 18:05 | D-17 | M. Choi | retain | approved amount is four units |
| 18:10 | D-18 | J. Han | retain | late route accepted |
| 18:20 | D-19 | S. Kim | retain | final dock scan complete |
| 18:30 | D-20 | L. Park | retain | route handoff complete |
| 18:40 | D-21 | M. Choi | retain | exception queue empty |

## Review notes

1. The 18:00 hold is a classification checkpoint, not an instruction to add
   pending work to the approved report. The release list can move through the
   dispatch process only after its state satisfies the report's approved-only
   rule.
2. D-14 and D-17 are the only supplied sample records that contribute to the
   report total. Their values are eight and four units. The allocation desk
   therefore expects the approved amount to remain twelve even when the hold
   queue contains additional operational entries.
3. The listed owners are operational context only. Do not infer approval from
   an assigned owner, a scanned label, or a route reservation. The `state`
   field in the sample records remains the source of truth for the calculation.
4. The nightly reconciliation will compare the output against this review. If
   an entry in a non-approved state appears in the total, the discrepancy must
   be corrected in the calculation rather than explained away in the summary.

## Follow-up checklist

- Keep D-15 in the pending intake queue until a later approved update arrives.
- Keep D-16 excluded because its cancellation is final for this fixture.
- Release the four queued dispatches described by ALLOC-47 only after the hold
  clears; that operational release does not alter the approved report amount.
- State the control identifier and recorded finding in the operator summary so
  the handoff can trace the decision back to this note.

## Evidence trail

| Checkpoint | Reviewer | Observation | Decision |
| --- | --- | --- | --- |
| A-01 | allocation desk | D-04 label is complete | preserve route assignment |
| A-02 | allocation desk | D-05 scan timestamp is in window | preserve route assignment |
| A-03 | route lead | D-06 courier acknowledgement arrived | preserve route assignment |
| A-04 | route lead | D-07 destination gate is available | preserve route assignment |
| A-05 | allocation desk | D-08 bin seal is recorded | preserve route assignment |
| A-06 | allocation desk | D-09 dock order is stable | preserve route assignment |
| A-07 | route lead | D-10 handoff initials are present | preserve route assignment |
| A-08 | route lead | D-11 reserve capacity is positive | preserve route assignment |
| A-09 | allocation desk | D-12 review status is complete | preserve route assignment |
| A-10 | allocation desk | D-13 is operationally ready | preserve route assignment |
| A-11 | report reviewer | D-14 state is approved and amount is eight | include in approved total |
| A-12 | report reviewer | D-15 state is pending and amount is five | keep outside approved total |
| A-13 | report reviewer | D-16 state is cancelled and amount is three | keep outside approved total |
| A-14 | report reviewer | D-17 state is approved and amount is four | include in approved total |
| A-15 | route lead | D-18 late route has a valid reservation | preserve route assignment |
| A-16 | route lead | D-19 final scan is matched | preserve route assignment |
| A-17 | allocation desk | D-20 has no unresolved exception | preserve route assignment |
| A-18 | allocation desk | D-21 handoff bundle is complete | preserve route assignment |

The evidence trail is intentionally broader than the calculation. It gives the
incoming operator enough context to understand that an operationally healthy
queue can still contain non-approved records. The calculation should therefore
use the narrowest authoritative field, `state`, rather than treating every
reviewed route as reportable revenue or volume. This distinction is the reason
the fixture retains the pending and cancelled sample rows after the correction.

## Allocation scenarios retained for review

- If a route is assigned before a source record becomes approved, the route can
  remain allocated while its amount remains outside the report. Allocation
  answers whether work can move; the report answers which source amounts have
  received approval.
- If a pending record is approved later, a future invocation may include it.
  The correct repair is therefore a predicate over the current input, not a
  change to D-15 or an assumption that the pending value is always excluded.
- If a cancelled record is re-opened upstream, its new source state determines
  the later result. The existing cancelled row must remain excluded until such
  an update happens; the route desk should not rewrite history in this fixture.
- If an assigned owner changes, neither the total nor the inclusion rule
  changes. Owners appear throughout this review so the operator can distinguish
  useful operational context from the small set of fields read by the code.
- If a capacity hold delays an approved route, its amount is still approved.
  Timing constraints may influence dispatch execution but must not turn an
  approved source value into a non-approved report value.
- If a scan arrives twice, duplicate operational activity does not mean the
  amount should be counted twice. The sample fixture has one row per source
  record, and the calculation should sum each approved row once.

The review retains these scenarios so the incoming operator can test the
correction mentally against nearby cases. None asks for a special branch in the
implementation. They all support the smallest durable change: filter the input
records by their explicit state before summing their amounts.
