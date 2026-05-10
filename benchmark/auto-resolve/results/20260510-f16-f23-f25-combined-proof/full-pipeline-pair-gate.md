# Full-Pipeline Pair Gate - 20260510-f16-f23-f25-combined-proof

Verdict: **PASS**

Rule: at least 3 fixtures; bare <= 60; solo_claude <= 80; l2_risk_probes clean; pair_mode true; l2_risk_probes - solo_claude >= 5.
Max pair/solo wall ratio: 3.00x
Average pair/solo wall ratio: 1.73x

| Fixture | Bare | Solo | Pair | Margin | Pair mode | Wall ratio | Status | Reason |
|---|---:|---:|---:|---:|---|---:|---|---|
| F16-cli-quote-tax-rules | 50 | 75 | 96 | +21 | true | 1.28x | PASS |  |
| F23-cli-fulfillment-wave | 33 | 66 | 97 | +31 | true | 2.25x | PASS |  |
| F25-cli-cart-promotion-rules | 25 | 75 | 99 | +24 | true | 1.65x | PASS |  |
