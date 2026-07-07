# iter-0066 — pre-VERIFY overhead levers (scoped checkpoint commits + probe-derive boundary + turn batching + round history)

status: CLOSED 2026-07-07 — levers A/B/D SHIPPED and live-verified on a
full SW2-shaped re-run (3157s, exit 0, every phase + both judges PASS —
the run that hit the 3600s cap in tranche-1); lever C (turn batching)
FALSIFIED by its own pre-registered gate and DELETED same-day (L5).
probe_derive 484.0 → 204.6s; git-sweep BUILD_GATE-FAIL class structurally
closed; failed rounds now attributable in state (`rounds_history`, live
capture on first run). R0 SHIP-WITH-EDITS → R1 VALID-WITH-EDITS; R1's Q5
REFUTE fired the hash-binding falsifier → probe-artifact digest
(`state.risk_probes_digest`) + probes archive shipped in-iter. P6
attention-cost gate FAILED-as-frozen (+2.81% final vs ≤ +1%),
adjudicated openly (R1 Q3: no deletable sentence survives; freeze
mis-calibration). Archives `/tmp/codex-iter0066/`.
R0 record: all 5 MUST-FIX adjudicated (4 adopted, MF5 hash-binding half
deferred with a named position that R1 then falsified — flipped per the
named-delta rule); 3 SHOULD-FIX adopted. Predictions P1-P6 frozen before
implementation; P1/P2 tightened per R0 (tightening adds falsifiers,
never removes one).

**Serves**: Mission 1 ceiling axis (NORTH-STAR ceiling contract / ops test #17).
Tranche-1 verdict was FAIL-pilot on LC3 efficiency; iter-0065 closed FS1-class
delivery + bounded pair-VERIFY and explicitly left pre-VERIFY overhead as "the
only unowned efficiency root" (HANDOFF entry point #1). This iter owns it.

## Why this exists (pre-flight 0)

One sentence: this iter removes three measured pre-VERIFY overhead classes
observed in `benchmark/ceiling/results/iter0064-t1/SW2-django-13265/A1/` —
(a) a 336s self-inflicted BUILD_GATE FAIL+repair caused by the skill's own
`git add -A` checkpoint contract, (b) a 484s probe_derive phase whose deriver
mutated the target implementation and hand-fought JSON escaping, and (c)
~165s of micro-turn bookkeeping — and makes failed-round wall-time
attributable in state so the next LC3 decomposition cannot be mis-attributed
the way iter-0065's was.

Mission-bound (#7): Mission 1, ceiling contract / ops test #17 — tranche 2
re-measures LC3 after this lever ships; without it the wall axis stays lost.

## Evidence (all opened this session, 2026-07-07)

Primary artifact: SW2 A1 (`iter0064-t1`, wall 3600s cap, exit 124).
Pre-VERIFY = 2205s (run start 19:15:32Z → verify.started_at 19:52:17Z).

- `pipeline.state.json` (workspace `.devlyn/`): plan 151.0s, probe_derive
  484.0s, implement 781.7s, build_gate 147.1s **round:1**, cleanup 138.5s.
- Session transcript `~/.claude/projects/...SW2.../fc04d8d6*.jsonl`: Agent
  spawn 19:41:19 "BUILD_GATE for Django autodetector fix" ran 254.5s
  (TaskOutput 19:45:35) and FAILed; the 19:47:20 round-1 re-spawn prompt
  states round 0 failed because "the orchestrator's checkpoint commit had
  accidentally swept in 512 unrelated pipeline-harness scaffold files via
  `git add -A`". Orchestrator repair 19:45:35→19:46:57 (~82s): `git reset
  --soft HEAD~1`, re-add of only the two authorized files.
- **Named delta vs iter-0065's decomposition** ("~503s orchestrator gaps
  before VERIFY"): new evidence (subagent session transcripts, unopened in
  0065) re-attributes 336s of that to a hidden failed BUILD_GATE round 0 +
  repair. True inter-phase micro-turn overhead is ~165s (SW2) / 172s (SW1
  gaps, archived state `rs-20260706T173818Z`). State hid the failed round
  because `state-phase-write.py spawn` resets the phase record per round.
- probe_derive subagent transcript (`agent-ae4595d868ab681b1.jsonl`, 386s of
  the 484s phase): 3 Edits on `django/db/migrations/autodetector.py`
  19:22:31–19:22:48 (deriver implemented a candidate fix to prove its probe
  passes post-fix), test run, `git checkout --` revert 19:24:11 — ~100s;
  then 5 python-heredoc attempts serializing a multiline `python -c` into
  the JSONL `cmd` string 19:24:26→19:25:35 — ~90s. Output: ONE probe (1843
  bytes).
- Contract sources: `SKILL.md:217` (`git add -A && git commit` single-phase
  checkpoint), `:222` (phase-gated), `:259` (cleanup);
  `references/phases/build-gate.md:25` enforces PLAN's `authorized_surface`
  against the diff; `references/phases/plan.md:18` makes PLAN declare it.
  The commit command and the enforcement disagree by construction whenever
  pre-existing untracked files exist.
- Phase-wrap overhead: plan phase 151s vs plan subagent 52s
  (`agent-ae8934c300439a0bc.jsonl`) — ~99s of orchestrator micro-turns
  around one spawn; debug-log timeline shows ~50 turns of 0.0–0.5s Bash +
  API round trip in the implement→build_gate window alone.
- Provenance notes (R0 "Unreproduced" items): the SW1 172s figure is a
  computation, not a stored number — sum of inter-phase gaps from the
  archived state's own phase timestamps
  (`SW1.../A1/.../.devlyn/runs/rs-20260706T173818Z-154f1464bd70/pipeline.state.json`);
  subagent transcripts live under the session directory
  `~/.claude/projects/<workspace-slug>/<session-id>/subagents/`, not the
  workspace.
- **Second lever-D observation — FS1 A2** (iter-0065 P1 attempt 2, archived
  run `rs-20260707T095913Z-b801a3df3a4c`): phases 1226s vs gaps 1870s;
  implement recorded as round:1 with a 1443s gap before it (hidden round 0
  + correction loop), verify round:2 with a 356s gap. Both multi-round runs
  observed to date hide their failed/superseded rounds in state.

## Lever A — checkpoint commits scoped to the authorized surface (MUST)

### Why-chain → violated invariant

1. Why did BUILD_GATE round 0 FAIL? `scope.out-of-scope-file` CRITICAL —
   512 pre-existing untracked files entered the implement checkpoint commit.
2. Why were they in the commit? `SKILL.md:217` prescribes `git add -A`,
   while the same pipeline's PLAN declared an `authorized_surface` that
   BUILD_GATE enforces. **Violated invariant: a checkpoint commit must
   contain exactly the authorized work; the prescribed command commits the
   entire worktree state.** Depth 2; stop.

The scope gate (iter-0046) worked as designed — it caught the leak. But
catching costs a full failed round (254.5s) + repair (~82s) per occurrence.
Fix the contract so the leak is impossible at commit time; the gate remains
for its own class (IMPLEMENT writing files outside the surface).

### Fix (post-R0)

- IMPLEMENT checkpoints (`SKILL.md:217`, `:222` phase-gated, **and the
  BUILD_GATE fix-loop repair commit — R0 MUST-FIX 3, `SKILL.md:242` path**):
  stage via `git add --pathspec-from-file` on the concrete file list printed
  by a new `spec-verify-check.py --print-authorized-surface` mode — never
  `-A`. **Pathspec parity by construction (R0 MUST-FIX 2)**: the flag
  resolves the surface (incl. `dir/**` entries) to existing changed/new
  files using the SAME matching code the gate enforces
  (`spec-verify-check.py:288,1203,1230`), so staging and enforcement cannot
  diverge, and `git add` never sees a non-matching pathspec (authorized
  paths PLAN declared but IMPLEMENT did not create cannot fail the add).
- **Fail-loud untracked delta (R0 MUST-FIX 1, decisive criterion
  fail-loud-over-silent-drop)**: today the sweep is what made out-of-scope
  NEW files visible to the gate (`git diff` sees them only once committed —
  `spec-verify-check.py:1065`). Scoped staging alone would convert that
  loud CRITICAL into a silent untracked leftover. Fix: PHASE 0 records the
  untracked baseline (`.devlyn/untracked.baseline`, sorted
  `git status --porcelain` untracked list); the BUILD_GATE authorized-surface
  check also compares current untracked files against baseline ∪
  authorized_surface (`.devlyn/` exempt as harness state) — any new
  unauthorized untracked file → `scope.out-of-scope-file` CRITICAL, same
  finding id, same fix rule (remove it, never widen the surface). Loudness
  preserved; the 336s failed-round tax and the reset repair are gone.
- CLEANUP commit (`SKILL.md:259`): `git add -u` (tracked
  modifications/deletions only). Cleanup's allowlist is artifacts, dead code
  added by this diff, and stale doc references — none legitimately creates a
  new untracked deliverable. **Fail-loud complement (R0 SHOULD-FIX 3)**: the
  existing post-CLEANUP scope check extends to untracked delta vs baseline —
  a cleanup-created untracked file is an allowlist violation finding, not a
  silent leftover.
- Closes as the same class: `.devlyn/` harness state can no longer enter
  pipeline commits in a real user repo. (`.git/info/exclude` for `.devlyn/`
  stays a separate HANDOFF follow-up — it guards the USER's own commits,
  out of this iter's scope.)

## Lever B — probe-derive worktree boundary + mechanical emission (MUST)

### Why-chain → violated invariant

1. Why 484s for one probe? The deriver implemented a candidate fix in the
   target file to validate the probe post-fix (~100s incl. revert), then
   hand-escaped a multiline command into JSON five times (~90s).
2. Why did it do that? The contract demands executable, mechanically
   validated probes but is silent on validation boundaries and emission
   ergonomics: nothing forbids mutating tracked files, and the inline-JSON
   `cmd` format makes a nontrivial probe adversarial to serialize.
   **Violated invariant: probe derivation is read-only with respect to
   tracked files (pre-IMPLEMENT worktree integrity), and emitting a valid
   probe must be mechanical, not a serialization fight.** Depth 2; stop.

The edit-test-revert cycle is also an unpriced integrity hazard: an
incomplete revert would hand IMPLEMENT a polluted base. Observed cost this
run is wall only; the fix removes both.

### Fix (post-R0)

- `references/phases/probe-derive.md`: explicit boundary — the deriver MUST
  NOT modify tracked files; pre-implementing the candidate fix to prove the
  probe passes post-fix is out of contract (that is IMPLEMENT +
  BUILD_GATE's job). Validation = execute the probe against `base_ref` and
  confirm the command runs to its assertion. **Base-outcome classification
  (R0 MUST-FIX 4)**: a bug-exposing probe fails on base for the right
  reason; a preservation/regression probe (its `derived_from` names
  unchanged behavior, e.g. "pre-existing tests continue to pass")
  legitimately PASSes on base. Either outcome is valid evidence the probe
  executes; universal fail-on-base is NOT required.
- Probe bodies may be script files under `.devlyn/probes/<id>.<ext>` written
  by the deriver, with `cmd` invoking them (e.g. `python3
  .devlyn/probes/P1.py`). Inside the worktree, persists through the run,
  BUILD_GATE/VERIFY replay unchanged. **Exception (mechanical validator
  compatibility)**: solo-headroom-hypothesis probes keep the hypothesis's
  backticked observable command inline in `cmd`
  (`validate_risk_probes_cover_solo_headroom_hypothesis` checks `cmd`
  containment — `spec-verify-check.py:420`).
- **Script content scanning (R0 MUST-FIX 5, first half; independently found
  by the orchestrator pre-R0)**: `FORBIDDEN_RISK_PROBE_CMD_RE` +
  `external_url_hosts` scan only the `cmd` string
  (`spec-verify-check.py:650`). When `cmd` references `.devlyn/probes/`
  files, the validator scans each referenced file's content with the same
  rules — at load time, so it binds at derive validation AND at every
  BUILD_GATE/VERIFY replay.
- **Hash-binding deferred (R0 MUST-FIX 5, second half — named position for
  R1)**: R0 asked replay to bind a script hash against post-derive
  mutation. Position: script files do not widen the pre-existing surface —
  `risk-probes.jsonl` itself is writable by later phases in the same
  `.devlyn/` trust domain and its `cmd` is equally rewritable today; the
  self-authorization class predates this iter. Real closure needs an
  orchestrator-held digest in `pipeline.state.json` (the
  `source.criteria_sha256` precedent) covering the jsonl AND scripts —
  logged as a follow-up candidate, not smuggled into this iter's scope.
  Falsifier accepted: evidence of an actual post-derive probe mutation in
  any run flips this to MUST immediately.
- NOT shipped, logged: probe-derive.md quality_bar slimming (fixture-domain
  blocks: cart/pricing, FEFO/warehouse, webhook HMAC). No observed wall
  linkage to instruction length this run; deleting measured probe-strength
  rules risks re-opening F16/F23/F25-class weakness. Surfaced as a
  thermometer-discipline doc follow-up, not an efficiency lever.

## Lever C — bookkeeping turn batching (SHOULD; measured, deletable)

Observed: ~50 micro-turns (each a 0.0–0.5s Bash + full API round trip) in
SW2's inter-phase windows ≈165s; SW1 gaps 172s; ~99s wrap around a 52s plan
subagent. Fix: one sentence in SKILL.md's run rules — consecutive mechanical
bookkeeping steps (state-phase-write call, jq/python validation, announce
line) with no intervening decision are combined into a single Bash
invocation; engine wrapper calls stay solitary and foreground (iter-0065
rule and iter-0009 observability contract untouched). Prose-ceiling risk is
acknowledged (iter-0058/0062); the E1 precedent (one sentence flipped sonnet
B4 4/4→1/4) is the existence proof a single targeted sentence can move
sonnet behavior. Measured by P3; deleted on L5 if it does not move turns.

## Lever D — per-round phase timing history (SHOULD; measurement integrity)

Observed: build_gate round 0 (254.5s) exists only in the session transcript;
`pipeline.state.json` shows round:1 only, because `state-phase-write.py
spawn` resets the phase record per round (by design, iter-0042). This
corrupted iter-0065's decomposition and would corrupt tranche-2 LC3
attribution the same way. Fix: `spawn` appends the superseded round's
`{round, started_at, completed_at, duration_ms, verdict, triggered_by}` to
`phases.<name>.rounds_history[]` before resetting; `state-schema.md`
documents it. Read-side consumers unchanged (additive field).

## Predictions (frozen before implementation; retroactive edits are dishonest)

Measurement vehicle: one SW2-shaped A-arm re-run (same task django-13265,
sonnet headless orchestrator, executor=codex pin, `--pair-verify`, high-risk
so probe_derive fires — iter-0064 A-arm invocation shape via
`run-ceiling-arm.sh` mechanics), plus self-tests and a trivial smoke. Test
arms sonnet/codex only; Fable orchestrates the iteration, never an arm.

- **P1 (lever A, deterministic)**: every `chore(pipeline):` commit in the
  re-run contains only paths within PLAN's `authorized_surface` (cleanup:
  tracked-file changes only); pre-existing untracked scaffold remains
  untracked at run end; zero `scope.out-of-scope-file` findings caused by
  pre-existing untracked files. Mechanism: the staging command can no longer
  express the sweep. **Fail-loud clause (R0 POS-1 falsifier adopted)**: a
  planted unauthorized NEW untracked file (created post-baseline in a
  synthetic gate test) still raises `scope.out-of-scope-file` CRITICAL — if
  it stays silent, lever A converted loud to silent and L1 fires.
- **P2 (lever B)**: probe-derive subagent makes zero tracked-file
  modifications (`git status --porcelain` clean of tracked entries during
  the phase; no Edit/Write on tracked paths in its transcript);
  `--validate-risk-probes` passes on the emitted artifact (script-file form
  included); BUILD_GATE replays the probes unchanged. Expected direction:
  probe_derive phase wall < 300s (observed 484s; the two named sinks sum
  ~190s) — recorded raw; the GATE is the mechanism checks, not the
  stochastic wall number.
- **P3 (lever C)**: API-turn count inside inter-phase windows (run start →
  verify.started_at, phase records and rounds_history excluded) drops ≥ 30%
  vs SW2 A1's like-for-like windows; recorded raw. **Mechanically
  reproducible (R0 SHOULD-FIX 1)**: a checked-in extractor
  (`benchmark/ceiling/scripts/interphase-turns.py`) computes it from the
  debug log + state timestamps — same script on both runs, no hand counts.
- **P4 (lever D)**: `state-phase-write.py` self-tests cover: two-round
  respawn preserves round 0's timing in `rounds_history`; respawn after a
  completed FAIL round; `exec` block preserved across respawn; existing
  history never clobbered (R0 SHOULD-FIX 2). The re-run's state carries
  `rounds_history` for any phase that actually re-ran.
- **P5 (L1 guard)**: trivial-goal smoke through resolve (sonnet) unchanged —
  trivial path routing, mini-spec sentinel, no new halts.
- **P6 (attention cost)**: resolve skill token total
  (`scripts/skill-token-gauge.py`) delta ≤ +1% — lever A/B/C edits mostly
  replace existing sentences.

**Claim boundary**: LC3 / total-wall movement is NOT this iter's claim —
implement wall is task-stochastic and the SDK terminal-stall class
(iter-0065, not skill-fixable) remains live. Claimed: the three named
overhead classes are closed at the contract level, proven by the re-run's
decomposition showing them absent, and failed-round wall becomes
attributable in state. Tranche-2 LC3 is measured by its own run after.

## Loss conditions (a change that cannot lose is invalid)

- **L1**: P1 falsified — a checkpoint commit still sweeps pre-existing
  untracked files, OR legitimate authorized new files fail to stage
  (false `BLOCKED:implement-empty` / lost work) → revert lever A.
- **L2**: P2 mechanism checks falsified — deriver still mutates tracked
  files, or emitted probes malformed/unreplayable under the script-file
  allowance → revert lever B.
- **L3**: P5 falsified → revert smallest unit + re-smoke; 2× fail → surface
  (HANDOFF binding rule).
- **L4**: probe replay breaks at BUILD_GATE/VERIFY on script-file probes →
  revert the script-file half of lever B (boundary sentence stands on its
  own evidence).
- **L5**: P3 shows < 10% turn reduction → delete the lever C sentence
  (prose that does not move behavior is pure attention cost).

## Probes

1. SW2-shaped A-arm re-run (gates P1/P2/P3; wall numbers recorded raw).
2. `state-phase-write.py` two-round self-test (gates P4).
3. Trivial smoke, PHASE-0 routing evidence only (gates P5).
4. `spec-verify-check.py --print-authorized-surface` unit check against a
   fixture plan.md (positive + malformed-sentinel negative).
5. Token gauge before/after (gates P6).

## Implementation deliverables (Codex CLI, workspace-write; mirrors ×3)

1. `SKILL.md` — PHASE 0 untracked-baseline write; :217/:222 scoped staging
   via `--print-authorized-surface` + `git add --pathspec-from-file`;
   BUILD_GATE fix-loop repair commit path (same scoped staging); :259
   `git add -u` + cleanup untracked-delta check; one lever-C batching
   sentence (engine wrapper calls stay solitary + foreground).
2. `_shared/spec-verify-check.py` — (a) `--print-authorized-surface`:
   resolves surface to existing changed/new files with the gate's own
   matching code, one path per line, nonzero exit on missing/malformed
   sentinel; (b) authorized-surface enforcement extends to untracked delta
   vs `.devlyn/untracked.baseline` (`.devlyn/` exempt); (c) risk-probe
   validation scans `.devlyn/probes/` files referenced from `cmd` with the
   existing forbidden-ref + external-URL rules at load time.
3. `references/phases/probe-derive.md` — tracked-file mutation ban +
   base-outcome classification (bug-exposing vs preservation) +
   `.devlyn/probes/` script-file allowance with the hypothesis-inline
   exception.
4. `_shared/state-phase-write.py` — `rounds_history` append on spawn +
   self-tests per P4; `references/state-schema.md` notes `rounds_history` +
   `untracked.baseline` artifact.
5. `benchmark/ceiling/scripts/interphase-turns.py` — P3 extractor
   (benchmark-side asset, not shipped skill surface).
6. Mirrors `config/skills/` ↔ `.claude/skills/` ↔ `.agents/skills/`;
   `bash scripts/lint-skills.sh` clean; token gauge P6.

## Second implementation pass (R1 Q5 MUST edit)

**Hash-binding + archive (2026-07-07, Codex CLI workspace-write xhigh,
archive `/tmp/codex-iter0066/impl2-response.log`)**:
`--print-risk-probes-digest` (sha256 over a canonical
`path\0bytes\0` stream: risk-probes.jsonl + each referenced
`.devlyn/probes/*` in sorted order); replay integrity check in the
`--include-risk-probes` path — probes enabled/present with missing OR
mismatched `state.risk_probes_digest` → `correctness.risk-probe-integrity`
CRITICAL fail-closed (`--validate-risk-probes` stays digest-free for
derive time); SKILL.md PHASE 1.5 computes + writes the state key
(`criteria_sha256` inline-write pattern) with orchestrator-only
regeneration rule; state-schema field bullet; `archive_run.py`
`move_probe_scripts()` preserves `probes/<file>` layout in run archives +
`--self-test`. Orchestrator re-ran all gates: 4 self-tests PASS, lint
"All checks passed." (orchestrator synced the sandbox-denied `.agents`
mirror), token gauge final 116,059 chars (**+2.81% total — final P6 raw;
the digest MUST was adopted knowing it worsens P6**, recorded, not
hidden).

## Principles check (final, at close)

- **0 Pre-flight**: ✅ removes measured user-visible overhead failures
  with archived repro — the tranche-1 task that died at the 3600s cap now
  completes at 3157s with every phase PASS; probe_derive 484.0 → 204.6s;
  the 336s git-sweep FAIL class cannot recur (staging cannot express it +
  fail-loud delta gate); wall-time-per-fixture drop is pre-flight signal
  (iv).
- **7 Mission-bound**: ✅ Mission 1 ceiling axis (ops #17) — the
  pre-VERIFY overhead lever HANDOFF names as tranche-2 prerequisite.
- **1 No overengineering**: ✅ every addition cites an observed failure
  (512-file sweep → scoped staging; probe target-mutation + escaping
  thrash → boundary + script files; hidden rounds ×2 runs →
  rounds_history; post-derive mutation observed live → digest); the one
  unproven addition (lever C sentence) was deleted by its own loss
  condition the same day it shipped.
- **2 No guesswork**: ✅ P1-P6 frozen pre-implementation; P3 FALSIFIED →
  L5 executed; P6 FAILED → raw numbers kept, adjudicated openly at R1;
  zero retroactive prediction edits.
- **3 No workaround**: ✅ fixes land at violated invariants (checkpoint
  contract = authorized surface; probe derivation is tracked-read-only;
  state must attribute every round; probe artifacts integrity-bound to
  orchestrator-owned state). Fail-loud preserved via the untracked delta
  — R0's silent-drop counter adopted, not argued away.
- **4/5 Worldclass / Best practice**: ✅ 4 self-test suites green
  (writer-parity, script-scan, digest, rounds_history cases pinned);
  lint green; parity-by-construction (staging + baseline share the
  gate's parser/matcher); stdlib only.
- **6 Layer-cost-justified**: ✅ no new layers; overhead removed from
  existing ones. Wall 3157s vs old cap-kill recorded raw — LC3 remains
  NOT claimed (n=1, task-stochastic implement, correction-loop
  variance); tranche 2 owns that measurement.

## Pair rounds

- **R0 (2026-07-07, read-only xhigh, 503s, archive
  `/tmp/codex-iter0066/r0-response.log`): SHIP-WITH-EDITS.** Decisive
  criteria (Codex-named, in order): fail-loud-over-silent-drop,
  root-cause-vs-symptom, measurement-integrity, observed-failure-citation,
  prose-ceiling precedent. MUST-FIX 1 (untracked-delta fail-loud) ADOPTED —
  baseline + gate delta check; MUST-FIX 2 (pathspec parity) ADOPTED —
  parity by construction via shared matching code; MUST-FIX 3 (fix-loop
  path) ADOPTED; MUST-FIX 4 (base-outcome classification) ADOPTED —
  preservation probes PASS on base legitimately; MUST-FIX 5 ADOPTED for
  script content scanning (orchestrator had independently found it pre-R0),
  hash-binding DEFERRED with a named position + falsifier (see lever B) —
  open disagreement carried to R1, not silently closed. SHOULD-FIX 1/2/3
  all ADOPTED (P3 extractor script, extended P4 self-tests, cleanup
  untracked fail-loud). R0's two unreproduced items resolved with
  provenance notes in Evidence. POS-5 boundary confirmed: n=1 re-run gates
  mechanisms only, never LC3.
- **R1 (2026-07-07, read-only xhigh, archive
  `/tmp/codex-iter0066/r1-response.log`): VALID-WITH-EDITS.**
  Q1 CONFIRM — all three orchestrator post-delegation edits verified at
  file level (`--write-untracked-baseline` shares `git_status_entries`
  with the reader; CLEANUP revert semantics restored; dedup verified;
  mirrors byte-identical). Q2 CONFIRM — P3 falsification + L5 deletion
  correct per the frozen loss condition; turn increase attributed to the
  correction loop + large-classification confound, not a 0066 defect.
  Q3 CONFIRM — R1's adversarial hunt found no whole added sentence
  deletable without losing a mechanism; **P6 closes
  FAILED-with-adjudication** (freeze mis-calibration; R1 recompute +1.77%
  vs orchestrator +1.83%, directionally consistent). Q4 CONFIRM status
  quo — decisive criterion: loud, evidenced correctness beats adding a
  deterministic pre-gate snapshot for one correctly-handled case; raw 144
  CRITICALs preserved in `spec-verify-findings.jsonl`, adjudication
  evidence in `build_gate.log.md:53`. Q6 CONFIRM — round-0 null
  completion is orchestrator write-protocol noncompliance
  (state-schema.md already mandates complete-per-reply), not a mechanism
  gap.
  **Q5 REFUTE — position flipped on a fired falsifier (named delta)**:
  the deferral position's accepted falsifier ("any observed post-derive
  probe mutation flips this to MUST") fired on the FIRST live run — R1
  found, and the orchestrator re-verified in the debug log, a top-level
  Edit rewriting `.devlyn/probes/P1.py` at 12:47:44 (post-derive, during
  the correction loop; 1992 → 2701 bytes), plus an archive gap: the
  archived `risk-probes.jsonl` references a script the run archive does
  not contain. Hash-binding moved from follow-up to THIS iter's MUST:
  state-held digest (`state.risk_probes_digest`, `criteria_sha256`
  precedent) over `risk-probes.jsonl` + referenced scripts, verified
  fail-closed at every replay; `archive_run.py` archives
  `.devlyn/probes/`. Implemented as a second Codex delegation
  (`/tmp/codex-iter0066/impl2-response.log`).

## Execution record (filled as gates clear; raw numbers only)

- **Implementation (2026-07-07, Codex CLI workspace-write xhigh, 1448s,
  archive `/tmp/codex-iter0066/impl-response.log`)**: 7 files +518/−107.
  Codex sandbox could not write `.agents/` — orchestrator synced that
  mirror. Orchestrator line-by-line review found and fixed at root cause
  (surfaced here for R1 reconciliation per
  `feedback_implementation_to_codex`):
  1. **Baseline writer/reader parser mismatch**: Codex's PHASE 0 step used
     `git status --porcelain | awk` — C-quoted special-character paths and
     collapsed untracked DIRECTORIES to `dir/`, while the reader
     (`current_untracked_files`) parses `-z --untracked-files=all` per-file.
     Every pre-existing file under an untracked directory (exactly the SW2
     scaffold shape) would false-positive as created-during-run CRITICAL.
     Fix: new `--write-untracked-baseline` mode sharing `git_status_entries`
     with the reader (parity-by-construction, same argument as R0 MUST-FIX
     2); SKILL.md PHASE 0 calls it; self-test pins the untracked-dir +
     space-path case and the baseline-exempt assertion.
  2. **CLEANUP contract semantic loss**: Codex's rewrite of SKILL.md
     cleanup step 1 dropped the original "revert to `pre_sha`" action and
     the findings-file target. Restored with the untracked-delta extension
     merged in.
  3. Token-budget dedup: scoped-staging command stated once (PHASE 2 step
     3), referenced by name at the phase-gated + fix-loop sites;
     state-schema rounds_history example collapsed; probe-derive
     script-file rules deduped into the output-rules block.
  - Also verified: state-schema.md + spec-verify-check.py docstrings no
    longer cite autoresearch/ paths (pre-existing violations of the
    iter-0065 runtime-surface rule, removed by Codex — kept).
- **Gates (2026-07-07, re-run by orchestrator, not trusted from delegate)**:
  `state-phase-write.py --self-test` PASS (P4 cases);
  `verify-merge-findings.py --self-test` PASS;
  `spec-verify-check.py --self-test` PASS (script-probe scan 4 cases,
  print-surface parity incl. `dir/**` + authorized-but-uncreated,
  missing-baseline fail-closed, untracked-delta flag + baseline exempt +
  writer-parity untracked-dir case); `lint-skills.sh` "All checks passed."
  (both mirrors synced, `.agents` by orchestrator); empty-pathspec edge:
  `git add --pathspec-from-file=-` with empty input exits 0 staging
  nothing → commit fails loud ("nothing to commit") — acceptable loudness.
- **P5 PASS (2026-07-07, `iter0066-p5`, sonnet compliance cell small)**:
  `overall: "PASS"`, zero failed assertions, `finish_gate_ran` true —
  trivial path unchanged on the new surface (L3 avoided). Side evidence
  for lever A: `.devlyn/untracked.baseline` written (0 entries, clean
  scratch repo — correct) and the implement checkpoint commit contains
  exactly `bin/cli.js` + `tests/cli.test.js` (scoped staging live).
- **P3 baseline (mechanical, `interphase-turns.py` on old SW2 A1)**: 47
  API-request turns / 503.4s across 6 inter-phase windows (the 388s window
  includes the hidden round 0 — the old state has no `rounds_history`, the
  like-for-like caveat recorded).
- **SW2 re-run (2026-07-07, `iter0066-p1` A1, sonnet orchestrator,
  executor=codex, 3157s wall, exit 0, NO timeout — old run: 3600s cap
  kill)**: every phase PASS; `sub_verdicts {mechanical: PASS, judge: PASS,
  pair_judge: PASS}`; archive + finish-gate ran. Phases: plan 111.6s,
  probe_derive 204.6s, implement 204.1s (round 1), build_gate 321.8s
  (round 0, single), cleanup 54.1s, verify 730.8s. Complexity classified
  `large` this run (old: `medium`) — classifier variance, recorded.
- **P1 PASS**: the single `chore(pipeline): implement` commit contains
  exactly the two authorized_surface files (`autodetector.py`,
  `test_autodetector.py`); 2,102-path pre-existing untracked scaffold
  recorded at PHASE 0 and still untracked at run end; zero
  `scope.out-of-scope-file` findings from pre-existing untracked files;
  no git-sweep BUILD_GATE FAIL round (the 336s class is gone from this
  run). Synthetic fail-loud clause already pinned in the self-test
  (planted unauthorized untracked file → CRITICAL).
  **New-mechanism edge caught live (for R1)**: BUILD_GATE's own mandated
  lint setup (`pip install flake8 isort` into non-gitignored `.venv/`)
  created 144 post-baseline untracked files → the delta gate correctly
  flagged them CRITICAL → the BUILD_GATE agent verified attribution
  (mtimes matching the gate run, zero baseline entries, no relation to
  the diff) and reclassified per build-gate.md's own pre-existing
  quality_bar rule to `scope.tooling-artifact-leak` MEDIUM non-blocking.
  Loud, evidenced, contract-sanctioned — but the CRITICAL→MEDIUM
  downgrade is made by the same agent the gate binds; R1 adjudicates
  status-quo vs a pre-gate untracked snapshot.
- **P2 PASS**: probe-derive subagent made ZERO tracked-file writes (old
  run: 3 Edits on the target impl) — its 2 Writes were
  `.devlyn/probes/P1.py` + `.devlyn/risk-probes.jsonl`; first live use of
  the script-file form, `cmd` is one short line (the ~90s JSON-escaping
  thrash class gone); probes validated + replayed at BUILD_GATE (PASS).
  probe_derive wall 204.6s < 300s expected direction (old 484.0s, −58%).
- **P3 FALSIFIED → L5 EXECUTED**: like-for-like inter-phase windows
  (excluding each run's fix/correction window): old 10 turns/115s → new
  32 turns/190s — turns went UP, not down ≥30%. Confounds recorded (this
  run classified `large` so PHASE 0 did assumption-synthesis work — 15
  turns in window 1 vs 2; scoped staging + baseline add mechanical
  steps), but the frozen gate is the gate: the lever-C batching sentence
  was deleted from all three mirrors same-day (prose that does not move
  behavior is attention cost). Raw extractor outputs archived in this
  section; old aggregate 47 turns/503.4s, new 82/1130.6s — the new 941s
  window is implement round 0 (codex, ~430s) + the orchestrator's
  substantive correction loop, NOT bookkeeping.
- **P4 PASS**: self-test suite green (4 pinned cases) AND live capture:
  the re-run's implement record is round 1 with `rounds_history[0]` =
  round 0's spawn (codex over-broad first attempt; orchestrator reviewed
  the diff, empirically proved the plan's pure-reorder sufficed, fixed
  its own spec-drafting error — fabricated test-class name — corrected
  criteria + sha256, respawned). Nuance for R1: the orchestrator never
  called `complete` for round 0, so the history entry has null
  completed_at/verdict — attributable-but-incomplete; write-protocol
  already mandates complete-per-reply, this is orchestrator compliance,
  not a mechanism gap.
- **P6 raw (adjudication open for R1)**: resolve SUBTOTAL 112,890 →
  115,170 chars = **+2.02% > the frozen ≤ +1% gate — P6 FAILED as
  frozen.** Recorded raw, not retro-edited. After the L5 deletion the
  final surface is **114,951 chars = +1.83%, still > +1%**. Adjudication
  position: the freeze was mis-calibrated (iter-0065 used ≤ 2% for TWO
  levers; this iter ships FOUR), every surviving addition carries a named
  failure mode, and further cuts hit semantic loss (CLAUDE.md forbids
  gaming the count). Three dedup passes applied (−673 chars from peak
  115,843) before the L5 deletion. R1 is asked to adversarially hunt
  remaining deletable text; if none survives, P6 closes
  FAILED-with-adjudication.
