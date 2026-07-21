# iter-0078 — C1 product wiring: session-owned Stop-hook pressure, claude route (REGISTERED-FROZEN 2026-07-22)

**Why (pre-flight 0)**: K2a (invoke_exit 0 + phase open — the session ends its
turn while a pipeline phase is dispatched/open, headless wind-down kills the
work) is a repeated live death class with three receipts across cohorts:
probe-a iter0077 (sonnet backgrounded the BUILD_GATE Agent and ended its turn;
DECISIONS 0077.4), FS1 nodeg-20260721e, F25 nodeg-20260720e. C2 classifies
these correctly but only post-hoc — the row is already dead. The C1 Stop-hook
probe (0074.3) measured the ONLY in-session lever: claude route veto-capable,
5/5 BLOCK_HONORED, zero STATE_ESCAPE, clean controls green. iter-0074
explicitly deferred product wiring to its own registration — this is that
round. Production-ready principle: a hands-free product should not silently
self-terminate with verification incomplete when a measured in-session
correction pressure exists.

**Round record**: three-way R0+R1 2026-07-22 (packets + logs
/tmp/threeway-0078-c1w/). R0: BOTH seats GO-WITH-EDITS on all six questions;
independent convergence on active-state-only classification, installer hooks
merge, and synthetic-mechanism-probe predictions. R1: Grok CONFIRM FREEZE + 1
precision edit; Codex OBJECT + 2 precision edits (receipt-collision fix;
lint-mirror MATCH_COUNT=0 fresh measurement). Orchestrator adjudication:
Codex's receipt edit SUBSUMES Grok's (decisive criterion = the already-frozen
byte/tree-neutral controls; Grok's form still allowed a mismatch-receipt write
on foreign active state, violating control (c); Codex's zero-mutation-allow
form is the only self-consistent one — Grok's freeze precondition is satisfied
a fortiori). Orchestrator named deltas vs its own R0 packet: WITHDREW
"next cohort exercises the hook naturally" (stage_devlyn_context stages
config/skills + CLAUDE.md + AGENTS.md + engines.json, never
.claude/settings.json — run-ceiling-arm.sh:364-372); WITHDREW probe-a-replay
prediction (variance lottery — probe-b completed the identical row); bare
"classify" narrowed to active-state-only; fail-open direction frozen as a
NAMED DEVIATION from the probe hook (which blocked on classifier error,
stop-hook.py:138-142).

## Receipts (all orchestrator-opened live at citation time)

- Probe measurement: c1-stop-parity results 20260720T061924Z summary.json —
  registration_bar_passed true, 5/5 BLOCK_HONORED, canary exit2; run
  20260720T061746Z = canary-red harness-dead gate fired as frozen. Honest
  bound: CLI caps the stop-hook loop ~9 blocks then exit 0.
- K2a class: DECISIONS 0077.4 (probe-a mechanism from claude-debug.log:
  background Agent dispatch + "print wind-down" abort); FS1 -21e; F25
  -20260720e.
- Dead product path: package.json files ships `config`, NOT
  `benchmark/ceiling` → devlyn:queue/SKILL.md:22 classifier path is dead in
  installed products.
- Installer surface: bin/devlyn.js:768-803 merges env + permissions only — no
  hooks merge exists today.
- Latent tripwire: terminal-claim-check.py invocation_members (:227-) sweeps
  all `.devlyn/runs/*`; archive_run.py prune (:134-148) keeps in-flight runs
  forever; PER_RUN_PATTERNS (:25-28) has no hook-receipt pattern.
- Session channel: CLAUDE_CODE_SESSION_ID present in Bash env (CLI 2.1.216,
  live); host ~/.claude/hooks/devlyn-hook.mjs:35 parses stdin session_id; the
  probe hook validated only stop_hook_active (stop-hook.py:54-62) — session
  binding is an UNMEASURED delta, closed by the parity canary below.
- Schema policy: state-schema.md:1 — bump on breaking change only; zero
  session_id refs today; bootstrap init stamps run_id, no session
  (resolve-bootstrap.py:595-598), byte-exact self-test :713-719.
- Lint: critical_path_files MATCH_COUNT=0 for all four required surfaces
  (Codex R1 fresh measurement, orchestrator-confirmed list at
  lint-skills.sh:58-).
- Engine routing: SKILL.md:57 — the resolve session is the claude
  orchestrator even under executor=codex (child-process delegation); a
  claude-session Stop hook covers all claude-orchestrated resolve runs.
  codex route = ROUTE-DISABLED-BY-HARNESS only under CODEX_MONITORED_ISOLATED
  (codex-monitored.sh:105-114); omp unmeasured.

## Mechanisms (frozen; build = Codex sol; probe arms claude→sonnet, codex→terra)

1. **Single-source classifier**: move `terminal-claim-check.py` →
   `config/skills/_shared/` with TWO entrypoints in one module —
   active-state-only (C1 hook) and invocation-set (C2 drain/arm). Benchmark
   copy DELETED in the same commit, no shim. Callers updated:
   run-ceiling-arm.sh:21, run-c1-probe.py CLASSIFIER const,
   devlyn:queue/SKILL.md:19/22 (installed consumers resolve
   `$DEVLYN_SHARED_DIR`). `scripts/lint-skills.sh` adds
   `_shared/terminal-claim-check.py`, `_shared/resolve-stop-hook.py`,
   `_shared/resolve-bootstrap.py`, and `devlyn:queue/SKILL.md` to
   `critical_path_files`; drift in any of the four across installed mirrors
   fails lint. Fixes the dead product C2 path.
2. **`config/skills/_shared/resolve-stop-hook.py`** (adapted from the
   measured probe hook; exit-2 block form; stop_hook_active logged, NEVER an
   allow path): single read of active `.devlyn/pipeline.state.json` bytes,
   parse once — ownership AND classification from that same snapshot (TOCTOU
   closure). **Block ⇔ deterministic canonical root found ∧ active state
   exists ∧ same-snapshot classifier says INCOMPLETE ∧ state.session_id
   non-null ∧ equals hook session id** (stdin `session_id` preferred,
   CLAUDE_CODE_SESSION_ID env fallback). **Else allow without
   project-filesystem mutation; the allow reason is exposed only in hook
   process output. Hook errors, MALFORMED state, and unparsable stdin
   likewise allow without filesystem mutation (NAMED DEVIATION from the
   probe's block-on-error; C2 remains the fail-closed terminal authority —
   0074.1 unchanged). Only the owned same-session INCOMPLETE block path may
   write an archive-allowlisted, run-scoped receipt, bounded by the CLI block
   cap** (pattern added to archive_run.py PER_RUN_PATTERNS). Block stderr
   names the exact repair path (complete the open phase via SPW / honest
   BLOCKED terminal + archive).
3. **Bootstrap session stamp**: resolve-bootstrap.py writes `session_id` =
   CLAUDE_CODE_SESSION_ID (null-safe) at state init. Additive optional field;
   schema stays v3.0; schema doc line + byte-exact self-test extended. Honest
   bound documented: resume/compaction may rotate the id → fail-open
   thereafter (pressure inert, never wrong-block).
4. **Installer**: bin/devlyn.js non-destructive idempotent `hooks.Stop` merge
   (preserves all pre-existing user hooks/settings) + portable hook command
   path to the installed `_shared` home.
5. **Labels**: claude route only (measured); codex/omp route facts recorded;
   C1 = in-session pressure (CLI ~9-block cap), C2 = authority.

Decisive criteria (named, adopted): Measured Delta Closure (Codex Q1) ·
Session-Owned Active State (Grok Q1) · Same-Snapshot Session Ownership (Codex
Q3) · Shipped Single Oracle / Consumer-Reachable Single Source (Grok/Codex
Q2) · Causal Mechanism Probe ≠ Variance Replay / Antecedent-Conditioned
Replayability (Grok/Codex Q4) · Zero-Side-Effect Clean Turn (Codex Q5) ·
Byte+Resource Isolation (Codex Q6) · No-Suppression seniority (Block 8,
senior to all completion pressure).

## Frozen predictions

- **P-0078-K (mechanism, deterministic, primary)**: synthetic
  installed-project trial — active INCOMPLETE state stamped with session S;
  session S forced Stop → FIRST Stop = exit-2 block + repair-path stderr +
  state bytes SHA-identical; after honest terminal + archive, Stop allows.
  Includes the **session-parity canary**: bootstrap-visible env id == Stop
  stdin id recorded green BEFORE any scoring (else FS-0078-F).
- **P-0078-KL (live, antecedent-conditioned, report-only)**: only rows where
  {same-session ∧ incomplete-at-Stop} actually occurred are diagnostic → ≥1
  block and zero exit-0-with-open-phase; no antecedent → NON_DIAGNOSTIC,
  never a failure.
- **P-0078-O (senior, over-tight)**: FOUR clean controls, each zero blocks
  AND byte/tree neutrality (no file/dir created or mutated): (a) non-resolve
  session, absent state; (b) archived-clean state; (c) foreign-session stale
  INCOMPLETE active state; (d) archive-only foreign incomplete, current
  session clean.
- **P-0078-I (install)**: fresh npm install into a clean project → hook +
  classifier present and executable; pre-existing user settings/hooks
  byte-preserved; queue C2 path executes.
- **P-0078-C (roadmap, report-only)**: first hook-bearing cohort (post-0078
  SHA + runner settings-staging edit + explicit NEW-baseline label) shows K2a
  partition = 0. Never a revert trigger alone; never mixed into 0077
  aggregation.

## Falsifiers

- **FS-0078-A**: any clean control blocks OR mutates the tree → over-tight
  dead, revert.
- **FS-0078-B**: any cross-session block (incl. forced concurrent state swap
  / TOCTOU) → binding broken, redesign before ship.
- **FS-0078-C**: P-0078-K fails, OR a live antecedent row shows zero blocks →
  mechanism dead, record-and-defer (0046 precedent).
- **FS-0078-D**: hook internal error manifests as a block → fail direction
  wrong, fix before scoring.
- **FS-0078-E**: block driven solely by archived runs → over-tight, redesign.
- **FS-0078-F**: session channel dead (stdin id absent AND env absent, or
  parity canary red) → BLOCKED:design.
- **FS-0078-G**: canonical root discovery nondeterministic → whole-claim
  BLOCKED:design.
- **FS-0078-H**: installer clobbers or drops any pre-existing user
  hook/setting → fix before ship.

## Sequencing (frozen — Byte Isolation + Resource Isolation)

0077 Stage B launches ONLY from `exam-0077-probe @ ae9f9ae` (pre-0078 bytes —
no contamination path); 0078 build/probe activity NEVER overlaps the Stage B
quiet-window cohort (serialize — the cohort owns the machine); any hook
invocation appearing in a frozen-0077 A-arm row → contaminated row, re-run.
Post-0078 cohorts require the runner settings-staging edit and an explicit
hook-bearing NEW-baseline label.

**Out of scope (frozen)**: codex/omp route wiring; C2 semantic changes;
auto-relaunch/resume mechanisms; recovery-quality scoring (0074 P2 deletion
precedent); wall-lever claims (0077 owns them); corpus changes.

## Principles check

- **0**: closes the measured K2a in-session gap (3 live receipts) with the
  only measured in-session lever; production-ready visibility of incomplete
  terminals.
- **1**: root-cause pressure at the turn-end contract, not a symptom watcher;
  single-source classifier DELETES the benchmark copy; fixes the dead
  product C2 path instead of adding a parallel one.
- **2**: one hook + one stamp + one installer merge; no new flags; W-B/W-T0
  untouched; recovery machinery explicitly out of scope.
- **3**: every load-bearing claim opened live this session; two orchestrator
  packet claims withdrawn on seat evidence (named deltas above).
- **4/5**: measured probe mechanism reused byte-adapted; standard hooks
  surface; self-tests + parity canary before scoring.
- **6**: pressure layer is in-session (no new pair surface); probe is
  minutes-tier; cohort read rides the existing periodic exam.
- **7**: fail direction explicit and frozen; C2 authority unchanged; labels
  honest (pressure ≠ authority; claude-route-only).
