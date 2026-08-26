# Headroom Gate — 20260511-f3-http-error-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -37.0
Minimum bare headroom: -37
Average solo headroom: -19.0
Minimum solo headroom: -19

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F3-backend-contract-risk | 97 | -37 | 99 | -19 | FAIL | bare score 97 > 60; solo_claude score 99 > 80 |
