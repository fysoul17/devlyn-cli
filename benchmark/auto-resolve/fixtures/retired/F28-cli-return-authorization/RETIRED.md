# F28 Retirement

Retired from active golden fixtures on 2026-05-11.

Reason: F28 no longer has usable pair-lift headroom after the hidden oracle was corrected. Initial smoke runs `20260511-f28-headroom-smoke-085307` and `20260511-f28-pair-smoke-091021` were superseded by `20260511-f28-policy-oraclefix-reverified-pair`, which reverified the same provider diffs against the corrected oracle and scored bare 50 / solo_claude 98 / l2_risk_probes 96. That fails the solo headroom precondition and produces pair margin -2.

Keep this fixture only for diagnostics or historical replay. Rework or rotate it before using it for new solo_claude < pair evidence.
