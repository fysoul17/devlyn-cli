# Headroom Gate — 20260511-f15-concurrency-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -39.0
Minimum bare headroom: -39
Average solo headroom: -14.0
Minimum solo headroom: -14

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F15-frozen-diff-race-review | 99 | -39 | 94 | -14 | FAIL | bare score 99 > 60; solo_claude score 94 > 80 |
