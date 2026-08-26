# Headroom Gate — 20260507-f10-f11-tier1-full-pipeline

Verdict: **FAIL**

Rule: at least 2 fixtures; bare <= 60, solo_claude <= 80, both arms clean.

| Fixture | Bare | Solo | Status | Reason |
|---|---:|---:|---|---|
| F10-persist-write-collision | 75 | 94 | FAIL | bare score 75 > 60; solo_claude score 94 > 80 |
| F11-batch-import-all-or-nothing | 98 | 97 | FAIL | bare score 98 > 60; solo_claude score 97 > 80 |
