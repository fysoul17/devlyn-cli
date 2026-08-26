# Headroom Gate — 20260511-f12-webhook-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -25.0
Minimum bare headroom: -25
Average solo headroom: -19.0
Minimum solo headroom: -19

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F12-webhook-raw-body-signature | 85 | -25 | 99 | -19 | FAIL | bare score 85 > 60; solo_claude score 99 > 80 |
