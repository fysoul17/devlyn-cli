# iter-0074 STUB — terminal-claim integrity (premature terminal during VERIFY): DESIGN ROUND ONLY

**Why this iter exists (pre-flight 0)**: twice-observed live class, now
fired on the credited current-stack row nodeg-20260719f: the session
backgrounded the primary VERIFY judge (transcript `run_in_background:
true`), then ended its turn with terminal_reason "completed" while
`phases.verify.verdict=None`, `completed_at=null`, no PHASE-6 archive
(watcher `BLOCKED:watcher:archived-state-missing`). A hands-free product
that self-reports "completed" with verification incomplete violates the
production-ready principle independently of any benchmark gate
(0072 SHIP-CREDITED residual 1; 0072.9 completed-dirty family).
Mission 1 product-liveness surface.

**License (three-way R0 2026-07-19, both seats GO-WITH-EDITS)**: DESIGN
ROUND ONLY. Build is licensed only if a mechanism can mechanically bind
or veto the externally visible terminal claim after the model ends its
turn — launcher/lifecycle-owned state check, resumable supervisor, or
equivalent Terminal-Claim Authority (Codex criterion). Explicitly NOT
licensed: prose reminders, skill bullets, PHASE-6-only gates, or
watcher-only post-hoc labeling that cannot change the emitted terminal
claim (Grok falsifier). If design converges to "no clean mechanical
bind" → record-and-defer (iter-0046 classes-2/3 precedent), no theater.

**Candidate surfaces to stress-test in the design round (priority order,
Grok R0)**: (i) finish-gate / state-writer refuses "completed" without
verify.verdict + archive receipt; (ii) driver/arm classifies
FAILED-INCOMPLETE when `verify.started_at && !completed_at`; (iii)
structural unskippability of the judge wait (foreground-only spawn
contract enforced by wrapper, not prose). Known hard constraint: no SPW
hook can force the model to continue a turn it has ended — the binding
surface must live in whatever process OWNS the terminal claim.

**Sequencing**: separate registration from iter-0073 (single-claim
discipline, Codex R0); the design round may run while 0073's Stage B
exam is detached. Entry = three-way design round with a frozen packet
citing the -19f receipts (pipeline.state.json, transcript, watch.log).
