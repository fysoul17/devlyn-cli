# EQ3-UA1 contract audit — 2026-10-10

**Finding: exclude the entire UA1 task from 0237 admission.** Its hidden `local-a` predicate requires a persisted success flag that the participant-visible contract does not require. Preserve every frozen fixture, oracle, raw result and charged attempt. Do not silently convert failures to passes, repair the historical oracle, or rerun until a favorable result appears. This audit does not establish full correctness of any submission or revise historical 0102 results.

This is source and completed-trace inspection, not a new model draw or oracle run. Root separately reported reproducing the unsupported predicate. Only d01–d04 were inspected; d05 was running or finishing and was not opened. The dispatcher was held by root at the next cell boundary.

Paths below use these absolute roots:

- `TASK = /Users/aipalm/.local/share/nx01/0237-harness/benchmark/executor-quality/tasks-0102/EQ3-UA1`
- `RUNS = /Users/aipalm/.local/share/nx01/0237-live/out-discovery`
- `EXP = /Users/aipalm/.local/share/nx01/0237-harness/autoresearch/experiments/0237`

## Receipt field versus loan-record field

The delivered request concerns a refused renewal: make the request result and loan record agree **when the request cannot be completed**. `EXP/tasks-discovery-max.json:1564–1565` contains that request and an empty obligations list. The runner copies only `visible/` into the participant tree (`EXP/runner.py:75–85`); hidden metadata is not a participant requirement.

| Evidence | What it requires |
|---|---|
| `TASK/visible/checks/run_checks.py:25–27` | Successful call returns exactly `{"accepted": True, "renewed": True}`; due becomes 34; fee clock stays 10. This is a **returned receipt** assertion. |
| `TASK/visible/checks/run_checks.py:28–32` | Refusal returns both flags false; the record's `renewed` value must not be truthy; due and hold position remain; the fee event is recorded. An absent record key satisfies the explicit refusal assertion. |
| `TASK/visible/loan_desk/renewal_intake.py:7–9` | Original successful behavior updates only `due` and returns `{"accepted": True}`. It does not create a persisted `renewed` key. |
| `TASK/visible/circulation/fee_escalator.py:3–4` | A renewed loan retains its established fee clock. No success-flag requirement. |
| `TASK/visible/checks/hold_expiry_case.py:3–4` | A rejected renewal preserves recorded due and waitlist position. No success-flag requirement. |
| `TASK/hidden/oracle.py:25–32` | Hidden `local-a` additionally requires `bool(normal.get("renewed"))` after a successful renewal. |

All 29 participant-visible files were inspected. None requires persisting a successful-renewal flag or consumes such a flag after success. `TASK/task.json:5` and `hidden/manifests.json:6` describe a refused-renewal invariant; even that hidden description does not supply the missing successful-record requirement. The private gold patch adds the flag (`TASK/patches/gold.patch:10`), but a reference implementation is not a source of participant obligations.

The oracle therefore distinguishes two implementations with the same required returned receipt, due-date update, preserved fee clock and refusal behavior, solely by an additional private representation choice. This is overprescription, not an observed discovery failure.

## Completed submissions and unchanged raw outcomes

Every row below passed its public check and had no recorded scope violation. The table transcribes each cell's existing `checks.json`; it does not regrade them.

| Cell | Frozen oracle result | Submitted behavior and trace evidence |
|---|---|---|
| `d01-EQ3-UA1-claude-A-r1` | `local-a` FAIL; other four PASS | `snapshot/visible/loan_desk/renewal_intake.py:12–17` refuses before changing due, charges refusal, returns the required successful receipt without a record flag. `run/stdout:13` reads all tracked visible files; `final.txt:17–22` reports probes preserving accepted-record behavior; `:27` identifies accepted-fee timing as unpinned. |
| `d02-EQ3-UA1-claude-B-r1` | `local-a` FAIL; other four PASS | Implementation `:7–12` has the same behavior. `run/stdout:21,23` reads all visible files. `final.txt:24` explicitly declines a record flag because it does not exist and only a falsey value on refusal is required. This was considered, not undiscovered. |
| `d03-EQ3-UA1-claude-C-r1` | `local-a` FAIL; other four PASS | Implementation `:7–12` is byte-identical to d02. `run/stdout:11` reads all visible files. `final.txt:17–18,27` explicitly preserves the original accepted record and declines a new flag under No overengineering. This was considered, not undiscovered. |
| `d04-EQ3-UA1-codex-B-r1` | `remote-a` FAIL; other four PASS, including `local-a` | Implementation `:7–13` calls the fee recorder before the hold decision and persists the decision in the loan. `run/stdout:8,11,16–17` reads the relevant contracts and other visible files; `:27` announces one decision for receipt and record. Added checks at `snapshot/visible/checks/run_checks.py:28–29` explicitly assert charging the successful renewal. |

All cell-relative paths in that table are under `RUNS/<cell>/`. Renewal implementation SHA-256 values:

| Cell | SHA-256 |
|---|---|
| d01 | `43d60759339b6a90da11c0412153316e18473afbb51eeaed874486e680ef11ab` |
| d02 and d03 | `c6001013696722ddfd240b185cd66673b71d056596e5a10a08aa6a61bb2f039e` |
| d04 | `1c9167440703d739070298a28dfdc37fe2a7e7396720574559300a1b90394f96` |

Before the repairs, the owners' public runs failed on the incomplete successful receipt; afterward, the public checks passed. That observed before/after improvement is compatible with the frozen hidden failure. It is not evidence that the private record flag is required, nor does passing the public check prove the whole task complete.

## Separate ambiguity: accepted-renewal fee timing

`TASK/hidden/oracle.py:25–27,34` renews an unblocked loan at day 20, calls its fee recorder at day 23, and requires the event `("late", 13)`. Because `record_overdue_fee` is once-only (`TASK/visible/circulation/fee_escalator.py:8–14`), this also requires **no charge during the successful renewal at day 20**.

There is a defensible behavior-preservation argument for that expectation: the original successful renewal never called the fee recorder, and the requested bug concerns refusal. D01–d03 preserve that path; their finals explicitly acknowledge that accepted-fee timing is not pinned by the visible checks. D04 instead charges day 20, producing `("late", 10)` and making the later fee call a no-op. That is the exact reason its `remote-a` fails; it is not a missed fee-clock reset.

However, the visible fee doc explicitly preserves the **clock**, not invocation timing, and the visible successful-path assertions do not constrain `charged` or `events`. Thus distinguish a regression against existing successful behavior from a guaranteed, explicitly stated timing requirement. Do not present the hidden exact day-23 charge as unambiguous contract discovery evidence. D04's trace supports an inferred broader charging policy, not a failure to read the relevant file.

## Consequence for the screen

The three Claude outcomes cannot support the hypothesis that native, current instructions and discovery instructions all missed a nonlocal contract: each inspected the visible files; two explicitly rejected the extra state as unnecessary. D02 and d03 even produced identical implementation bytes. D04 made a different policy interpretation and failed a different hidden row.

Exclude UA1 as a whole from admission and pair-residual selection, including later scheduled UA1 cells irrespective of their scores. Retain original verdicts and costs as instrument-invalid or disputed task evidence; any aggregate must identify the exclusion and its resource-accounting treatment. Audit the other task-to-oracle mappings before more dispatch. A clarified future task needs a new registration and fresh comparison; it must not replace these frozen bytes or manufacture a treatment win.
