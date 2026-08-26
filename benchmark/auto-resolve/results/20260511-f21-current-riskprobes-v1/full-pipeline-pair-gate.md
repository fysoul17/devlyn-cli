# Full-Pipeline Pair Gate - 20260511-f21-current-riskprobes-v1

Verdict: **PASS**

Fixtures passed: 1/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60; bare headroom >= 5; solo_claude <= 80; solo_claude headroom >= 5; l2_risk_probes evidence-clean; pair_mode true; pair_trigger eligible with canonical reason; l2_risk_probes - solo_claude >= 5.
Average pair margin: +33.0
Allowed pair/solo wall ratio: 3.00x
Maximum observed pair/solo wall ratio: 1.47x
Average pair/solo wall ratio: 1.47x
Hypothesis trigger required: false

| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Pair | Margin | Pair mode | Hypothesis trigger | Triggers | Wall ratio | Status | Reason |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|---|
| F21-cli-scheduler-priority | 33 | 27 | 66 | 14 | 99 | +33 | true | true | complexity.high,risk.high,risk_probes.enabled,spec.solo_headroom_hypothesis | 1.47x | PASS |  |
