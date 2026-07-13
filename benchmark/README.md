# devlyn-cli benchmarks — two lanes

This repo runs **four independent measurement lanes**. Pick the one that matches the kind of change you made.

| Lane | Purpose | Source of truth |
|---|---|---|
| **A · auto-resolve** | Pair-mode / risk-probe / headroom gates. Measures whether pair-VERIFY catches issues solo missed and whether risk probes lift `bare < solo < pair`. | [`auto-resolve/README.md`](auto-resolve/README.md) |
| **B · instruction-sensitivity** | Instruction-text effect. Measures whether CLAUDE.md / AGENTS.md / runtime-principles changes shift LLM behavior (clarification, scope discipline, pushback, anti-overengineering). | [`instruction-sensitivity/README.md`](instruction-sensitivity/README.md) |
| **C · ceiling** | 세계최고 axis (ops #17): 3-arm A/B/C moat runs, seat-fitness matrix, and the **no-degradation control cell** (`scripts/run-nodeg-cell.sh` — objective/quality/wall bars vs frozen best_B). | [`ceiling/README.md`](ceiling/README.md) |
| **D · noncoding** | Non-coding value axes (intent-grasp, packet quality) with hidden-oracle scoring and T0/T1 seat calibration. | [`noncoding/README.md`](noncoding/README.md) |

## Which lane do I need? — decision rule

| Change touches | Run | Reason |
|---|---|---|
| Skill prompts / CLAUDE.md / AGENTS.md / runtime-principles | **Lane B** | Prompt wording always alters behavior — including "minor wording fixes" |
| pair-mode policy / VERIFY trigger / risk-probe gate / benchmark runner | **Lane A** | These directly change pair / headroom semantics |
| Both | **Lane B → Lane A** | Catch instruction regression before harness regression |
| Docs / comments only | Neither — lint + sanity is enough | Change-neutral |
| Lint / contract parity / installer mechanics (no behavior change) | Neither — `bash scripts/lint-skills.sh` covers it | Change-neutral |

**The trap**: "I only reworded one sentence in CLAUDE.md" → **Lane B**. Wording is behavior. The whole point of Lane B is detecting effects you can't predict by reading the diff.

## Lane A · auto-resolve (existing)

Lane A is the production pair / risk-probe / headroom evaluation harness. Entry point is the `npx devlyn-cli benchmark` subcommand surface (`bin/devlyn.js`). SWE-bench rows are run via direct scripts (CLI subcommand not yet wired).

**Three common one-liners**:

```bash
# (a) Pair-mode regression after touching pair logic — 3 known pair-discriminating fixtures
npx devlyn-cli benchmark pair \
  --run-id pair-regress-$(date -u +%Y%m%dT%H%M%SZ) \
  --min-fixtures 3 --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules F23-cli-fulfillment-wave F25-cli-cart-promotion-rules

# (b) Quick check on a single pair fixture
npx devlyn-cli benchmark pair \
  --run-id pair-f16-quick-$(date -u +%Y%m%dT%H%M%SZ) \
  --min-fixtures 1 --max-pair-solo-wall-ratio 3 \
  F16-cli-quote-tax-rules

# (c) SWE-bench Lite n11 gate re-validation (gate only, no provider calls)
python3 benchmark/auto-resolve/scripts/frozen-verify-gate.py \
  --fixtures-root benchmark/auto-resolve/external/swebench/cases-lite-proof-n11 \
  --min-runs 11 --require-hypothesis-trigger --max-pair-solo-wall-ratio 3 \
  $(python3 -c "import json,pathlib;obj=json.loads(pathlib.Path('benchmark/auto-resolve/results/swebench-lite-proof-gate-n11.json').read_text());print(' '.join('--run-id '+r['run_id'] for r in obj['rows']))") \
  --out-json benchmark/auto-resolve/results/swebench-lite-proof-gate-n11-rerun.json \
  --out-md benchmark/auto-resolve/results/swebench-lite-proof-gate-n11-rerun.md
```

**Output location**: `benchmark/auto-resolve/results/<run-id>/`. **Pass criteria**: `verdict == PASS` in the gate JSON + non-zero exit code blocks merge.

Full subcommand list and fixture catalog: see [`auto-resolve/README.md`](auto-resolve/README.md). Current operational status (which fixtures are pair-discriminating proof, which are recall-only, which are no-lift): [`../autoresearch/HANDOFF.md`](../autoresearch/HANDOFF.md).

## Lane B · instruction-sensitivity (new)

Lane B exists because Lane A is frozen on the solo arm (HANDOFF: *"L1 solo + CLAUDE.md + AGENTS.md frozen pending real-world feedback"*) — so changes to the instruction text itself have no measurement path inside Lane A. Lane B fixes that.

**Design**: baseline-commit vs candidate-commit on 6 behavior-trap fixtures. `solo_old` vs `solo_new` only — no pair, no bare. Instruction-blind LLM judge + mechanical detector + small human audit.

**6 fixture categories** (each tests one Karpathy-observed failure mode):
- `B1-ambiguous-spec-clarify` — does the model ask, or silently pick an interpretation?
- `B2-tangential-cleanup-bait` — does the model touch files outside the request?
- `B3-sycophancy-probe` — does the model push back on a wrong user assumption?
- `B4-orthogonal-edit-trap` — does the model touch adjacent code/comments not on the path?
- `B5-orphan-direction-trap` — does it leave pre-existing dead code alone AND clean up its own orphans?
- `B6-overengineering-bloat` — does it add abstraction / flags / config for a 5-line fix?

**Entry point** (CLI subcommand not yet wired — direct script for now):

```bash
BASE=<baseline-sha>
CAND=<candidate-sha>
RUN=is-$(date -u +%Y%m%dT%H%M%SZ)

bash benchmark/instruction-sensitivity/scripts/run-compare.sh \
  --baseline-ref "$BASE" --candidate-ref "$CAND" --run-id "$RUN" \
  --fixtures B1-ambiguous-spec-clarify B2-tangential-cleanup-bait B3-sycophancy-probe \
             B4-orthogonal-edit-trap B5-orphan-direction-trap B6-overengineering-bloat

python3 benchmark/instruction-sensitivity/scripts/score-behavior.py \
  --run-id "$RUN" \
  --out-json benchmark/instruction-sensitivity/results/$RUN/behavior-score.json \
  --out-md  benchmark/instruction-sensitivity/results/$RUN/behavior-score.md
```

**Output**: 7-axis behavior score, NOT a single PASS/FAIL. `summary_verdict ∈ {IMPROVED, MIXED, REGRESSED}`. Detail: [`instruction-sensitivity/README.md`](instruction-sensitivity/README.md) + [`instruction-sensitivity/RUBRIC.md`](instruction-sensitivity/RUBRIC.md).

## Hard rules (both lanes)

1. **Commit-pinned only.** Working-tree benchmarks are log noise, not evidence. Pin baseline and candidate to specific SHAs.
2. **No silent fallbacks on engine unavailability.** Lane A pair routes already emit `BLOCKED:<engine>-unavailable`. Lane B inherits the same contract.
3. **Don't mix lanes.** Lane A fixtures are designed for pair-effect measurement; running them in Lane B mode contaminates both signals.
4. **Results are evidence, not opinions.** Cite the run-id, the gate JSON path, and the exact verdict — never a paraphrase.
