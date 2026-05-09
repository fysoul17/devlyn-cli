# Auto-Resolve Benchmark Results (v2.1)

Date: 2026-04-22
Baseline ref: `4eb7b47` (v1.14.0 — CPO lens in ideate + handoff enforcement)
Head ref: v2.1 STEP 5 complete (commit `5859959`)

This report separates **measured** properties from **hypothesized** properties. Any number in this file without an explicit measurement script behind it is not reported.

## 1. Static properties (measured via `measure-static.py`)

| Metric | Baseline | Head | Delta | Interpretation |
|--------|---------|------|-------|----------------|
| `SKILL.md` lines | 602 | 645 | +43 | Slight growth from routing logic + structured output contracts. Offset by phase-prompt concision. |
| `SKILL.md` tokens estimate | 10,817 | 14,438 | +3,621 | ~4 chars/token estimate. Head has denser lines (more content per line) due to structured contracts. |
| Legacy monolithic artifact refs | 28 | 0 | **−28** | `BUILD-GATE.md` / `EVAL-FINDINGS.md` / `done-criteria.md` / `SPEC-CONTEXT.md` / etc. completely removed. |
| Structured artifact refs | 0 | 54 | **+54** | `pipeline.state.json` + `findings.jsonl` references (structured, machine-parseable). |
| Goal-driven XML blocks | 3 | 13 | **+10** | `goal` / `output_contract` / `quality_bar` / `principle` / `harness_principles` adoption on BUILD/EVALUATE/CHALLENGE. |
| Reference files | 2 (build-gate, engine-routing) | 5 (+findings-schema, pipeline-state, pipeline-routing) | +3 | Forward-declared schemas + routing matrix. On-demand loaded, not always in context. |

**Measured reading**: the orchestrator's *potential* context surface grew from 922 → 1,590 lines (+668). In practice, reference files are loaded on-demand per phase — the orchestrator rarely carries all 1,590 lines at once. The ~28→0 removal of legacy artifact references and ~0→54 adoption of structured references IS always in orchestrator context since both live in SKILL.md.

## 2. Route trace simulations (measured via `trace-route.py`)

All 3 test cases produce the expected routing outcome. **3/3 match.**

| Test case | Expected route | Measured route | Phase count | Match |
|-----------|---------------|----------------|-------------|-------|
| T1-trivial (CLI typo, complexity=low) | `fast` | `fast` | 4 | ✓ |
| T2-standard (order cancel, complexity=medium, web files) | `standard` | `standard` | 8 (includes browser) | ✓ |
| T3-high-risk (session token rotation, auth keywords) | `strict` | `strict` | 10 | ✓ |

### Stage A decision traces

- T1: `spec.complexity=low, 0 risk keywords → fast`
- T2: `spec.complexity=medium, 0 risk keywords → standard`
- T3: `risk keyword hit: ['auth', 'session', 'token']... → strict` (correctly force-escalates regardless of complexity)

### Phase inclusion matrix validation

Monotonicity holds: `fast ⊆ standard ⊆ strict`. Each route adds phases on top of the previous, never removes.

## 3. What is NOT measured here (future work)

The following require REAL auto-resolve pipeline executions on real tasks. Hypotheses from prior design docs remain labeled as hypotheses until run:

- **Wall-clock time per route** — requires running the full pipeline with timing.
- **Actual token consumption** (Codex + Claude) — requires running with token accounting enabled.
- **Fix-round convergence** — how often does `max_rounds` exhaust vs settle?
- **Criterion verification correctness** in production-like scenarios — requires real BUILD + EVALUATE on real code.
- **False-positive escalation rate** (Stage B escalates when it shouldn't) — needs a population of realistic tasks.
- **Fix-batch packet efficiency** (tokens saved vs re-parse) — needs instrumented runs.

`run-real-benchmark.md` documents the procedure. 30 paired runs across the 3 tiers = ~7.5–15 hours execution time and is out of scope for this commit.

## 3.1 Full-pipeline pair evidence (measured 2026-05-09)

Run set: `20260509-f16-f25-combined-cartprobe-v2`

Gate:

```bash
python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  --run-id 20260509-f16-f25-combined-cartprobe-v2 \
  --pair-arm l2_risk_probes \
  --min-fixtures 2 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3
```

Result: **PASS**. Both fixtures satisfy the headroom precondition, pair mode
actually fired, the pair arm was clean, and the blind judge scored pair above
solo by more than the +5 margin floor.

| Fixture | Bare | Solo | Pair (`l2_risk_probes`) | Margin | Pair mode | Wall ratio |
|---------|-----:|-----:|------------------------:|-------:|-----------|-----------:|
| F16-cli-quote-tax-rules | 50 | 75 | 96 | +21 | true | 1.28x |
| F25-cli-cart-promotion-rules | 25 | 75 | 99 | +24 | true | 1.65x |

Average pair/solo wall ratio: **1.46x**.

Supporting focused run: `20260509-f25-cartprobe-v2` closed the previous F25
gap. The `l2_risk_probes` arm passed 4/4 fixture verification commands, produced
a two-file diff, and scored 99 vs solo 75.

## 4. Conclusions (evidence-based only)

**Confirmed**:
1. Zero-copy migration is complete: 28 → 0 legacy monolithic artifact references in SKILL.md.
2. Structured-artifact adoption is complete: 54 structured references (`pipeline.state.json` + `findings.jsonl`).
3. Goal-driven prompt adoption: 10 additional `<goal>/<output_contract>/<quality_bar>/<principle>` blocks across BUILD/EVALUATE/CHALLENGE.
4. Routing logic produces the designed outcomes for 3 representative test cases covering all 3 routes.
5. Monotonicity invariant holds: `fast ⊆ standard ⊆ strict`.
6. Full-pipeline pair evidence now clears the two-fixture gate for F16 + F25:
   `l2_risk_probes` beats `solo_claude` by +21 and +24 points with pair mode
   true and average pair/solo wall ratio 1.46x.

**Still hypothetical** (pending real-run validation):
- Wall-time reduction for `fast` route on trivial tasks.
- Token consumption reduction from fix-batch packet.
- Overall pipeline throughput change beyond the measured F16/F25 pair gate.

## 5. Reproducing

```bash
# Static
python3 benchmark/auto-resolve/measure-static.py \
  --baseline 4eb7b47 --head HEAD

# Route trace (all test cases)
python3 benchmark/auto-resolve/trace-route.py --all

# Single test case
python3 benchmark/auto-resolve/trace-route.py --test-case T3-high-risk

# Full-pipeline pair gate evidence
python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  --run-id 20260509-f16-f25-combined-cartprobe-v2 \
  --pair-arm l2_risk_probes \
  --min-fixtures 2 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3
```
