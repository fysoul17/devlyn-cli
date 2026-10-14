# Accounting continuation fix — predictions before verification

2026-10-14. Offline only; no model review, network, Docker, GitHub, real
credentials, commit, or DESIGN.md edit.

The first read-only probe predicted that filtering the real case's transient
rows would either complete 0254 or expose a later failure. Observed: the two
rows are system api_retry/api_error, with no assistant API-error notice; the
filtered audit reports `orphan or missing body file`. It must remain STOP.

Before running the new tests: a valid synthetic owner/foreground-child receipt
set plus only system retry rows will grade once in measured phase. Retry plus
account/session mismatch, broken child lifecycle, foreign carrier, independent
launch, malformed counters, or body-index failure will STOP before grading.
Aggregate-only UNKNOWN and smoke will STOP. A matching nonnegative owner/whole
aggregate excess after an owner retry may remain UNKNOWN after grading, but
inconsistent or child-retry excess will STOP. Existing lifecycle order and
Codex's three counter patterns will remain unchanged.

After targeted checks pass, the README offline rp-d1 + rp-d2 suites are expected
to pass. Raw test output and the read-only real-case eligibility result will be
recorded separately after execution. The private real case is not retry-only;
its independent body inventory defect is retained, while synthetic receipts
isolate the positive and adversarial cases without storing real evidence.

Targeted run 1: 35 passed, 1 failed (`cont-fix-targeted.log`). The failing test
used bare `codex exec`, which unchanged 0234/0255 does not recognize in its
launch-only detector. The test now uses the inherited `codex-monitored.sh`
contract (also testing `claude -p` and the peer helper); older code stays frozen.
Before run 2: predict these cases pass, scope defects still STOP even after an
accepted aggregate gap, and nonnegative owner-only excess is eligible when the
whole aggregate reconciles. Incomplete invocation inventories, scope parser
errors and malformed receipt counters must also STOP.
