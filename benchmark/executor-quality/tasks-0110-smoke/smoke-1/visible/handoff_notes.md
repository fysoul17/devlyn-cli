# Evening handoff notes

Control ID: **HAND-62**

Recorded finding: **cancelled intake D-16 remains excluded from the approved total**.

These notes are the shift lead's plain-language counterpart to the allocation,
capacity, exception, and reconciliation records. They describe why the report
must stay focused on the supplied record state instead of broad operational
activity.

## Timeline

- 16:00 — The evening desk received the sample dispatch batch and confirmed
  that it contains four records. The objective is to report only approved
  amounts, not all submitted amounts.
- 16:15 — The desk compared the sample with allocation work. D-14 is approved
  for eight units; D-17 is approved for four units. Those are the only values
  eligible for the report.
- 16:30 — D-15 remained pending. Its five units may need a later operator
  action, but there is no approved state and therefore no reporting authority.
- 16:45 — D-16 remained cancelled. Its three units are retained in the source
  history for auditability, while its amount stays outside the approved total.
- 17:00 — Route capacity was checked without changing record classifications.
  A capacity reservation is logistical evidence, not a replacement for the
  explicit approved state used by the calculation.
- 17:15 — The exception desk confirmed that visible warnings do not require a
  summary to speculate about future approvals. The summary should explain the
  current correction and report the current approved amount.
- 17:30 — The report preview showed twelve units after filtering. The desk
  recorded the preview for reconciliation and prepared the operator summary.
- 17:45 — The shift lead requested a file inventory in the summary so the next
  operator can verify that all fixture material was considered.
- 18:00 — The hold checkpoint began. Pending and cancelled records continued
  to appear in operational notes, but neither classification may add value to
  the approved report.
- 18:15 — The allocation review released unrelated queued dispatch work. That
  release must not change the four-record calculation used by this fixture.
- 18:30 — Capacity logged three reserve slots after route D-17. This supports
  the handoff but it is not an arithmetic input to `approved_total`.
- 18:45 — The exception register reiterated that D-15 needs no approval action
  until its state changes. The planned code correction therefore belongs in
  the approved filter, not in a manual adjustment to the summary.
- 19:00 — The lead restated the permanent point of control: cancelled intake
  D-16 remains excluded from the approved total. The next shift must preserve
  that exclusion even though the row remains visible in the sample data.
- 19:15 — Reconciliation completed against the intended twelve-unit total.
  The final summary needs to identify all visible files and the findings from
  each operational record, allowing the desk to reconstruct this timeline.

## Summary guidance

The operator-facing summary is not a replacement ledger. Keep it concise, but
name each visible fixture file so a reviewer knows the underlying record set.
For the five operational files, include the exact control ID and recorded
finding. For the code correction, explain that the function must sum amounts
only when the record state is `approved`, producing twelve for the provided
sample. Do not claim that pending or cancelled work is approved simply because
it appears in the same handoff packet.

## Cross-record observations

1. `allocation_review.md` confirms that the hold process is operational. Its
   queue release is not evidence that an unapproved source row should affect
   the report.
2. `capacity_window.log` confirms there are three reserve slots after D-17.
   Capacity is useful for dispatch planning but does not grant approval status.
3. `exception_register.md` marks D-15 as pending and D-16 as cancelled. These
   facts explain why they remain present in the packet while absent from total.
4. `reconciliation_ledger.md` lays out the calculation as eight plus four. It
   also documents that source rows must not be deleted merely to make a total
   appear correct.
5. `README.md` describes the approved-only rule in compact form; this note
   provides the longer narrative needed for an operator handoff.
6. `records.py` is the defect location. Its function should decide whether a
   record counts by reading the record's state before adding the amount.
7. `report.py` calls the calculation over the supplied JSON. It is a useful
   local check, but it is not the place to paper over a bad total.
8. `sample_records.json` is the source fixture. It deliberately contains one
   pending and one cancelled record so a broad sum gives the wrong result.
9. A summary that merely states twelve without explaining the filter is not a
   complete handoff because it offers no evidence that the classification was
   understood.
10. A summary that changes state labels instead of the calculation is also not
   complete because it would conceal rather than correct the original defect.
11. Future dispatch batches may contain more than four records. The code must
   filter every input row by state instead of using a fixed amount or IDs.
12. The required file inventory gives the next shift a review path: it can
   trace the summary from the small source data through each operational note.

## Closing instruction

When the correction is complete, write the summary in ordinary operator
language. Say that approved records total twelve units, identify the source
files and the five control findings, and retain the distinction between a
record that is present in the handoff packet and a record eligible for the
approved dispatch report. That distinction is the entire purpose of this smoke
fixture's seeded defect.

## Review prompts for the incoming shift

1. Which field in `sample_records.json` determines whether an amount is in the
   report? Confirm that it is the explicit state, not the presence of a route,
   a scan, a reviewer, an exception note, or a capacity reservation.
2. Which supplied values should remain visible but excluded? Identify D-15's
   pending five units and D-16's cancelled three units, then verify that the
   corrected function does not include either in an approved-only total.
3. Which supplied values should be included? Identify D-14's eight units and
   D-17's four units, then verify that the outcome is twelve rather than the
   broad sum of all four source amounts.
4. Which documents give operational context? Trace ALLOC-47, CAP-31, EXC-88,
   HAND-62, and RECON-53. Their findings must be represented in the summary,
   but they must not introduce a second inclusion rule in the implementation.
5. What should happen when a future input row changes? The code should respond
   through the same state test, which is why a general filter is required in
   `records.py` rather than a hard-coded amount, a list of approved IDs, or a
   manual correction in `report.py`.

An incoming reviewer can use these prompts as a compact audit: read the source
file names named in the summary, check that the control findings match the
operational records, and run the local oracle. The desired result is a small,
general code repair with a complete evidence-bearing handoff, not a broader
refactor of the fixture or a changed source dataset.
