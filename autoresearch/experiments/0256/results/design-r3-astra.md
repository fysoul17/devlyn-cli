**MEDIUM — Reset-aware reserve sampling remains unresolved.** [DESIGN.md:159](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/DESIGN.md:159) subtracts preflight utilization from verdict utilization without checking whether the window reset. A 20% → 5% transition can report −15 points despite positive consumption. Once the first panel cell replaces initialization, this can underreserve subsequent blocks. Waiting for resets at line 167 does not fix measurement across them. Define handling for changed reset timestamps and retain a conservative estimate when consumption is indeterminate. Also clarify line 168: historical estimates govern dispatch; they cannot guarantee total utilization stays below the caps. This remains a freeze blocker from Astra’s round-2 reserve finding.

Root correctly declined Grok’s `at_most` change. [DESIGN.md:189](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/DESIGN.md:189) is mathematically sound: complete candidate cost ≤ reference lower bound ≤ reference true cost. The existing function returns UNKNOWN when the candidate exceeds an incomplete reference bound. Read-only checks confirmed both directions and equality. Zero-success dominance is separately explicit.

All other round-2 findings are resolved at design level:

- Accounting now requires per-counter equality, terminal attempt coverage, and the exact 0239 negative control (lines 178–187).
- D3/D4 use unmodified current snapshots with frozen provenance (75–82).
- Renewal qualifies the host version, requires observed SMOKE renewal, permits one attempt per expiry, and refreshes assessor credentials (143–155).
- Reserve coverage includes both configurations and assessors; initialization, split blocks, owner priority, fault handling, and no-redraw rules are explicit (139–174).
- STOP/missing judgments, zero-success dominance, and paired severe-witness comparisons are covered (192–193, 220–228).
- Codex’s trust rewrite and the cited 44-line diff are corrected (34–37, 122–123).

**S/F are the only outstanding owner values for this replay**, explicitly recorded before SMOKE; 85/70 remains a recommendation ([DESIGN.md:156](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/DESIGN.md:156)). The powered study and next product candidate are future owner decisions; hold/stop rights are runtime discretion. The reserve fix requires an apparatus definition, not another owner choice.

REVISE
