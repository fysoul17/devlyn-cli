# Iteration playbook

One iteration tests one falsifiable hypothesis about the harness under the
harness ladder ([0232](../iterations/0232-harness-ladder.md) §2 and §6). Rung 1
is the instruction-only harness; each later rung adds one mechanism licensed
by a failure observed on the rung below. A candidate is admitted only under
§6: quality preserved, each task's completion count and each check or
oracle-row pass count no lower, per-success wall, input and output each no
higher, and more completions or one strictly lower per-success cost, with all
costs counted per correctly completed task, failures included.

Worked examples: [rp-d8](../experiments/rp-d8-bookkeeping-note/) for one
candidate (DESIGN, registration, results) and
[0233](../iterations/0233-installed-baseline-and-failure-paths.md) for a
multi-arm baseline.

## Identity

`NNNN` is the next unused integer after the last entry in `iterations/`.

## Evidence rules

Adapted from the editor, composer and reflector stages of
[Harness²](https://github.com/google-research/harness2)
(`harness2/core/prompts.py`; arXiv 2610.14224).

1. **Keep the base.** No change is the default outcome. A candidate replaces
   the base only when a frozen comparison meets the ladder rule; an owner
   adoption outside that rule is recorded as the owner's decision, separate
   from the experimental verdict.
2. **Anchor the contrast.** Cite the measured base and the exact trajectory
   moments where runs diverged. Freeze the candidate, prediction, endpoint,
   accounting and stopping rule before the first measured cell; an edit
   without execution evidence is speculation.
3. **Separate defects from frequency.** A failure that repeats across
   replicates is the strongest ground for a change, and a single occurrence is
   weak evidence of frequency. Reproduce a suspected contract, safety or data
   defect mechanically instead of dismissing it as noise.
4. **Record attribution honestly.** Give each changed component a verdict
   (helped, hurt, no observed effect or confounded) with the run and moment
   behind it. Confounded evidence alone supports no lesson.
5. **Choose the smallest effective change.** Try deletion or reuse first, and
   pay for added always-on text with a cut. Concise always-on prose fits
   ordinary sequencing; a hook needs repeated evidence that clear instructions
   are skipped and must never block valid completion.

## Steps

1. **Design** in `experiments/<id>/DESIGN.md`: why (rule 2), the strongest
   counter, the question, one candidate, arms, schedule, grading, the
   prediction frozen before smoke, ordered decision rules that include
   inconclusive and no-failure-observed outcomes, apparatus, and
   interpretation limits.
2. **Review the design** with Astra ultra and Grok 4.7 in parallel,
   read-only. Resolve each finding an independent check confirms; a
   substantiated blocker is fixed, never outvoted, and root decides the
   freeze ([NORTH-STAR](../NORTH-STAR.md), decision authority).
3. **Qualify the apparatus** for each engine × arm before any measured cell:
   the actual staged installation, dependencies and graders, and each guard
   with a violating and an allowed control. rp-d8's Claude-shaped offline
   tests missed a Codex installation-validation failure
   ([amendment 1](../experiments/rp-d8-bookkeeping-note/registration-amendment-1.md)).
4. **Register, run, report.** `registration.md` copies the frozen prediction
   and decision unchanged; `results.md` gives raw numbers, the decision by the
   frozen rule, per-component verdicts (rule 4) and next candidates for the
   owner.
5. **Record** one `DECISIONS.md` line and update `HANDOFF.md` by replacing
   superseded text, not appending to it.

## Anti-patterns to refuse

- **Re-running until the answer pleases.** A suspicious result gets its own
  investigation, never a silent rerun.
- **Renaming a verdict or editing a prediction after the run.** The log is
  append-only.
- **Bundling two mechanisms in one candidate.** The result cannot be
  attributed.
