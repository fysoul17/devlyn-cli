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

## DESIGN FROZEN — C2 terminal-claim binding (2026-07-19 three-way converged R0+R1, zero dissent)

**Round record** (packet /tmp/threeway-0074-r0/; logs codex-r0/grok-r0 +
codex-r1/grok-r1): R0 divergence Codex C1>C2 vs Grok C2>C1; orchestrator
adjudication criterion = **Measured-bind-first** (ship the binding whose
authority receipts already prove; probe the unmeasured one). R1 = BOTH
seats 5/5 CONFIRM, FREEZE-GO. Grok withdrew its isolation-strips-hooks
counter (named delta: claude-isolation.py:305-306 loads project,local in
the A-arm); Codex accepted the skip-eval rejection (named delta: -19f
objective resolved:true proves objective validity separable from
pipeline completeness) and the C1 deferral its own falsifier 3 implies.

**Build contract (Codex sol executor)**:
1. `benchmark/ceiling/scripts/terminal-claim-check.py` (stdlib,
   read-only, deterministic): classifier over
   `<root>/.devlyn/pipeline.state.json` → NOT_APPLICABLE (file absent)
   / INCOMPLETE:<phase> (started_at set, completed_at null; verify
   additionally requires non-null verdict) / INCOMPLETE:final_report
   (verify PASS/PASS_WITH_ISSUES, final-report completion absent) /
   INCOMPLETE:archive (final report done, root state not archived) /
   MALFORMED (unreadable/invalid active state — treated incomplete,
   fail-closed). Exit 0 = NOT_APPLICABLE or clean; exit 79 = incomplete
   (distinct — 78 is DEPS_STAGING_BLOCKED_EXIT, run-nodeg-cell.sh:48).
2. Benchmark binding: run-ceiling-arm.sh, ARM=A, after CLI return +
   devlyn-snapshot: run the check against the worktree; on incomplete
   write receipt `$RESULT_DIR/terminal-claim.json` {status, phase,
   reason, run_id} and record `terminal_outcome: FAILED-INCOMPLETE` in
   timing.json; final arm exit becomes 79 ONLY when it would otherwise
   be 0 (never masks 86/78/124). Eval/judge continuation stays
   driver-owned.
3. Product hands-free binding: queue-drain outer-loop contract line —
   after each resolve invocation the drain runs terminal-claim-check
   and marks `[F] FAILED-INCOMPLETE` instead of trusting the session's
   self-report. Mechanical primitive + minimal contract line; no new
   SPW write verb.
4. Self-tests: -19f topology fires INCOMPLETE:verify; clean full-PASS
   state → exit 0 silent; absent state → NOT_APPLICABLE silent;
   malformed JSON → 79; exit-code precedence (86/78/124 never
   overridden by 79).

**Falsifiers (pre-registered)**: F1 replay -19f state → arm still
records success ⇒ dead. F2 clean full-PASS trips predicate ⇒ over-tight
dead. F3 non-resolve session trips ⇒ scope dead. F4 malformed treated
as allow ⇒ fail-closed dead. F5 exit-79 collision or missing receipt on
fire ⇒ binding dead.

**Licensed follow-up (separate claim, NOT this build)**: C1 Stop-hook
parity probe — replay -19f state in a scratch project with a
project-scope hook installed; measure block honoring on
claude/codex/omp × headless-first. C1 registration only after per-route
measurement; frozen constraints from Codex R0: no retry-counter
fail-open, no semantic inspection of assistant text.
**Record-and-defer**: C4 foreground judge dispatcher, C3 SPW terminal
verb, auto-relaunch/resume. 0073 Stage B exam is immune by construction
(detached worktree at 21cd920).
