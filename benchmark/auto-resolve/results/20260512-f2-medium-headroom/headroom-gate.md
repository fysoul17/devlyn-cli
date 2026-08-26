# Headroom Gate — 20260512-f2-medium-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -23.0
Minimum bare headroom: -23
Average solo headroom: -15.0
Minimum solo headroom: -15

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F2-cli-medium-subcommand | 83 | -23 | 95 | -15 | FAIL | bare score 83 > 60; solo_claude score 95 > 80 |
