# Headroom Gate — 20260512-f7-scope-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -39.0
Minimum bare headroom: -39
Average solo headroom: -20.0
Minimum solo headroom: -20

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F7-out-of-scope-trap | 99 | -39 | 100 | -20 | FAIL | bare score 99 > 60; solo_claude score 100 > 80 |
