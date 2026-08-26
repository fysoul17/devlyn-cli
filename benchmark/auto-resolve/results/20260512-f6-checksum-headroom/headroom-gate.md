# Headroom Gate — 20260512-f6-checksum-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -37.0
Minimum bare headroom: -37
Average solo headroom: -16.0
Minimum solo headroom: -16

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F6-dep-audit-native-module | 97 | -37 | 96 | -16 | FAIL | bare score 97 > 60; solo_claude score 96 > 80 |
