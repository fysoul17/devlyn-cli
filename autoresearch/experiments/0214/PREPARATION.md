# 0214 — diagnose 0213 input growth; prepare, do not dispatch

2026-09-23. Root direct. User selected Fable/Grok diagnosis and preparation only.
0213 remains stopped: A COMPLETE, B BUDGET_EXCEEDED with terminal usage UNKNOWN,
22 NOT_RUN. No old cell is resumed, replaced, reassessed or promoted.

## Observations and limits

The immutable B rollout records 16 native usage updates associated with16 tool turns, ending at390,690 native
input plus32,799 review input =423,489, exceeding400,000 by23,489. Native cached
input328,832 is a subset of390,690, not an extra addend. This last observation
is not terminal usage, billing, or an all-attempt total.

Two B owner generations at14:45:54.834Z and14:46:07.546Z did nothing but poll
the existing review with requested1000ms waits. Both returned empty after5s.
The durations are from response_item/custom_tool_call_output payloads, decoded
from their JSON text blocks (wall_time_seconds and empty output fields).
Their associated generation inputs were28,044 and28,316 (sum56,360). The next
poll requested30000ms and returned the review after1.8s, with28,484 generation
input. A also had two empty short review polls (26,123 +26,262 =52,385 input).
These are input attached to generations issuing polls, not a price charged by
the waiting tool. Removing the observed56,360 arithmetically yields367,129;
that is a sensitivity calculation, not a prediction of a rerun's consumption.

Packet compaction had already reduced B review input to32,799. There is one
incomplete pair and no controlled counterfactual; no evidence supports raising
the limit, weakening checks or selecting an arm.

## Prospective diagnostic pilot (NOT_RUN)

Use two fresh D1 cells, A then B, exactly once each. They reuse exposed D1
material only as a technical diagnostic, excluded from advancement, confirmation
and the24-cell cohort. This is a separately budgeted proposal, not permission
to restart0213 or automatically launch a new screen. No C cell, retries,
replacement tasks or automatic follow-on. A failure stops before B.

The only treatment is the common [waiting instruction](common-wait.txt), inserted
immediately after the original0211/common.txt prefix in both generated prompts.
All0211 source files remain byte-identical. Preserve0204/owner.md for B, the source,
caller requirements, checks, model/effort, image and review policy. Do not also
change color handling, formatter availability, packets or candidate wording;
those would confound this diagnostic. No new scheduler or engine hook.

Predict before dispatch: with a review still running and no independent work,
the owner uses30000ms waits, reducing empty short-poll generations. Refute this
operational prediction if either owner requests a shorter sole-call review wait
(a generation whose only tool call polls the already-running review session)
while the outer deadline has not fired. Record requested and actual waits
separately: the old1000ms requests actually waited about5s. Completion below400,000 is an observed outcome, not
guaranteed by the instruction. Record all turns, actual waits, empty replies,
input/output/calls, wall time, checks and failures. No causal efficiency claim
or product adoption follows even if both cells complete.

Keep each owner pool at900s,400,000 cache-inclusive input,20,000 output and5
owner-pool model invocations, including descendants/reviews and teardown;
the4 descendant slots include at most2 participant reviews, not4 plus2. Total two-cell owner targets:800,000 input,40,000 output,
10 invocations. Keep each external assessment separate at240s,400,000 input,
8,000 output and1 invocation (two-cell totals800,000/16,000/2), plus120s per
deterministic check allowance. First observed breach or accounting, identity,
lineage, model, deadline or teardown failure stops the whole pilot. Interrupted
usage stays UNKNOWN. Limits remain observational, not guaranteed spend caps.

## Execution preparation and launch boundary

1. Preserve0210–0213 evidence and recovery refs. Allocate a new owned branch,
   scratch and fresh cell/home directories under a unique pilot output root;
   label the pilot separately from0213 in cohort accounting. Never reuse old auth.
2. Run `python3 -B autoresearch/experiments/0214/prepare.py <0-or-1> <runtime.json>`.
   The wrapper reuses0211/prepare.py and synchronizes the inserted common prefix,
   plan.argv prompt and baseline prompt SHA256. Set runtime.pilot_id to a fresh
   pilot tag and runtime.output to a new directory with that name; pilot.json
   records the tag, script/treatment hashes and diagnostic exclusion per cell. Bind this script's hash
   and the tag/output root in the launch seal and cohort. Reuse0210/native_cell.py,
   0211/check_cell.py and0211/assess.py. No model dispatch in0214.
3. Rebuild read-only control mounts from the retained source, validate exact
   image availability and calibrated D1 checks, and run existing accounting,
   packet and bounded teardown controls. Removed private scratch must be rebuilt,
   not recovered from evidence or historical runtime.json absolute paths.
4. Verify current-login and fresh Fable snapshot account/organization match,
   exact Astra/high and Fable5.1/medium routes, versions and available quota.
   Keep credentials0600 in owned scratch; record only fingerprints. No model or
   account substitution. Grok4.7 is preparation review only, not a participant.
5. Bind source/prompt/config/image/evaluator hashes, calibrated check results,
   paths, identities, order and budgets in a new launch seal before inference.
   Verify prompt.txt bytes equal plan.argv[-1] bytes and baseline.prompt_sha256
   equals their SHA256, with the sole delta at the original common boundary.
   Existing real native-child capability evidence may be reused only if its
   entire runtime binding still matches; otherwise a separately budgeted
   capability check must precede any pilot cell.
6. Dry materializations are evidence only. Regenerate all cells at launch with
   fresh runtime paths; never launch a saved dry plan. At a later execution
   instruction, run A; only if COMPLETE and all guards
   pass, run B. Apply frozen deterministic and blinded checks. Publish all
   attempts and stop. This preparation does not claim launch admission today.

**No overengineering / Optimized:** one common waiting instruction is the
minimum intervention suggested by observed empty polls. The small preparation
wrapper prevents the observed common-prefix/embedded-prompt mismatch. Deleting
the pilot boundary would conflate exposed diagnostics with the stopped screen.
