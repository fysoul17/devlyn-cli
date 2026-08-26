# Headroom Gate — 20260512-f4-web-headroom

Verdict: **FAIL**

Fixtures passed: 0/1 (minimum required: 1)

Rule: at least 1 fixtures; bare <= 60 with headroom >= 5, solo_claude <= 80 with headroom >= 5, both baseline arms evidence-complete.
Average bare headroom: -10.0
Minimum bare headroom: -10
Average solo headroom: -12.0
Minimum solo headroom: -12

| Fixture | Bare | Bare headroom | Solo | Solo headroom | Status | Reason |
|---|---:|---:|---:|---:|---|---|
| F4-web-browser-design | 70 | -10 | 92 | -12 | FAIL | bare score 70 > 60; solo_claude score 92 > 80; bare judge disqualifier; bare result disqualifier; bare verify disqualifier |
