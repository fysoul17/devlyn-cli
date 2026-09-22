# 0210 — approved amendment; native preflight failed

2026-09-22. Root direct, no resolve. The user's approval is effective in
[AMENDMENT.md](AMENDMENT.md); it does not establish execution parity.
Public comparison: **NOT_RUN, 0/24 owner starts, 0 assessments**.
No efficacy, advancement, adoption or spending guarantee follows.

## Stopping attempt

The single registered capability preflight ran at12:23:39 UTC against source
`19e0da7`, image
`sha256:4f2080e5d128d112f1519703416db9a0d66098a3ece54655407c75b81e35eb86`.
Its prediction was one Astra/high owner, one native child and one Fable/medium
review with complete terminal accounting and local teardown.

Codex exited1 during configuration loading, before `thread.started` or any
session file. The sealed configuration attempted to set retry limits under
`[model_providers.openai]`; installed Codex0.155.1 rejects overriding a reserved
built-in provider ID. Authentication readiness and the synthetic custom-provider
control did not exercise this exact production configuration. Static source
review did not catch that gap. This is an orchestration setup failure, not a
model performance result or evidence of Linux capability parity.

Elapsed time including local teardown was0.293s; Docker reported exited/PID0,
then the exact container was removed. Raw controller classification is
`UNKNOWN` + `INFRA_INVALID`: no terminal usage was available. No model dispatch
was observed; absent counters are not fabricated as zero token usage. The
registered no-restart rule was honored: no replacement preflight, development
cell or model assessment followed. The rejected configuration remains sealed.

Raw evidence, relative to the retained0210 evidence directory:
`preflight/launch.json`, `preflight/input-seal.json`, `preflight/plan.json`,
`preflight/home/.codex/config.toml`, `preflight/run/{started,result}.json`,
`preflight/run/{stdout,stderr}`. A future execution requires a compatible retry
configuration and an explicitly registered new attempt; this result is never
silently relabeled PASS. The approved observational contract itself stands.

## Verified scope

- Seven optimized-Python accounting regressions passed. Native0.155.1 copies
  ancestor context before a child-specific settings boundary; the adapter checks
  ancestry and rejects copied usage instead of subtracting guessed counters.
  Credential-free native loopback reconciled parent40/4 plus child100/10 to
  input140/output14, including58 cached input tokens. This verifies the exercised
  reported-counter composition, not provider billing.
- Four container controls passed: normal completion, excess input, missing
  reviewer usage and deadline termination. A detached, TERM-ignoring descendant
  was contained and removed with the private PID namespace. Full-mount sandbox
  checks allowed workspace writes and rejected writes to the telemetry home.
- Three review-transport controls passed: normal completion, bounded timeout and
  rejection of the old incomplete-publication race. Testing found and fixed a
  relocated packet-import failure before the registered preflight. Earlier failed
  fixtures and the first misclassified loopback probe remain in the evidence.
- Actual Fable5.1 and Grok4.7 each reviewed the native binding three times. Both
  final reviews accepted **preflight source only**; neither approved runtime
  parity or the later failed attempt. Findings drove atomic review records and
  the final native-error rescan. Root rejected a conditional exception-handling
  finding because the existing AccountingError already subclasses ValueError.

Evidence: `native-accounting-tests.txt`, `counter-reconciliation.json`,
`counter-probe-r1/output/`, `nonmodel-r1/summary.json`, `mount-control/`,
`reviewer-controls-r1/summary.json`, `fable-native-final/`, `grok-native-final/`.
The experimental adapter remains unqualified for comparison execution. The
first real native child/review capability check and the public launch seal are
still incomplete. Original user edits and PR90's separately retained workspace
are outside this change.
