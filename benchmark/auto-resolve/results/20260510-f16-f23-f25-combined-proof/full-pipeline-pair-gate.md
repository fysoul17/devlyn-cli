# Full-Pipeline Pair Gate - 20260510-f16-f23-f25-combined-proof

Verdict: **PASS**

Fixtures passed: 3/3 (minimum required: 3)

Rule: at least 3 fixtures; bare <= 60; bare headroom >= 5; solo_claude <= 80; solo_claude headroom >= 5; l2_risk_probes evidence-clean; pair_mode true; pair_trigger eligible with canonical reason; l2_risk_probes - solo_claude >= 5.
Average pair margin: +25.3
Allowed pair/solo wall ratio: 3.00x
Maximum observed pair/solo wall ratio: 2.25x
Average pair/solo wall ratio: 1.73x
Hypothesis trigger required: false

| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Pair | Margin | Pair mode | Hypothesis trigger | Triggers | Wall ratio | Status | Reason |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---:|---|---|
| F16-cli-quote-tax-rules | 50 | 10 | 75 | 5 | 96 | +21 | true | true | complexity.high,spec.solo_headroom_hypothesis | 1.28x | PASS |  |
| F23-cli-fulfillment-wave | 33 | 27 | 66 | 14 | 97 | +31 | true | true | complexity.high,spec.solo_headroom_hypothesis | 2.25x | PASS |  |
| F25-cli-cart-promotion-rules | 25 | 35 | 75 | 5 | 99 | +24 | true | true | complexity.high,spec.solo_headroom_hypothesis | 1.65x | PASS |  |
