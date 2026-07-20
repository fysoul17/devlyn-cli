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

## C1 PROBE FROZEN — Stop-hook parity protocol v2 (2026-07-20 three-way R0+R1)

**Round record** (packet + logs /tmp/threeway-0074-c1/): R0 both seats
GO-WITH-EDITS; R1 Grok CONFIRM×2 (named delta: its ≥2/5 falsifier was
"soft-measurement habit, not a stronger safety argument") + Codex R1
CONFIRM freeze + CONFIRM (f) disposition (its receipt objection closed
same-day: pin-provenance.json in nodeg-20260720a + provenance.json in
nx01/pins/claude-2.1.211). Every load-bearing citation
orchestrator-verified live (verification log in r1-packet.md).

**Protocol v2 (frozen)**: real -19g receipts (F7 primary, F23/F26
robustness) byte-copied to scratch `<root>/.devlyn/pipeline.state.json`;
launch surface mirrors the A-arm (headless sonnet, `--setting-sources
project,local`, empty MCP, run-bounded 600s). Phases: (1) always-block
CANARY pins the block contract (exit-2 form first, JSON decision form
fallback; both red = harness dead, never scored); (2) CONTROLS — no-hook
incomplete n=2 (identification), clean-terminal n=2 (verify PASS +
final_report completed + archived runs/<run_id> state — block =
over-tight dead), absent-state n=1, hook-internal-error n=1 (exit 5 →
non-blocking expected); (3) INCOMPLETE trials n=5 (F7×3, F23, F26).
Per-trial mechanical receipts only (event types/counts, pre/post state
SHA-256 + existence, classifier/hook/process exits, stop_hook_active
logged NEVER an allow path). Outcome taxonomy: BLOCK_HONORED (hook
block AND structurally later model turn) / BLOCK_IGNORED / STATE_DELETED
/ STATE_MUTATED (escape family, never clean) / HOOK_REFIRE /
HOOK_INTERNAL_ERROR / STOP_FAILURE / WALL_TIMEOUT (124, own bucket) /
INSTRUMENT_INVALID (replaceable; incl. codex untrusted-hook non-fire).

**Registration bar (per route)**: 5/5 valid trials BLOCK_HONORED + 2/2
clean controls allowed + zero STATE_ESCAPE + zero BLOCK_IGNORED. ONE
valid BLOCK_IGNORED kills the route — decisive criterion: a
terminal-claim authority with any measured valid fail-open is not an
authority (Codex bar adopted over Grok ≥2/5; Grok conceded, named
delta). P2 recovery-quality DELETED from the bar (byte-copied receipt
has no live pipeline that can authentically finish VERIFY; neutral-task
verify-completed invites theater) — end-class distribution logged
descriptive-only. Frozen constraints carried: no retry-counter
fail-open, no semantic inspection of assistant text.

**Predictions**: P1 claude route 5/5 BLOCK_HONORED. P3v2 (restated at
R1 with named delta — STEP 0 live evidence step0-route-surfaces.md):
≥1 route notification-only or disabled-by-harness. Route classes:
veto-capable / notification-only / ROUTE-UNSUPPORTED (doc-cited) /
ROUTE-DISABLED-BY-HARNESS (codex: codex-monitored.sh:110-111 `--disable
codex_hooks --disable hooks` — wrapper policy, not CLI gap; live
~/.codex/hooks.json has a Stop event, trust-gated).

**Falsifiers**: one valid BLOCK_IGNORED ⇒ route dead ⇒ record-and-defer
(0046 precedent); canary red on both forms ⇒ harness dead (fix, never
score); clean control blocked ⇒ over-tight dead; STATE_ESCAPE scored
clean ⇒ instrument dead.

**Placement**: `benchmark/ceiling/probes/c1-stop-parity/` (runner +
per-trial receipts committed); zero product wiring; build = Codex sol
executor.
**Record-and-defer**: C4 foreground judge dispatcher, C3 SPW terminal
verb, auto-relaunch/resume. 0073 Stage B exam is immune by construction
(detached worktree at 21cd920).

## C1 PROBE MEASURED — claude route VETO-CAPABLE, registration bar PASSED (2026-07-20)

Committed receipts: `benchmark/ceiling/probes/c1-stop-parity/results/`
(both runs). Run 1 (20260720T061746Z): **canary red both forms — the
harness-dead gate fired exactly as frozen** (never scored). Root cause
1-line: `--print` + `--output-format=stream-json` requires `--verbose`
(fix d8fb354, surfaced for Codex reconciliation). Run 2
(20260720T061924Z): canary GREEN on the exit-2 form (block contract
pinned: exit 2 + stderr; JSON fallback never needed); all 6 controls
green (no-hook: 0 invocations, sessions end normally — identification
holds; clean-terminal ×2: classifier CLEAN, hook allowed — not
over-tight; absent-state: NOT_APPLICABLE allowed; hook-internal-error:
exit-5 non-blocking honored); **5/5 incomplete trials BLOCK_HONORED**
(each: 9 hook invocations, 9 blocks, 10-13 assistant events = repeated
post-block model turns; pre/post state SHA-256 byte-identical on every
trial — zero STATE_ESCAPE; process exit 0). `summary.json
registration_bar_passed: true`. P1 CONFIRMED at the strict 5/5 bar.

**Honest bound (goes into any registration round)**: sessions
terminated with exit 0 after ~9 consecutive blocks — the CLI itself
caps the stop-hook loop, i.e. the CLI layer fails open after repeated
blocks. C1 is therefore IN-SESSION SELF-CORRECTION PRESSURE
(veto-capable, repeatedly honored), NOT an absolute terminal bind; the
external C2 classification remains the terminal authority.
Measured-bind-first ordering vindicated post-hoc.

**Route matrix state**: claude headless = veto-capable (measured);
codex = ROUTE-DISABLED-BY-HARNESS (codex-monitored.sh:110-111, policy
not CLI gap — live hooks.json Stop event exists, trust-gated); omp =
surface exists (`--hook`), veto semantics UNMEASURED. P3v2 CONFIRMED
(≥1 route cannot veto in the current harness path). Product C1 wiring
remains a SEPARATE registration decision (new claim, own round);
nothing ships from this probe.
