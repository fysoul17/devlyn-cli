# Headroom Gate — 20260510-f16-f23-f25-combined-proof

Verdict: **PASS**

Fixtures passed: 3/3 (minimum required: 3)

Rule: at least 3 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: 24.0
Minimum bare headroom: 10
Average solo_claude headroom: 8.0
Minimum solo_claude headroom: 5

| Fixture | Bare | Bare headroom | Solo_claude | Solo_claude headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F16-cli-quote-tax-rules | 50 | 10 | 75 | 5 | PASS |  |
| F23-cli-fulfillment-wave | 33 | 27 | 66 | 14 | PASS |  |
| F25-cli-cart-promotion-rules | 25 | 35 | 75 | 5 | PASS |  |
