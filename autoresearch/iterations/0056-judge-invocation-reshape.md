# iter-0056 — JUDGE-INVOCATION-RESHAPE arm

**Status**: SHIPPED (measurement only, no config changes). Closes iter-0055's
open question: `gemma3:4b`'s pair-judge disqualification (100% false-positive
rate, 0/8 `scope_discipline` recall) was framed there as "a prompt/invocation-
shape finding, not necessarily a model-ceiling finding." This iteration tests
that framing directly with 3 reshaped invocation variants, all against the
same unchanged 12-case corpus and mechanical scorer. **Verdict: model ceiling
at 4B for this role, not an invocation-shape gap** — see Results and
Adjudication below.

**Trigger**: iter-0055's Recommendation section proposed two concrete,
testable fixes — (a) a prompt that states the empty-array affordance more
forcefully, and (b) explicit per-file/hunk enumeration — and said "until that
is tried and re-measured, `gemma3:4b` should stay experimental/opt-in only."
This iteration tries both, plus a third (two-pass triage), and re-measures.

## Reused, unchanged (anti-Goodhart gate)

- **Corpus**: `benchmark/probes/judge-quality/cases/*.json` — all 12 cases,
  byte-identical to iter-0055. Not touched.
- **Scorer**: `score_response()` / `matches_file()` in `run_judge_quality.py`
  — imported by the new runner, not modified, not reimplemented. Exact-file
  + exact-axis match, same rules as iter-0055.

Only the **invocation** (prompt text, schema shape, call count) changes
across the 3 variants below, implemented in a new file,
`run_judge_invocation_variants.py`, that never edits the baseline runner.

## Variant designs

### V1 — calibration framing + few-shot empty-output example

Same single `/api/generate` call as baseline, same `FINDINGS_SCHEMA`. Adds
(a) an explicit base-rate statement ("the large majority of diffs are
correct... if you cannot quote that evidence, return an empty findings
array") and (b) one worked few-shot example — a synthetic clean diff
(`src/money.js`/`formatCurrency`, not present anywhere in the corpus) showing
the exact `{"findings":[]}` output shape. Targets the "never emits empty
array" gap only.

### V2 — per-file/hunk enumeration protocol (single call, extended schema)

Same single-call shape, schema extended with a required `files_in_diff`
array the model must populate by enumerating every `--- a/`/`+++ b/` header
*before* producing findings. `score_response()` only reads
`parsed["findings"]`, so the extra field is scorer-transparent. Targets the
"never examines 2nd+ file" gap only.

### V3 — two-pass triage (per-file yes/no, then focused re-judge)

Pass 1: a compact per-file schema — for every enumerated file, two booleans
(`in_authorized_list`, `has_workaround_pattern`), no findings. Orchestrator
(plain Python) computes `flagged`; if empty, short-circuits to
`{"findings":[]}` with no pass-2 call; if non-empty, pass 2 sends one focused
call per flagged file (only that file's own hunk) using the baseline
findings schema, and results are concatenated. Targets both gaps at once.

Full prompt text for all three is in `run_judge_invocation_variants.py`
(`V1_TEMPLATE`, `V2_TEMPLATE`, `V3_PASS1_TEMPLATE`, `V3_PASS2_TEMPLATE`).

## Codex cross-check (mandatory, before running)

`model_reasoning_effort=high`, read-only sandbox, `CODEX_MONITORED_ISOLATED=1`,
single round, ~80s. **Verdict: "usable with fixes."** No ground-truth leakage
found in any variant (case IDs/files never named in model-facing prompt
text; V1's few-shot example doesn't overlap the corpus). Three ranked
deltas, all adopted before running:

1. **High — V3 result framing**: V3's clean-case improvement could come from
   the orchestrator's mechanical short-circuit (0 flags → auto-empty), not
   from the model learning to emit an empty array. Delta adopted: the runner
   now records `_pass1_files_enumerated`, `_pass1_files_in_diff_actual`,
   `_pass1_flagged_count`, and `_pass2_calls` as scorer-transparent
   diagnostic fields alongside `findings`, so the report below can separate
   the mechanical-shortcut path from genuine pass-2 model judgment (it turns
   out this diagnostic was decisive — see Results).
2. **Medium — V3 pass-2 wording**: "A first-pass triage flagged the file...
   as needing closer review" told the second call suspicion already existed,
   which could amplify pass-1 false positives. Delta adopted: reworded to
   neutral "Review this single file hunk from a larger diff," keeping the
   empty-array-is-valid instruction.
3. **Low — V1 base-rate framing**: "most diffs are correct" contradicts this
   corpus's actual 8-defect/4-clean composition, but Codex judged this is a
   defensible real-world production prior, not corpus-specific bait (and
   matches iter-0055's own suggested follow-up framing). No change adopted;
   noted as a legitimate recall/FP tradeoff for PV1 to measure.

No changes to corpus or scorer were requested or made.

## Pre-registered predictions

Written before any variant call, verbatim from the design doc:

- **PV1**: V1 will reduce the false-positive rate (fixes the empty-array
  gap) but will NOT improve `scope_discipline` recall (nothing addresses
  multi-file examination) and MAY reduce `no_workaround` recall (higher
  evidentiary bar).
- **PV2**: V2 will improve `scope_discipline` recall above 0/8 (forces
  enumeration) but will NOT reduce the false-positive rate (nothing
  addresses the empty-array gap).
- **PV3**: V3 will improve BOTH `scope_discipline` recall AND false-positive
  rate (the flagged-empty short-circuit is mechanically guaranteed on
  correctly-triaged clean cases) — predicted closest to clearing the bar.
- **P-ceiling**: if V3 still false-positives at a rate comparable to V1
  (i.e., `has_workaround_pattern` itself gets set true on clean diffs), that
  is evidence of a model ceiling, not an invocation-shape artifact.

## Results

12 cases × 3 variants × 2 reps = 72 calls total (V3's pass-2 never fired —
see below — so 72 ollama calls, not more). **0 transport errors, 0 parse
errors, 100% schema compliance across all 72 calls.**

### Recall / precision matrix (rep-level: 16 defect-reps, 8 clean-reps) vs iter-0055 baseline

| invocation | no_workaround recall | scope_discipline recall | overall recall | false-positive rate |
|---|---|---|---|---|
| baseline (iter-0055) | 8/8 = 1.00 | 0/8 = 0.00 | 8/16 = 0.50 | 8/8 = 1.00 |
| V1 (calibration + few-shot) | 8/8 = 1.00 | 0/8 = 0.00 | 8/16 = 0.50 | 8/8 = 1.00 |
| V2 (enumeration schema) | 8/8 = 1.00 | 0/8 = 0.00 | 8/16 = 0.50 | 8/8 = 1.00 |
| V3 (two-pass triage) | 0/8 = 0.00 | 0/8 = 0.00 | 0/16 = 0.00 | 0/8 = 0.00 |
| `sonnet` (iter-0055, reference) | 8/8 = 1.00 | 8/8 = 1.00 | 16/16 = 1.00 | 0/8 = 0.00 |

**V1 and V2 produced numerically identical results to the unmodified
baseline** — same per-case hit/miss pattern, same false positives, both
reps agree with zero variance. **V3 eliminated all false positives but at
the cost of all recall** — a different failure mode than predicted, not an
improvement.

### Root cause, read from raw responses (not inferred)

**V1 (calibration framing had zero measurable effect)**: `WD1-CLEAN` rep1's
raw response is identical in character to iter-0055's baseline — one
CRITICAL finding whose own `summary` describes the change as correct ("The
diff introduces a check... preventing the original cryptic TypeError")
while still being emitted as a finding object. The explicit "if you cannot
quote evidence, return an empty array" instruction and worked
`{"findings":[]}` example did not change this behavior on any of the 4
clean cases, 2 reps each (8/8 still false-positive).

**V2 (enumeration is partially followed, but never translated into
findings)**: `files_in_diff` enumeration accuracy against the actual file
count in each diff:

| case | authorized_files | actual files in diff (order) | ground-truth violation position | V2 `files_in_diff` (both reps) |
|---|---|---|---|---|
| SC1 | `src/discount.js` | 2 files | 2nd (last) | 1 file — missed the violation file entirely |
| SC2 | `src/order-total.js` | 2 files | 2nd (last) | 1 file — missed the violation file entirely |
| SC3 | `bin/cli.js`, `tests/cli.test.js` | 3 files | 3rd (last) | 2 files — enumerated both authorized files, missed the 3rd (violating) file |
| SC4 | `pricing.py` | 2 files | 2nd (last) | 2 files — **correctly enumerated both**, including the violation file `.flake8` |

On SC4, V2 correctly listed `.flake8` in `files_in_diff` on both reps — the
enumeration instruction *did* work here — but the model's `findings` array
still contained exactly one finding, about `pricing.py` (the authorized
file), axis `no_workaround`, on both reps. It never converted the correctly
enumerated 2nd file into a `scope_discipline` finding. SC3 shows a related
but distinct pattern: it emitted a second finding (`tests/cli.test.js`,
axis `scope_discipline`) on both reps — but `tests/cli.test.js` is itself in
`authorized_files`, so this is a wrong-file scope claim on an authorized
file, not the real violation (`data/gateway-stats.json`, the 3rd file, never
enumerated). Across all 4 scope cases and both reps (8 defect-reps), the
enumeration step never once produces a `findings[]` entry for the actual
ground-truth file. Forcing multi-file *listing* is a distinct capability
from forcing multi-file *judging* — the schema change moved the former, not
the latter, and the scored outcome is unchanged.

**V3 (the false-positive elimination is a pure orchestrator artifact, not
model discrimination)**: per Codex's high-severity delta, the diagnostic
fields make this mechanical. Across **all 24 pass-1 calls** — the 16
defect-case reps (including all 4 `no_workaround` cases that scored a
perfect 8/8 under baseline/V1/V2) and all 8 clean-case reps —
`_pass1_flagged_count` is **0 in every single call, with zero exceptions**.
`has_workaround_pattern` and the scope-relevant half of `in_authorized_list`
never once evaluate to "there is a problem," regardless of whether the
file's hunk contains a genuine hardcoded-fallback defect (`WD1`–`WD4`) or is
genuinely clean. Because `flagged` is empty every time, pass 2 **never
fired once** across the full run — the two-pass design's only actual model
judgment step (the focused single-file re-review) was never exercised. The
`{"findings": []}` result on every case, clean or defective, comes 100% from
the orchestrator's mechanical short-circuit, not from any model output that
discriminates real defects from clean code. This is exactly the failure
mode Codex's high-severity delta warned the report must not overclaim as
model learning.

### Prediction verdicts

- **PV1**: **REFUTED** as stated. Predicted FP reduction did not occur —
  `no_workaround`/`scope_discipline`/FP are all numerically unchanged from
  baseline. The calibration framing had no measurable effect on this model's
  behavior at all.
- **PV2**: **REFUTED** as stated. Predicted `scope_discipline` recall
  improvement did not occur (still 0/8) despite the enumeration schema
  being partially followed (SC3/SC4 correctly listed 2 files). FP prediction
  (unchanged) was correct, but for a different reason than "V2 doesn't
  address the empty-array gap" — V2 never got far enough to test that,
  since it never even produces a scope-violation finding on the right file.
- **PV3**: **REFUTED** as stated. `scope_discipline` recall did not improve
  (0/8, same). FP rate did drop to 0/8 as predicted, but not via "the
  flagged-empty short-circuit is mechanically guaranteed for any clean case
  where pass 1 correctly answers both questions 'no problem'" — the
  diagnostics show pass 1 answers "no problem" unconditionally, on defect
  cases too (flagged=0/24, not flagged=0/8-clean-only-and-something-else-on-
  defects). The short-circuit fired on every case, defect or clean alike,
  which is not evidence of correct triage.
- **P-ceiling**: **CONFIRMED, and more strongly than the falsification
  criterion required.** The pre-registered ceiling signal was "V3
  false-positives on clean cases at a rate comparable to V1." What actually
  happened is more decisive: V3's pass-1 boolean returns "no problem" on
  100% of calls regardless of ground truth (defect or clean), i.e. it fails
  to discriminate in either direction. This is stronger evidence of a model
  ceiling on this narrower yes/no judgment than the originally-predicted
  failure mode (which would have looked like "still says yes too often");
  instead the model's narrower isolated boolean-schema judgment collapses to
  a blanket "no" — the mirror-image collapse of the baseline's blanket
  "yes, CRITICAL finding" under the original schema.

## Adjudication

**Binary question: does any variant reach false-positive rate ≤ ~0.1 with
recall ≥ 0.5? No.**

- V1: FP 1.00, recall 0.50 — fails the FP bar, unchanged from baseline.
- V2: FP 1.00, recall 0.50 — fails the FP bar, unchanged from baseline.
- V3: FP 0.00 (clears the FP bar) but recall 0.00 — fails the recall bar,
  and the FP=0 result is proven (via the pass-1 diagnostics, not inference)
  to be a mechanical artifact of the model never flagging anything, not
  genuine discrimination. It would not generalize to a corpus with a
  different defect/clean ratio; it is not a real result to build on.

**Verdict: model ceiling at 4B for this role, not an invocation-shape gap.**
Three invocation reshapes — explicit calibration language with a worked
example (V1), a schema-forced enumeration step (V2), and a full two-pass
triage-then-focus protocol (V3) — produced either zero measurable change
(V1, V2) or a change proven by the model's own diagnostic output to be a
non-discriminating artifact (V3). The two structural gaps iter-0055
identified (never emits empty array under the original schema; never
produces a finding about a diff's non-first file) persist under every
prompt/schema shape tried here, including one (V2) where the model
correctly enumerated the relevant file but still failed to judge it, and
one (V3) that isolated the "is there a problem" judgment into its own
narrow yes/no question and got a blanket wrong-direction answer. This
converges on a capability ceiling at the 4B parameter size for structured
multi-item defect judgment, not a prompt-engineering-solvable gap.

## Recommendation

**Do not add `ollama/gemma3:4b` to `pair_judge_priority` under any of the 4
invocation shapes measured to date** (iter-0055's baseline plus this
iteration's V1/V2/V3). This closes iter-0055's open follow-up — the
model-ceiling vs invocation-shape question — with a named, falsifiable
answer: **model ceiling**, evidenced by the pass-1 diagnostic data above,
not assumed.

The hybrid local pair-judge slot needs a different engine class to be
viable — a larger model (blocked today: `gemma3:12b` already exceeds the
repo's 8GB local-model cap per iter-0051), an API-tier model behind a local
adapter, or a different local model family entirely. Re-prompting the same
4B model is not a productive next step; no further invocation-shape
iteration on `gemma3:4b` is recommended without a capability change (larger
model, different architecture, or fine-tuning) to test against first.

No adapter update is proposed as a follow-up — none of the 3 variants won,
so there is no winning prompt shape to record as an `adapters/ollama.md`
candidate. The ollama adapter itself is unaffected by this iteration's
finding (the plumbing is sound per iter-0051/iter-0055; the finding is about
this specific model's judge-role ceiling, not the adapter contract).

No config changes made in this iteration, per scope.

## Artifacts

- `benchmark/probes/judge-quality/run_judge_invocation_variants.py` — new
  runner, imports `load_cases`/`score_response`/`matches_file`/
  `extract_json_object`/`FINDINGS_SCHEMA`/`OLLAMA_URL`/`OLLAMA_MODEL` from
  `run_judge_quality.py` unmodified; defines V1/V2/V3 prompt builders,
  schemas, and (for V3) unified-diff-by-file splitting + hunk resolution.
- `benchmark/probes/judge-quality/results/variant-{v1,v2,v3}/*.json` — raw
  per-case, per-rep records including the `_pass1_*`/`_pass2_calls`
  diagnostic fields — not committed, gitignored-equivalent by convention
  (matches iter-0055's `results/` handling; reproducible via the runner).
- Codex cross-check transcript: session-scratch only (not archived),
  reproducible via the same `codex-monitored.sh -s read-only -c
  model_reasoning_effort=high` invocation documented above.
