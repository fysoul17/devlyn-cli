# 0184 — review connected to matched repair

## Decision and scope

This Mission 1 study answers whether bounded direct development should add
mandatory OTHER-model review plus repair, compared with equally budgeted fresh
same-model review plus repair. The owner authorized the actual next comparison
and confirmed that harder development tasks should follow separately. Root performs
research directly; no resolve is invoked in this study.

[Protocol](../experiments/0184/PROTOCOL.md) fixes four new Astra/high initial
implementations: two requests on the actual prediction collector, two draws each.
Each initial product is sealed and copied into same-model and Fable5.1/high review
branches, followed by identical fresh Astra/high repair. Review packets are identical
within each pair; initial reasoning, timings and external checker results are withheld.
Every branch runs even if its initial source is correct, so false-positive harm can
be observed. Root neither filters review claims nor repairs measured products.

These are two root-authored requests on one real internal tool: transactional output
publication and literal patch filenames. They are not independently sampled tasks
or evidence for complex cross-module/state/concurrency work. Each request explicitly
excludes the other's existing behavior; unrelated findings are not valid repair goals.

Registration at 2026-09-16T13:46:17.048633+00:00 binds 40 files, including requests,
source/checks, runner, unchanged 0179 direct instructions and native binary inputs.
Registration SHA256 `cbb227bccefd8358f368860f7da3c3fea97de43e69c10b9aba849249cc2e8544`.
Native Codex 0.154.0 and Claude Code 2.1.273 were observed before dispatch. Both reviewers
use high effort and 600s bounds; initial/repair Astra calls have 1200s bounds. The reused
outer process observer retains its original 1800/1810/1830s ceilings; run-bounded
argv enforces the smaller native budgets. Process trees and raw transport are retained.

## Calibration and transport

The actual-CLI checker distinguishes original/reference/mutant for both requests
(6/6 expected outcomes). It checks ordinary output/schema/filter parity, literal
metacharacter/Unicode/space names, failure preservation of existing/absent output,
real file-size-limited write failures, atomic replacement and cleanup.

An initial checker missed a staging-then-direct-overwrite mutant. A real hardlink
control now checks that successful publication does not overwrite the old inode;
the mutant fails and the atomic reference passes. Original failed calibration and
pre-correction checker are retained. This occurred before any quality draw.

The first Fable setup was rejected before Popen by the reused observer's fixed
bounds contract; no model was called. The final transport probe passed with exact
Fable5.1 usage, tools/MCP/plugins absent. Its native client also reports small Haiku
infrastructure usage, retained rather than omitted from cost. Fable list-price
estimates are not actual bills.

The self-review probe returned the requested JSON with no tool calls. The runner
initially misclassified a native unstable-feature warning as a tool event; its raw
warning/result remains unchanged, and the event classifier now records errors
separately from tool calls. No additional inference was used to rewrite that result.
Codex read-only tool capability remains callable, unlike disabled Fable tools; actual
review tool use is prohibited and checked. This transport difference limits claims
of perfect configuration identity across engines.

## Results

All 20 scheduled native calls completed: four initial implementations, eight reviews
and eight repair/verification runs. All 12 sealed sources passed the frozen mechanical
checker and supplied smoke test, with preserved scope and no debris. That score
missed a requirement violation; it is retained unchanged in ASSESSMENT.json/METRICS.json.

Both same-model reviews identified --out equal to a patch or instances input path,
which destroys that input despite the explicit preservation requirement. Root wrote
the replay prediction after all sources were sealed, then ran 14 actual CLI controls
on the six atomic products and calibration reference. Both initial and both OTHER
products returned success and overwrote the input. Both same-model repairs rejected
with exit1, empty stdout and unchanged input. The calibration reference also fails:
its checker coverage gap is explicit, not retroactively repaired into a PASS claim.

| Path | Root-complete products | Failures fixed | New regressions | Mean review+repair |
| --- | ---: | ---: | ---: | ---: |
| Initial direct products | 2/4 | — | — | — |
| Fresh Astra review → Astra repair | 4/4 | 2 | 0 | 87.988s |
| Fresh Fable review → Astra repair | 2/4 | 0 | 0 | 143.731s |

Each reviewer reported two findings. Astra's findings concerned the same input-loss
invariant in two independent initial draws (native severities MEDIUM/HIGH). Fable's
LOW findings identified absent filename/line context in decode/JSON diagnostics.
Six further CLI diagnostic replays confirm that its repairs added that context and
preserved output. These are concrete, non-blocking actionability improvements, not
invented defects; the frozen request did not prescribe exact filename/line fields.
They did not close input loss. The two literal tasks remained correct and unchanged
through both review routes. Root inspected every initial source delta, all repair
source deltas, raw findings and repair explanations; no additional blocker was found.

Shared generation took 593.211s. Same-model review/repair took 90.383/261.569s;
OTHER review/repair took 323.113/251.809s. Counterfactual native path totals are
945.163s and 1168.133s, including the same generation once in each; these are all
attempts, including incomplete OTHER products, not successful-only completion times.
Physical experiment accounting charges generation once, not twice. External checker
and smoke assessment added 2.917/3.015s for final branches; root collision/diagnostic
replays, preparation and delivery are separate. Native counters and Fable list-price
estimates/auxiliary usage are retained; actual dollars are UNKNOWN.

Review packet bytes matched in every pair and all reviewers used zero tools.
Blinding was incomplete: Codex's rendered environment contains coded identifiers
such as atomic-1-S-review in its cwd, despite the user packet withholding conditions
and timings. Native system contexts and tool callability differ too. These limitations,
two requests on one source, and post-seal collision adjudication prevent a general
model-ranking or perfect-blinding claim. Raw evidence and all 40 registered inputs
remain preserved; no model received external replay feedback and no product was rerun.

Decision: the prediction that OTHER review repairs more failures was not supported.
Do not replace same-model review with OTHER review on this sample, or infer a need
for mandatory additional peer review. Fresh same-model review plus repair helped
here. This study compares single reviewers, not their combination; it does not test
or change the installed full-route pair default. The atomic request has a persistence/
preservation contract, so small file count does not establish low-risk direct-entry
eligibility. Full safeguards for such work remain intact. Harder cross-module/state/
concurrency tasks are the next fresh comparison, with actual resolve controls.

Evidence authority: `.devlyn/0184/RESULT.json`, frozen ASSESSMENT.json/METRICS.json,
COUNTEREXAMPLE-PREDICTION.md, INPUT-COLLISION-REPLAY.json, DIAGNOSTIC-REPLAY.json,
registration, source seals, paired packets and raw native streams.

## Principles and delivery

Pre-flight 0: this is the owner-requested final comparison before the bounded-direct
peer-review go/no-go decision. Mission 1: measure additional correct repairs and harm,
then verified completion time, while preserving the engine's baseline capability.
No overengineering/optimized: reuse existing bounded native/process machinery;
only paired snapshots, actual-CLI checks and evidence needed for this comparison
are added. No guesswork: freeze prediction/input bytes before dispatch, preserve
setup and calibration failures. No workaround: no outcome selection, planted model
errors, operator repair, silent model fallback or erased failed draw. Best practice:
stdlib filesystem/CLI controls; code shape is judged through behavior and source
review, not exact reference text. Worldclass/production ready: no unrelated product
code or peer policy is promoted without demonstrated benefit and no blocking defect.

Delivery/CI/owned cleanup is separate from research verdict under receipt
500627caa6c42463728dd5e5; `.devlyn/0184-delivery/FINAL.md` owns final status. Source/Git,
frozen evidence and original WIP remain preserved. No collector product change,
installed skill/routing change, or package release is included in this research result.
