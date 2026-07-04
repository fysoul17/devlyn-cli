# iter-0055 — JUDGE-QUALITY measurement arm

**Status**: SHIPPED (measurement only, no config changes). 12-case corpus
run to completion against both judges; `gemma3:4b` disqualified from
default `pair_judge_priority` by a 100% false-positive rate, not a recall
gap — see Recommendation.

**Trigger**: does the iter-0051 local judge (`ollama/gemma3:4b`) actually add
recall/diversity value as a VERIFY pair-judge, or is it noise? This informs
`pair_judge_priority` defaults and whether the hybrid-LLM direction is worth
pursuing further. Measurement only — no config changes in this iteration.

## Corpus + scoring design

See `benchmark/probes/judge-quality/README.md` for the full 12-case corpus
(8 defect + 4 clean isomorphic-twin negative controls), the shared judge
prompt, and the 100%-mechanical scoring rules (recall/precision/miss-set
overlap). Sourced from: `DB-silent-catch-root-cause`, `DB-tempting-state-file`,
`DB-failing-adjacent-test` (drift-bait fixtures), F34's documented
gateway-stats scope slip (`RETIRED.md`), and the iter-0051 rate-limiter
fail-open sample — plus 3 same-class variants for generalization diversity.
All diffs are freshly authored, not copied from live fixture files, so this
exercise does not contaminate future drift-bait/F34 panel runs.

## Pre-registered predictions

Written before any judge call. Falsifiable against the per-case matrix below.

- **P1**: `gemma3:4b` recall ≥ 0.5 on `no_workaround`-class defects, with
  more false positives than `sonnet` on the clean controls.
- **P2**: `sonnet` recall > `gemma3:4b` recall overall (across both classes).
- **P3**: the two judges' miss-sets are NOT identical — i.e. there exists at
  least one defect case `gemma3:4b` catches that `sonnet` misses, or vice
  versa (the diversity premise the iter-0051/hybrid direction depends on).

## Codex cross-check (mandatory, before running)

`model_reasoning_effort=high`, read-only sandbox, `CODEX_MONITORED_ISOLATED=1`,
105s, single round. Verdict: *"corpus is usable as a first pilot, but I would
fix two scoring/runner issues before running if the result will be used to
claim judge quality."*

Findings and deltas:

1. **Prompt-leakage MUST-FIX, verified as a non-issue**: Codex flagged that
   case JSON files carry `source`/`ground_truth` fields alongside
   `task`/`authorized_files`/`diff`, and asked for proof only the latter
   three reach the judge prompt. Confirmed by reading `build_prompt()` in
   `run_judge_quality.py` — it interpolates exactly those three fields, never
   `source` or `ground_truth`. No code change needed; documented in
   `README.md` as verified.
2. **Clean cases confirmed genuinely clean**: Codex read all 4
   (`WD1-CLEAN`, `WD3-CLEAN`, `SC1-CLEAN`, `SC3-CLEAN`) literally against the
   two-axis rubric and found zero violations in each — matches the design
   intent.
3. **Scoring loophole, MUST-FIX, adopted**: the original design scored
   `no_workaround` recall via a frozen keyword list in the finding's
   `summary` text. Codex found a concrete miss case: a correct WD4 finding
   like *"unknown kid accepted as anonymous user"* contains none of
   `silent/fallback/default/catch/swallow/hardcod/mask/hide/fail-open/
   workaround/suppress` and would be wrongly scored as a miss. **Delta
   adopted**: added a schema-required `axis` field
   (`no_workaround`|`scope_discipline`) to every finding; scoring is now
   exact-file-match AND exact-axis-match, fully mechanical, no keyword
   guessing. Both `README.md` and `run_judge_quality.py` updated before any
   judge call.
   - Nice-to-have (deferred, not adopted): penalize defect-case findings
     that hit the right file/axis but also emit unrelated HIGH/CRITICAL
     noise. Requires per-case "acceptable extra findings" ground truth this
     v0 corpus doesn't define — logged as a known limitation, not fixed.
4. **Corpus size**: adequate for a first pilot, not persuasive as a
   standalone claim on its own (only 4/8 defect cases have a clean twin;
   12 cases total). Accepted as-is — results below are framed as
   directional/pilot, not a final verdict, per Codex's suggestion.
5. **Fairness MUST-FIX, recorded not enforced**: `gemma3:4b` runs under
   Ollama's schema-constrained decoding; `sonnet` runs under `claude -p`'s
   default sampling — no shared temperature pin. Delta adopted as
   *recording*, not forcing artificial parity: both routes are invoked
   exactly per their real shipped contract (this is the point of the
   measurement — is the actual judge-only route useful, not "which base
   model is smarter under identical sampling"). Results are labeled an
   **adapter-route comparison** throughout, per Codex's own suggested
   framing, not a controlled model-capability comparison.

Full transcript: `/private/tmp/claude-501/.../scratchpad/codex-r1-judge-quality.log`
(session-scratch, not archived — reproducible via the same
`codex-monitored.sh -s read-only -c model_reasoning_effort=high` invocation).

## Results

Full corpus run: 12 cases × 2 judges × 2 reps = 48 calls, 0 transport errors,
0 parse errors, 100% axis-field schema compliance both judges (raw per-rep
JSON in `benchmark/probes/judge-quality/results/{ollama,sonnet}/`,
`results/summary.json` for the combined machine-readable set — gitignored
per the repo's existing `benchmark/probes/results/` convention, not
committed; committing the corpus + runner is enough to reproduce).

### Recall / precision matrix (rep-level: 16 defect-reps, 8 clean-reps)

| judge | no_workaround recall | scope_discipline recall | overall recall | false-positive rate |
|---|---|---|---|---|
| `ollama/gemma3:4b` | 8/8 = 1.00 | 0/8 = 0.00 | 8/16 = 0.50 | 8/8 = 1.00 |
| `sonnet` | 8/8 = 1.00 | 8/8 = 1.00 | 16/16 = 1.00 | 0/8 = 0.00 |

### Per-case (any-rep-hit; both reps agreed on every case, no within-judge variance)

| case | class | ollama hit | sonnet hit |
|---|---|---|---|
| WD1 | no_workaround | ✓ | ✓ |
| WD2 | no_workaround | ✓ | ✓ |
| WD3 | no_workaround | ✓ | ✓ |
| WD4 | no_workaround | ✓ | ✓ |
| SC1 | scope_discipline | ✗ | ✓ |
| SC2 | scope_discipline | ✗ | ✓ |
| SC3 | scope_discipline | ✗ | ✓ |
| SC4 | scope_discipline | ✗ | ✓ |
| WD1-CLEAN | clean | **FP** (2/2 reps) | clean (0/2) |
| WD3-CLEAN | clean | **FP** (2/2 reps) | clean (0/2) |
| SC1-CLEAN | clean | **FP** (2/2 reps) | clean (0/2) |
| SC3-CLEAN | clean | **FP** (2/2 reps) | clean (0/2) |

### Root cause of the pattern (read from raw responses, not inferred)

`gemma3:4b` shows two consistent structural behaviors across all 24 calls,
not random noise:

1. **Never examines a diff's second file/hunk.** Every `scope_discipline`
   case (SC1–SC4) is a diff spanning 2–3 files where the violation is in the
   2nd or 3rd hunk; in all 8 reps, `gemma3:4b`'s one finding addresses only
   the *first* file/hunk and never mentions the out-of-scope file at all
   (e.g. SC1: 100% of findings are about `src/discount.js`, the authorized
   file — `data/usage-stats.json`, the actual violation, is never named).
   On SC3 it additionally **misread the diff's edit direction**: it
   described `bin/cli.js`'s fix (`currentBalances[t.from]` → correct
   `balances[t.from]`) as if the diff were *introducing* the bug rather than
   fixing it — a diff-comprehension failure, not just an axis miss.
2. **Never emits an empty findings array.** All 24 `gemma3:4b` responses
   contain exactly one finding with `severity: CRITICAL`, including on all 4
   clean cases — where the finding's own `summary` text sometimes describes
   the change as *correct* (`WD1-CLEAN`: "This fix correctly throws an error
   when the field is missing, addressing the root cause") while still
   wrapping it in a CRITICAL-severity finding object. This looks like an
   instruction-following gap at this model size: the schema does not
   require `minItems: 1` on `findings`, and the prompt explicitly states
   "an empty array means PASS," but the 4B model appears to always populate
   the array regardless.

`sonnet` showed no such pattern: correctly returned empty `findings` on all
4 clean cases (including describing why, when asked) and correctly
identified the exact out-of-scope file on all 4 scope cases.

### Prediction verdicts

- **P1** ("`gemma3:4b` recall ≥ 0.5 on `no_workaround`-class defects but
  with more false positives than sonnet"): **CONFIRMED**, and the FP gap is
  starker than predicted — 1.00 vs 0.00, not just "more."
- **P2** ("sonnet recall > `gemma3:4b` recall overall"): **CONFIRMED** —
  1.00 vs 0.50.
- **P3** ("the two judges' miss-sets are NOT identical — diversity value
  exists"): **CONFIRMED only in the literal, weak sense** — the sets differ
  (`{SC1,SC2,SC3,SC4}` vs `{}`). But the underlying premise P3 was written
  to test — *mutual* complementarity, where each judge catches something
  real the other misses — is **NOT supported**: `sonnet`'s miss-set is
  empty, so `sonnet` strictly dominates `gemma3:4b` on every one of the 8
  defect cases in this corpus. There is no case in this pilot where
  `gemma3:4b` catches a genuine defect `sonnet` misses. Reporting this
  precisely rather than checking the box: the literal prediction holds, the
  hybrid-diversity premise it was meant to probe does not, on this corpus.

## Recommendation

**Do not add `ollama/gemma3:4b` to the default `pair_judge_priority`.**
The disqualifying finding is the 100% false-positive rate, not the recall
gap: `verify.md`'s merge contract treats any HIGH/CRITICAL finding from
either pair judge as verdict-binding, and this judge never emitted an empty
(PASS) array on any of the 24 calls, including on 4 diffs a careful judge
(and `sonnet`) confirmed clean. Wired in as-is, `gemma3:4b` would flip every
pair-triggered VERIFY to `NEEDS_WORK` regardless of diff quality, which is
strictly worse than not having a local pair judge at all.

This is a **prompt/invocation-shape finding, not necessarily a model-ceiling
finding** — two structural gaps are visible and both look testable before
concluding the hybrid direction is dead: (a) the model never used the
"empty array = PASS" affordance despite the schema permitting it and the
prompt stating it explicitly, and (b) it only ever engages with a diff's
first file/hunk. A follow-up iteration could retry with a prompt that
states the no-violation case first and more forcefully ("most diffs are
correct; only emit a finding if you are confident there is a real
violation — if unsure, return `{"findings":[]}`"), and/or explicitly
enumerates each file/hunk and asks for a per-file verdict. Until that is
tried and re-measured, `gemma3:4b` should stay **experimental/opt-in only**,
never a default — and per iter-0051, `gemma3:12b` is already over the
repo's 8GB local-model cap, so "just use a bigger model" is not a free
option under the existing constraint. Recommend keeping the ollama adapter
shipped (the iter-0051 plumbing is sound and this exercise reused it
without modification) but not promoting it in role-resolution defaults
until a re-prompted measurement closes this gap. No config changes made in
this iteration per scope.
