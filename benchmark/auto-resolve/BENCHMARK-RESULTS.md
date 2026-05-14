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

The following require REAL `/devlyn:resolve` pipeline executions on real tasks. Hypotheses from prior design docs remain labeled as hypotheses until run:

- **Wall-clock time per route** — requires running the full pipeline with timing.
- **Actual token consumption** (Codex + Claude) — requires running with token accounting enabled.
- **Fix-round convergence** — how often does `max_rounds` exhaust vs settle?
- **Criterion verification correctness** in production-like scenarios — requires real BUILD + EVALUATE on real code.
- **False-positive escalation rate** (Stage B escalates when it shouldn't) — needs a population of realistic tasks.
- **Fix-batch packet efficiency** (tokens saved vs re-parse) — needs instrumented runs.

`run-real-benchmark.md` documents the procedure. 30 paired runs across the 3 tiers = ~7.5–15 hours execution time and is out of scope for this commit.

## 3.0 Current benchmark snapshot (provider-free, 2026-05-14)

Generated from local gate artifacts with:

```bash
npx devlyn-cli benchmark recent
npx devlyn-cli benchmark audit --require-hypothesis-trigger --out-dir /tmp/devlyn-benchmark-audit-strict
```

Status:

- Verdict: **PASS**
- Active fixtures: 21
- Rejected controls: 17
- Pair evidence rows: 4
- Unmeasured candidates: 0

Pair lift:

- Average margin: **+27.25**
- Minimum margin: **+21**
- Average wall ratio: 1.66x
- Maximum wall ratio: 2.25x
- Gate: margin >= +5; wall <= 3.00x

Evidence cards:

### F16 cli quote tax rules

- Scores: bare 50, solo_claude 75, pair 96.
- Lift: +21; wall 1.28x; arm `l2_risk_probes`.
- Run: `20260510-f16-f23-f25-combined-proof`.
- Triggers: `complexity.high`, `spec.solo_headroom_hypothesis`.

### F21 cli scheduler priority

- Scores: bare 33, solo_claude 66, pair 99.
- Lift: +33; wall 1.47x; arm `l2_risk_probes`.
- Run: `20260511-f21-current-riskprobes-v1`.
- Triggers: `complexity.high`, `risk.high`, `risk_probes.enabled`,
  `spec.solo_headroom_hypothesis`.

### F23 cli fulfillment wave

- Scores: bare 33, solo_claude 66, pair 97.
- Lift: +31; wall 2.25x; arm `l2_risk_probes`.
- Run: `20260510-f16-f23-f25-combined-proof`.
- Triggers: `complexity.high`, `spec.solo_headroom_hypothesis`.

### F25 cli cart promotion rules

- Scores: bare 25, solo_claude 75, pair 99.
- Lift: +24; wall 1.65x; arm `l2_risk_probes`.
- Run: `20260510-f16-f23-f25-combined-proof`.
- Triggers: `complexity.high`, `spec.solo_headroom_hypothesis`.

## 3.1 Full-pipeline pair evidence (measured 2026-05-09, expanded 2026-05-11)

Run set: `20260510-f16-f23-f25-combined-proof`

Gate:

```bash
python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  --run-id 20260510-f16-f23-f25-combined-proof \
  --pair-arm l2_risk_probes \
  --min-fixtures 3 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3
```

Result: **PASS**. All three fixtures satisfy the headroom precondition,
including the default 5-point `bare`/`solo_claude` headroom margins. Pair mode actually
fired, the pair arm was clean, and the blind judge scored pair above `solo_claude` by
more than the +5 margin floor.

| Fixture | Bare | Solo_claude | Pair (`l2_risk_probes`) | Margin | Pair mode | Wall ratio |
|---------|-----:|-----:|------------------------:|-------:|-----------|-----------:|
| F16-cli-quote-tax-rules | 50 | 75 | 96 | +21 | true | 1.28x |
| F23-cli-fulfillment-wave | 33 | 66 | 97 | +31 | true | 2.25x |
| F25-cli-cart-promotion-rules | 25 | 75 | 99 | +24 | true | 1.65x |

Average pair margin: **+25.3**.
Average pair/solo wall ratio: **1.73x**.
Headroom summary before pair measurement: average bare headroom **24.0**,
minimum bare headroom **10**, average solo_claude headroom **8.0**, minimum solo_claude
headroom **5**.

Earlier two-fixture run `20260509-f16-f25-combined-cartprobe-v2` also passed
the current gate for F16/F25 with margins +21 and +24, average pair margin
+22.5, and average pair/solo wall ratio 1.46x.

Supporting focused run: `20260509-f25-cartprobe-v2` closed the previous F25
gap. The `l2_risk_probes` arm passed 4/4 fixture verification commands, produced
a two-file diff, and scored 99 vs `solo_claude` 75.

Additional focused run: `20260511-f21-current-riskprobes-v1` re-measured F21
with the current risk-probe path and passed the same full-pipeline gate with
`--min-fixtures 1`. Scores: `bare` 33, `solo_claude` 66, `l2_risk_probes` 99, pair margin
+33, pair mode true, pair/solo wall ratio 1.47x. This is supporting fixture
evidence for the same pair mechanism and is counted by `benchmark audit` as the
fourth passing pair-evidence row alongside the F16/F23/F25 proof run.

Rejected candidate: `20260508-f26-headroom` measured F26 payout ledger rules at
bare 25 / solo_claude 98, so it fails the headroom precondition (`solo_claude <= 80`)
despite being a useful ledger arithmetic control fixture.

Rejected candidate: F22 ledger close reached ceiling in both available headroom
runs (`20260507-f21-f22-full-pipeline-pair`: bare 91 / solo_claude 98;
`20260508-f22-exact-error-headroom`: bare 94 / solo_claude 98). It is a control
fixture, not counted pair-lift evidence.

Rejected candidate: `20260511-f27-headroom-smoke-061401` measured F27
subscription proration at bare 33 / solo_claude 94. It fails the headroom precondition
(`solo_claude <= 80`) and bare passed only 1 of 3 verification commands, so it
must not be counted as pair evidence until it is reworked or rotated and clears
a fresh headroom gate.

Rejected candidate: F28 return authorization is not pair-lift evidence. Earlier
unstable runs `20260511-f28-headroom-smoke-085307` and
`20260511-f28-pair-smoke-091021` were superseded after a hidden-oracle bug was
found. The oracle had expected a defective item to bypass expiration, which the
visible spec does not require. After re-verifying the same provider diffs
against the corrected oracle, `20260511-f28-policy-oraclefix-reverified-pair`
scored bare 50 / solo_claude 98 / `l2_risk_probes` 96, margin -2, and failed
headroom. Rework or rotate F28 before spending more pair arms.

Rejected candidate: `20260511-f30-headroom-v1` measured F30 credit hold
settlement at bare 33 / solo_claude 98. It fails the headroom precondition
(`solo_claude <= 80`) and must not be counted as pair evidence until it is
reworked or rotated.

Rejected candidate: `20260511-f15-concurrency-headroom` measured F15 frozen-diff
race review at bare 99 / solo_claude 94. It fails both headroom preconditions
and should remain a frozen-diff review control unless reworked to expose a lower
solo ceiling.

Rejected candidate: `20260511-f3-http-error-headroom` measured F3 backend
contract risk at bare 97 / solo_claude 99 after tightening the invalid-query
HTTP error body verifier. It fails both headroom preconditions and should remain
a backend contract control unless reworked.

Rejected candidate: `20260512-f2-medium-headroom` measured F2 medium CLI at
bare 83 / solo_claude 95. It has a positive solo-over-bare margin, but both
baseline scores exceed current headroom ceilings, so it remains a medium CLI
control fixture rather than pair-lift evidence.

Rejected candidate: `20260512-f4-web-headroom` measured F4 web browser design at
bare 70 / solo_claude 92, with a +22 solo-over-bare margin. It fails headroom
because both baseline scores exceed the ceilings and bare also carries
judge/result/verify disqualifiers. Rework F4 before spending a pair arm.

Rejected candidate: `20260512-f5-fixloop-headroom` measured F5 fix-loop at bare
99 / solo_claude 99, with bare and solo each passing 5/5 verification commands.
It fails both headroom preconditions and should remain a fix-loop control unless
reworked.

Rejected candidate: `20260512-f6-checksum-headroom` measured F6 dep-audit
checksum at bare 97 / solo_claude 96, with bare and solo each passing 6/6 verification
commands. It fails both headroom preconditions and should remain a dep-audit
control unless reworked.

Rejected candidate: `20260512-f7-scope-headroom` measured F7 scope discipline
at bare 99 / solo_claude 100, with bare and solo each passing 6/6 verification
commands. It fails both headroom preconditions and should remain a scope-control
fixture unless reworked.

Rejected candidate: `20260512-f9-e2e-headroom` measured F9 ideate-to-resolve at
bare 60 / solo_claude 90, with a +30 solo-over-bare margin and passing F9
artifact checks. It fails headroom because bare headroom is 0 < 5, solo exceeds
80, and bare carries a judge disqualifier. Keep F9 as the novice-flow anchor,
but rework it before spending pair arms as pair evidence.

Rejected by design: F1 is a trivial calibration fixture where every arm is
expected to one-shot; F8 is a known-limit ambiguity barometer with expected
margin in [-3, +3]. Neither should be used as pair-lift evidence.

Rejected candidates: `20260507-f10-f11-tier1-full-pipeline` measured F10
persistent write collision at bare 75 / solo_claude 94 and F11 batch import at
bare 98 / solo_claude 97. Both fail headroom and should remain control fixtures
unless reworked.

Rejected candidate: `20260511-f12-webhook-headroom` measured F12 webhook
signature/replay at bare 85 / solo_claude 99. Bare passed 6/7 verification
commands and solo passed 7/7, but the blind judge scores still exceed both
headroom ceilings, so F12 should remain a webhook/security control unless
reworked.

Rejected candidate: `20260512-f31-seat-rebalance-headroom` measured F31 seat
rebalance at bare 33 / solo_claude 98. Bare had 1/3 verification commands
passing and carried judge/result/verify disqualifiers; solo passed 3/3. F31
therefore fails the solo_claude headroom precondition and must not receive a pair arm
unless reworked.

## 4. Conclusions (evidence-based only)

**Confirmed**:
1. Zero-copy migration is complete: 28 → 0 legacy monolithic artifact references in SKILL.md.
2. Structured-artifact adoption is complete: 54 structured references (`pipeline.state.json` + `findings.jsonl`).
3. Goal-driven prompt adoption: 10 additional `<goal>/<output_contract>/<quality_bar>/<principle>` blocks across BUILD/EVALUATE/CHALLENGE.
4. Routing logic produces the designed outcomes for 3 representative test cases covering all 3 routes.
5. Monotonicity invariant holds: `fast ⊆ standard ⊆ strict`.
6. Full-pipeline pair evidence now clears the three-fixture gate for F16 + F23
   + F25: `l2_risk_probes` beats `solo_claude` by +21, +31, and +24 points with
   average pair margin +25.3, pair mode true, and average pair/solo wall ratio
   1.73x.
7. F21 also clears a focused full-pipeline gate after current-risk-probe
   remeasurement: 33 / 66 / 99 with pair margin +33 and wall ratio 1.47x, and
   is counted by `benchmark audit` as the fourth passing pair-evidence row.
8. F26 is rejected as pair-lift evidence because `solo_claude` reaches ceiling: bare 25 /
   solo_claude 98 in `20260508-f26-headroom`.
9. F22 is rejected as pair-lift evidence because both `bare` and `solo_claude` reach ceiling
   in available headroom runs.
10. F27 is rejected as pair-lift evidence in its first headroom smoke: bare 33 /
    solo_claude 94, with bare verification 1/3.
11. F28 is rejected as pair-lift evidence. A hidden-oracle bug was corrected,
    then `20260511-f28-policy-oraclefix-reverified-pair` reverified the same
    provider diffs at bare 50 / solo_claude 98 / pair 96, margin -2, so the fixture is
    ceiling-saturated for `solo_claude` and should be reworked or rotated.
12. F30 is rejected as pair-lift evidence in its first headroom run:
    `20260511-f30-headroom-v1` scored bare 33 / solo_claude 98.
13. F15 is rejected as pair-lift evidence in `20260511-f15-concurrency-headroom`:
    bare 99 / solo_claude 94, so the fixture is ceiling-saturated.
14. F3 is rejected as pair-lift evidence in `20260511-f3-http-error-headroom`:
    bare 97 / solo_claude 99, so the fixture is ceiling-saturated.
15. F2 is rejected as pair-lift evidence in `20260512-f2-medium-headroom`:
    bare 83 / solo_claude 95, so both baseline scores exceed headroom ceilings.
16. F4 is rejected as pair-lift evidence in `20260512-f4-web-headroom`:
    bare 70 / solo_claude 92 with bare disqualifiers, so it needs rework first.
17. F5 is rejected as pair-lift evidence in `20260512-f5-fixloop-headroom`:
    bare 99 / solo_claude 99, so the fixture is ceiling-saturated.
18. F6 is rejected as pair-lift evidence in `20260512-f6-checksum-headroom`:
    bare 97 / solo_claude 96, so the fixture is ceiling-saturated.
19. F7 is rejected as pair-lift evidence in `20260512-f7-scope-headroom`:
    bare 99 / solo_claude 100, so the fixture is ceiling-saturated.
20. F9 is rejected as pair-lift evidence in `20260512-f9-e2e-headroom`:
    bare 60 / solo_claude 90 with bare headroom 0 and a bare judge disqualifier.
21. F1 and F8 are rejected by design as calibration/known-limit controls, not
    pair-lift evidence candidates.
22. F10 and F11 are rejected as pair-lift evidence in
    `20260507-f10-f11-tier1-full-pipeline`: F10 scored bare 75 / solo_claude 94, and
    F11 scored bare 98 / solo_claude 97.
23. F12 is rejected as pair-lift evidence in `20260511-f12-webhook-headroom`:
    bare 85 / solo_claude 99, so the fixture is ceiling-saturated.
24. F31 is rejected as pair-lift evidence in
    `20260512-f31-seat-rebalance-headroom`: bare 33 / solo_claude 98, with bare
    disqualifiers and `solo_claude` at ceiling.
25. F32 is rejected as pair-lift evidence in
    `20260512-f32-subscription-renewal-headroom`: bare 33 / solo_claude 98, so the
    subscription renewal fixture is solo-ceiling despite useful rollback/shape
    coverage.

**Still hypothetical** (pending real-run validation):
- Wall-time reduction for `fast` route on trivial tasks.
- Token consumption reduction from fix-batch packet.
- Overall pipeline throughput change beyond the measured F16/F23/F25 pair gate
  and focused F21 pair evidence.

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
  --run-id 20260510-f16-f23-f25-combined-proof \
  --pair-arm l2_risk_probes \
  --min-fixtures 3 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3

# Additional focused F21 evidence
python3 benchmark/auto-resolve/scripts/full-pipeline-pair-gate.py \
  --run-id 20260511-f21-current-riskprobes-v1 \
  --pair-arm l2_risk_probes \
  --min-fixtures 1 \
  --min-pair-margin 5 \
  --max-pair-solo-wall-ratio 3
```
