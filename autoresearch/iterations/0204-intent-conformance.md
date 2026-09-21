# 0204 — Internal intent owner executes, repairs and refuses false completion

2026-09-22 KST. Root direct, no resolve invocation. Continues
[0201](0201-harness-transformation-plan.md) after 0202/0203. Internal candidate:
[owner prompt](../experiments/0204/owner.md),
[pre-invocation protocol](../experiments/0204/PROTOCOL.md) at `ff17af5`.
No installed skill, public option, default routing, pair policy or release changes.

## Observed trace and decision

One owner invocation, reported as `gpt-6-astra/high` by native `turn_context`, called actual
`claude-fable-5-1` twice for independent static review. The owner handled
planning, implementation, code cleanup and real checks in its own context.
The 42 native command events contain no separate PLAN/BUILD/CLEANUP model call
or resolve invocation. Native rollout identity, reviewer modelUsage, transport,
raw checks and source hashes are retained in `.devlyn/0204/`.

The source is a new copy of the exposed 0198 `binding-1-initial` product, not a
fresh task or a model-quality draw. Independent review was explicitly requested;
autonomous review selection, different executor/owner engines and initial
feature generation were not tested. This establishes the invocation portion
of 0201 step 1 for this route, not full step 2 admission or product adoption.

**The fixture result is INCOMPLETE, not PASS.** The following are separate facts:

- Owner inspection found the known Unicode-branch identity defect; the first
  Fable review missed it. Owner corrected an initially cascading probe, then
  reproduced 18 failing subcases before changing source. Replacing `strip()`
  with `removesuffix("\n")` and adding two regression methods closed those cases.
  Do not attribute this repair's discovery to Fable.
- The 13 inherited/added tests and bootstrap self-test passed. Root independently
  reran both against the same source. Supplemental actual-Git witnesses changed
  from 4/6 to 6/6: ordinary branch, trailing NBSP, branch/tag collision, each with
  an owned receipt and a real allocated receipt whose status was changed to COMPLETE.
- Fresh Fable review supplied a new non-branch symbolic-HEAD counterexample.
  The owner reproduced erroneous receipt binding after `HEAD` was pointed at
  `refs/tags/t`, then stopped with the finding unresolved at the two-review cap.
  No source changed after the final review and no third call was launched.
- Windows junction handling remains an unexecuted platform finding. The
  inherited expected file fails the supplied checker's shape check; it was kept
  immutable and both actual test commands ran directly. Neither limit is PASS.

The observed sequence is first review → owner-originated repair → affected
checks → fresh review → reproduction of a reviewer finding. **Repair of a
reviewer-originated finding remains OPEN.** The first review's deep-JSON concern
was reproduced but met the requested CLI refusal contract; advice about read-only checkouts was outside the repair scope, and its Windows claims remain unexecuted.
This does not prove task completeness or superiority over native.
The original 0198 product and out-of-scope fixture bytes
remain unchanged. Final check/review hashes match the repaired source; the
root audit verifies this independently of the owner's self-report. Compared
values and artifact references are in `hash-comparison.json`, with the executed
`audit.py` retained alongside them. This is root evidence, not a claim that the
static Fable source reviewer independently recomputed those hashes.

## Evidence and apparatus review

`AUDIT.json`, `owner.rollout.jsonl`, `owner.stdout`, `participant.diff`,
`participant-evidence/owner-result.json`, root checks and baseline/final
witness files are under `.devlyn/0204`. The retained participant is
`/Users/aipalm/.local/share/nx01/0204-participant`; it was not published as product code.

Separate actual Fable source advice exposed loss of witness evidence on malformed
output. Corrected recording retains failed rows; non-JSON output, non-object
output and malformed state controls each record 6/6 failures. An explicit HEAD
assertion supplements the real allocator's branch switch. The witness cases
were named before dispatch; their implementation was committed after dispatch
began, so these are supplemental checks, not a preregistered comparative score.
Original baseline evidence is preserved separately from the amended replay.

The review helper now labels missing checks explicitly. That packet-only control
used zero model calls; the change was made after the frozen live trace. The
reviewed owner prompt is unchanged. Root dispositions retain rejected advice:
the claimed false-green NBSP terminal row is contradicted by both raw baseline
runs (exit0, `passed:false`). Generic CLI refusals remain allowed by the original
request; error-code requirements were not tightened after seeing the result.

Native owner elapsed 703.548s includes its two reviews (128.571s/116.260s).
Observed native OUTPUT: owner 16,193 + reviews 11,116/9,400 = 36,709; reasoning is
included once. Owner input 2,055,405 includes 1,972,608 cached tokens; reviewer
input/cache categories remain separate in raw usage. Outer root preparation,
audit, source advice and delivery are excluded/UNKNOWN. These are diagnostic
counts, not whole-cost, billing, completion-speed or savings evidence. Native
skill-discovery warnings are retained; execution isolation is instructional,
not a certified clean environment. Static review omits some support modules.

## Next boundary

Keep this exposed run frozen, including incomplete findings. Do not fix every
inherited research defect or reroll until PASS. Step 2 still needs repair of a
reviewer-originated finding and the planned
0185 rollback and 0187 scope regressions before A/B/C admission. Then register
new tasks and whole-call time/usage budgets under 0201; the 24/48 ceilings remain
unspent comparison maxima, not authorization for unregistered runs. Public
intent installation/migration, untouched confirmation and Mission1/gate15 stay OPEN.

Principles: pre-flight 0/mission 1 — unblock the actual candidate invocation
decision, not a new research platform. No overengineering/subtractive-first —
one owner prompt reuses the bounded runner/checker; no scheduler or phase DSL.
No guesswork — prediction precedes the run, failures and raw results survive.
No workaround/production ready — explicit routes, scope and incomplete status
remain visible. Worldclass — acceptance covers this internal artifact, not the
unfinished fixture. Best practice/optimized — standard-library tooling and
existing receipt/check primitives; no efficiency superiority claim.
