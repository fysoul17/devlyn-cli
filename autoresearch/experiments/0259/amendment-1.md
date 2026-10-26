# 0259 amendment 1: authentication fault reported only on the retry event (2026-10-26)

This is a dated amendment to the frozen [DESIGN.md](DESIGN.md) (r2) and the [registration](registration.md). It was
written before any measured cell was graded. The probe, the witness and the audit had not run on any tree.

## Observed failure

`d007-D3-claude-C-r4` was dispatched at 2026-10-26T04:10Z. The host lid was then closed and the Mac slept on battery
until about 11:00Z (`pmset` log: `Clamshell Sleep`, `Using Batt`). On wake the cell's Claude session could not refresh
its OAuth token:

- It made 10 `system`/`api_retry` events. The last one has `error_status: 401` and `error: "authentication_failed"`.
- The `result` event that follows has these values:
  - `is_error: true`
  - `terminal_reason: "api_error"`
  - `api_error_status: null`
  - `model: "<synthetic>"`
  - `result` reads "Failed to authenticate: OAuth session expired and could not be refreshed"
- The cell has zero input and output tokens and zero trace bytes, with `owner_status=EXITED_NONZERO`.

The next cell, `d008`, ran normally with a fresh credential.

The registered classifier is 0233's `quota.py`. It treats a Claude result as an authentication fault only when the
result itself carries `api_error_status` 401 or 403. This failure put the 401 on the retry event instead, so it was not
recognised. The cell was scored `PRODUCT_INCOMPLETE` as though the model had worked and failed, when no model turn ran.
Under the fault rules DESIGN keeps (0256 DESIGN "Faults"), a shared account fault during execution is archived and
rerun, and 0233's classifier counts an authentication result as such a fault. This failure falls under that intent but
has a shape the classifier does not match.

## Change

1. **The authentication rule gains one shape**, matched on native fields only. Within one Claude stream file, consider
   a `result` event with all three of these:
   - `is_error: true`;
   - `terminal_reason: "api_error"`;
   - `api_error_status` missing or null.

   It is an authentication fault of kind `claude authentication retry` when the most recent `system`/`api_retry` event
   before it has `error_status` 401 or 403, and nothing between them shows a request getting through. A `result` event,
   or an `assistant` event whose `message.model` is not `"<synthetic>"`, shows one, and clears the remembered retry.
   (`d007` has only the CLI's synthetic error message between its last retry and its result.)
   - A 401 retry followed by a successful result is not a fault.
   - A result with its own status other than 401/403 (for example 500) is left to 0233's rule.
   - Model prose and the result text are never read.
   - The rule applies to execution and assessment streams alike, as 0233's rule does.
2. **Finished verdicts are reclassified once by the same rule.** A measured cell's final, non-STOP verdict is
   rewritten to `status: STOP` when all of these hold:
   - its preserved evidence now shows an execution fault under the amended rule;
   - its recorded `quota.execution` was empty.

   The new reason is `shared account fault during execution: <kinds>`. The rewritten verdict keeps every original field
   and records the original status and its sha256 under `reclassified`. The driver's existing path then archives it as
   `.stop-N` and reruns the cell in a fresh attempt, the same as for a quota fault.
3. **Only final verdicts are scored.** Archived attempts still add their wall time and usage to the slot's reported
   costs, and they remain in the mandatory audit of every attempt.

The rule does not read the arm, the task or any outcome. A sleep interrupts whichever attempt is running, so the
RESULT reports every reclassified attempt by arm. The schedule, caps, deadline, scoring, identity rule, and all other
registered controls are unchanged. The rerun of `d007` comes after the last scheduled cell instead of in its original
slot, because the run is not interrupted to apply this amendment. The RESULT discloses this.

## Review

Astra ultra and Grok 4.7 reviewed read-only ([results/](results/)).

- **Round 1:** both REVISE with the same two HIGH findings:
  - a remembered 401 retry outlived later results;
  - an explicit terminal status was overridden.

  Change 1 was narrowed under `results/amend1-fix-r1-contract.md`, with regression tests.
- **Round 2:** both SHIP, no findings.

Tests: 36 passed, 33 subtests; 0258's suite 27 passed. A dry classification of the 19 finished verdicts matches only
`d007`.

## Operator steps

1. Let the running driver finish the schedule; its loaded code is not changed under it.
2. Move the measured checkout to the commit that contains this amendment.
3. Run `python3 autoresearch/experiments/0259/reclassify.py <runtime.json> autoresearch/experiments/0259/cells.tsv` and
   record its output.
4. Relaunch the driver with the same schedule. It skips finished cells and archives and reruns each reclassified one.
