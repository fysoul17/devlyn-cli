# Headroom Gate — 20260512-f9-e2e-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: 0.0
Minimum bare headroom: 0
Average solo headroom: -10.0
Minimum solo headroom: -10

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F9-e2e-ideate-to-resolve | 60 | 0 | 90 | -10 | FAIL | bare headroom 0 < 5; solo_claude score 90 > 80; bare judge disqualifier |
