# Next session: continue core harness improvement

Updated 2026-09-15 KST. Continue the owner's unified vision and model-adaptation
direction through devlyn-cli core improvements: model/harness fit, routing,
overhead, intent/constraint coverage, verification/repair and comparative value.
H is evidence within that program, not the predetermined main deliverable.
**The next implementation and confirmation are NOT_RUN.** 0175's nine draws,
six final reviews, PR44 delivery and owned cleanup are COMPLETE; do not repeat.
Start in `/Users/aipalm/.local/share/nx01/core-continuation-20260912` and read
[HANDOFF](HANDOFF.md) plus the relevant evidence below.

## 0. Resume the agreed goal; reconcile model guidance with implementation

Read the owner-provided unified vision, 0120 and the confirmed official Astra
guide linked in HANDOFF. Its source is resolved; do not ask the user for it again.
Treat Astra guidance as one model's evidence. Inspect the common contract and
actual loaded prompts, skills, adapters and role capabilities for the selected
engines/models. Claude/Grok and future Kimi/Qwen may need different tactics;
do not copy Astra-specific rules globally or confuse a CLI with the model it runs.
The existing adapter cites GPT-5.5; separate source age from behavioral mismatch.
Account for already-shipped 0172/0174 entry changes rather than duplicating them.
Separate completed changes, remaining mismatches and untested ideas.
Vendor advice supplies hypotheses, not
local performance proof or permission to rewrite all phases.
Within the agreed program, record the next bounded work unit, its success checks
and remaining commitments once; resume that unit across session boundaries.
Complete and verify it before advancing. Change the agreed goal/scope/sequence
only through the evidence and user-decision rule in HANDOFF. New ideas go into
remaining work rather than silently replacing the current task.
Select a falsifiable core improvement from this evidence;
the H diagnosis below is available if it serves that choice. Preserve the recent
pair result without making all future work a routing benchmark or fixture repair.
Structural changes remain possible under the existing core-research authorization;
this context update starts no OS integration, model migration or experiment.

## 1. Implement and verify the selected core improvement

Map any confirmed omission to the actual authoring, validation, review or repair
contract and its callers. Follow the standing research execution instruction in
[HANDOFF](HANDOFF.md); preserve current product routing and explicit pins.
Reproduce a proposed core defect before changing source, make the smallest fix,
then run relevant regression/acceptance checks and independent native reviews.
Use fresh cases to test behavioral improvement; deliver accepted core changes
with scoped commits, CI and owned cleanup. If the registered hypothesis is
falsified, close that unit with its evidence and resume the agreed next work.
Do not treat an inconclusive probe as completion or silently change the goal.
Do not invent generic gates, model rules or new phases to justify the fixture result.

## 2. Confirm proposed selection changes and continue the core loop

Keep current direct/full+pair policy while fixing and using the observed better
candidate. Pair's better H outcome is already observed. A general selection rule
needs fresh evidence; isolating Opus-only causation is not a prerequisite to the
repair or practical use of that result.

If the selected unit proposes a general routing-policy change, pre-register a
bounded confirmation with new tasks and repeated bare/solo/pair draws. Declare sample
size, resource ceiling, stop rules and falsifiable prediction before any draw;
use untouched cases, common source/requests/checks, matched primary settings,
fresh sessions and balanced order. Distinguish prepared-spec execution from
requirements discovery. Retain failures and internal repair costs; no favorable
rerolls, tuning on confirmation or indefinite expansion until pair wins.

Compare final substantive defects and contract completion first, then total
verified completion time including repairs, then observed cost. Calibrate common
independent checks and anonymous review; qualify actual skill/catalog exposure.
Unsplit cost counters remain UNKNOWN. Use inspected representation, ownership
and oracle risks to evaluate a boundary; no invented universal difficulty score.
After each scoped result, update the active workstreams and continue the
next supported core improvement. Neither fixture repair nor this screen closes
Mission 1; evidence-backed reductions and fixes remain the product deliverable.

## Reference packet: H diagnosis and calibration, only if selected

If the selected core improvement needs this evidence, trace the frozen H spec,
generated tests, primary/pair findings and repair
rounds under `.devlyn/0175/work/` and `.devlyn/0175/H-{bare,solo,pair}/assessment/`.
Determine why the original 14 independent checks/nominal positive missed numeric
boundaries, why solo's repair remained partial, and how pair reached its better
result. Separate root-authored oracle omissions from generated-check/reviewer
misses and actual harness behavior. These are observations, not yet one proven
core cause. Use this diagnosis to select the smallest falsifiable core hypothesis.

Use a new owned task/checkout and a copy of the final H-pair product as the
starting candidate. H-pair already fixes measured precision loss; preserve that
gain while closing the remaining defect. It is an experimental fixture, not
devlyn production queue code. A fixture repair alone proves no harness change.

- Source: `.devlyn/0175/H-pair/assessment/product/queue.py`; associated caller,
  original/regression tests and `spec.expected.json` are in the same product root.
- Contract: `.devlyn/0175/inputs/H/spec.md:6` accepts finite int/float timestamps
  excluding bool, with no integer magnitude bound; duration must be positive.
- Failure: `_validate_time` passes integers through `math.isfinite`, which
  overflows for `10**400`; expiry storage also calls `float(expires)`. Inspect
  validation, arithmetic, persistence and decode together before choosing a fix.
- Evidence: `.devlyn/0175/integer-domain-registration.json`,
  `.devlyn/0175/integer-domain/H-pair.result.json`, and `check-integer-domain.py`
  under `.devlyn/0175/`. Precision evidence/probe: `large-expiry/` and
  `check-large-expiry.py` under that same root.

State the falsifiable prediction before editing: the frozen candidate rejects
valid huge integers; the repair accepts them with exact persisted expiry,
exclusive ownership and correct acknowledgement, while keeping the precision
case `now=2**53, duration=1` and existing behavior intact.
Do not narrow the contract to make the failure disappear or edit frozen inputs.
Keep source changes within the existing authorized queue/regression-test surface;
copy and prepare required test inputs before running the new task's actual gates.

Close with a failing-before/passing-after regression, all original and specified
checks, the existing 14 independent H methods, precision/domain probes, and
independent verification of tenant/token/expiry fences, concurrency, rollback
and scope. `check-integer-domain.py` reports JSON `pass`; exit zero alone is not
acceptance. Verify representation boundaries of the chosen fix as well as the
known example. Follow current route/pin and bounded repair rules; a review PASS
does not override a failing requirement. Preserve original 0175 results and
report this follow-up separately. Do not repair every frozen arm to re-rank them.

Historical protocol: Git
`701c43dcf7ae84446a2ca432d64131762e0232b2:autoresearch/NEXT-SESSION-routing-boundary.md`.
Frozen inputs/results: [0175](iterations/0175-routing-boundary.md),
`.devlyn/0175/REGISTRATION.json` and `.devlyn/0175-delivery/0175-evidence.tar.gz`.
