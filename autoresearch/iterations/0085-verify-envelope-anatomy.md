---
id: "0085-verify-envelope-anatomy"
title: "Measure the portable post-judge VERIFY envelope"
kind: instrumentation
status: FROZEN 2026-07-28T14:46:42Z
complexity: medium
depends_on: ["0084-node-lint-applicability"]
---

# iter-0085 — measure the portable post-judge VERIFY envelope

## Why this iteration exists

The user asked Codex, Fable 5, and Grok 4.5 to find and improve the next real
problem together. The corrected `nodeg-hook-20260722c` anatomy is
conservation-clean for all seven rows and places the largest phase median in
VERIFY: 615,523 ms, versus startup at 193,016 ms. Four rows completed VERIFY.

Their portable receipts show a large wall after judge output exists but before
VERIFY completes. The clearest row is F25: the primary and pair judge tools end
at 15:11:03 and 15:11:32, while the merge summary is not written until
15:14:56 and the phase completes at 15:15:33. The recorded
`pair_judge: 222000` is queue-inclusive over sequential 193,695 ms and
29,052 ms calls, so the state duration fields are not a trustworthy interior
thermometer.

R0 split on BUILD versus MEASURE-FIRST. Fable's R1 named the deciding delta and
joined Codex and Grok on MEASURE-FIRST: concurrency can explain only a minority
of the residual on F7/F11, only F25 was fully manually anchored, and choosing a
whole-VERIFY dispatcher before a bucket table risks repeating iter-0077's
failed mechanical-absorption claim. This iteration therefore implements only a
read-only offline instrument. It changes no product behavior.

## Decisive criterion

**Measured dominant-path causality:** register a later product mechanism only
when a portable, conservation-checked lifecycle bucket is large enough to
matter and the mechanism's causal path actually removes that bucket. Do not
infer primary-versus-pair identity or model-thinking sub-buckets from debug
lines that do not contain that information.

## Subtractive-first answer

1. Delete the proposed semantic seven-bucket parser: stored debug events do not
   reliably identify primary versus pair work or prompt-thinking time.
2. Delete the dispatcher from this iteration: the winning causal path has not
   been published yet.
3. Add one smallest instrument that uses timestamps already preserved on judge
   and merge artifacts to partition VERIFY into pre-finalization and
   post-judge finalization wall.

This pure-addition measurement surface is required by the user's explicit
three-model improvement request and the observed broken VERIFY thermometer.

## Fixed population and portable inputs

Input root:
`benchmark/ceiling/results/nodeg-hook-20260722c/`.

Discover rows from `*/A1/attribution.json`; score exactly the four rows where
`verify_complete` is true. Read only:

- `A1/attribution.json`;
- `A1/devlyn-snapshot/runs/*/pipeline.state.json`;
- `A1/devlyn-snapshot/**` judge-output and merge-summary artifacts;
- `A1/claude-debug.log` only for advisory TaskStop and tool-interval receipts.

The instrument must not read the original off-repo worktrees. F26
`history[0]` is reported as secondary context, if reported at all, and excluded
from the fixed four-row medians.

## Exact anchors and buckets

For each scored current VERIFY record:

- `phase_start` / `phase_end`: `phases.verify.started_at` and `completed_at`;
- `final_judge_output`: latest filesystem mtime inside the phase window among
  recognized raw primary/pair stdout artifacts. The output must list every
  matched relative path, mtime, and SHA-256 so the selected maximum is
  auditable;
- `merge_complete`: the current run's `verify-merge.summary.json` mtime;
- `pre_final_judge_ms = final_judge_output - phase_start`;
- `judge_to_merge_ms = merge_complete - final_judge_output`;
- `merge_to_phase_end_ms = phase_end - merge_complete`;
- `post_judge_finalize_ms = judge_to_merge_ms + merge_to_phase_end_ms`.

Only the two non-overlapping partition buckets
`pre_final_judge_ms` and `post_judge_finalize_ms` compete for conservation.
The two finalize sub-spans explain the aggregate and must not be counted again.
Every anchor must satisfy
`phase_start <= final_judge_output <= merge_complete <= phase_end`.

Filesystem timestamp precision must be emitted. The partition must conserve
the recorded VERIFY duration within 1,000 ms per row. A missing, ambiguous, or
out-of-order anchor makes that row ineligible; it must not be silently filled
from `judge_durations_ms`.

Recognized judge-output names must be explicit and minimal for the frozen
cohort, covering the existing Codex primary raw stdout variants and the run's
`claude-judge.stdout`. Do not accept arbitrary `*.stdout` files. Malformed or
retry artifacts may be listed as receipts but the latest successful canonical
judge output is the anchor.

## Output contract

Add `benchmark/ceiling/scripts/verify-envelope-anatomy.py` with:

```text
python3 benchmark/ceiling/scripts/verify-envelope-anatomy.py \
  benchmark/ceiling/results/nodeg-hook-20260722c \
  --output benchmark/ceiling/results/nodeg-hook-20260722c/verify-envelope-anatomy.json
python3 benchmark/ceiling/scripts/verify-envelope-anatomy.py --self-test
```

The JSON must be deterministic (`sort_keys`, no NaN), use only paths relative
to the input root, include input hashes, per-row anchors/buckets/conservation,
advisory state `judge_durations_ms`, explicit thermometer flags, aggregate
medians, and a machine-readable gate verdict plus failed conjuncts.

`--self-test` must build temporary synthetic fixtures and cover at least:
ordered anchors/pass, missing judge output, ambiguous current run, out-of-order
mtime, non-conservation, irrelevant stdout rejection, deterministic bytes, and
the four-row frozen regression when the repository cohort is present.

## Stage-A decision bar

The bar is frozen before any product mechanism and is informed by the already
disclosed R0 manual extraction; this is a registration gate, not a blinded
experiment.

`P-0085-VENV` is PASS only when all conjuncts hold:

1. exactly four verify-complete rows are discovered and at least three are
   eligible;
2. every eligible row conserves VERIFY within 1,000 ms and has ordered portable
   anchors;
3. median `post_judge_finalize_ms` is at least 120,000 ms;
4. median `post_judge_finalize_ms / verify_duration_ms` is at least 20%;
5. the aggregate contains no absolute host/worktree path and every selected
   receipt has a SHA-256.

PASS registers only the failure class
`post-judge VERIFY finalization envelope`; it does not authorize or select a
dispatcher. Any later mechanism must receive its own frozen spec and matched
behavioral probe.

STOP / invalidation:

- fewer than three eligible rows, any eligible conservation failure, or an
  anchor-order failure means the instrument is invalid and must be fixed before
  mechanism work;
- either effect-size threshold missing means STOP on this lever and publish the
  spread;
- a result that depends on `judge_durations_ms`, an unportable worktree, or an
  arbitrary stdout glob is rejected as measurement laundering;
- a future mechanism that weakens either LLM judge, fresh-context independence,
  merged-severity behavior, or user-visible failure handling is rejected.

## Scope boundary and mission boundary

Allowed tracked implementation surface:

- `benchmark/ceiling/scripts/verify-envelope-anatomy.py`;
- this iteration record;
- the generated
  `benchmark/ceiling/results/nodeg-hook-20260722c/verify-envelope-anatomy.json`.

No canonical or installed skill, shared product script, state schema, engine
route, prompt, gate, dependency, or benchmark raw receipt may change.

A future helper that preserves both fresh LLM judges and only fuses measured
mechanical finalization can remain Mission 1 work. Replacing, skipping, or
synthesizing an LLM quality verdict is the M1.5 deterministic-runner boundary
and is not authorized here.

## Verification

- `python3 benchmark/ceiling/scripts/verify-envelope-anatomy.py --self-test`;
- generate the frozen JSON and require exit 0 / gate PASS;
- rerun generation and require byte-identical output;
- independently recompute all four anchor chains from state/artifact mtimes;
- `python3 -m py_compile benchmark/ceiling/scripts/verify-envelope-anatomy.py`;
- `bash scripts/lint-skills.sh`;
- `git diff --check` and exact changed-surface audit.

Done means the portable result either names a material post-judge finalization
envelope or stops cleanly. No product optimization is bundled into the
measurement result.
