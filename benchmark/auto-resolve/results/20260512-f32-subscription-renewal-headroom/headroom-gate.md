# Headroom Gate — 20260512-f32-subscription-renewal-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: 27.0
Minimum bare headroom: 27
Average solo headroom: -18.0
Minimum solo headroom: -18

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F32-cli-subscription-renewal | 33 | 27 | 98 | -18 | FAIL | solo_claude score 98 > 80 |
