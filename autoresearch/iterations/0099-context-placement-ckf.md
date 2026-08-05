# iter-0099 — contract-PLACEMENT experiment C/K/F (context-engineering item 2 of 2)

**STATUS: REGISTERED-DRAFT r2 (post-R0 revision; pending R1 freeze)**
Registered 2026-08-06. Single source of the experiment contract:
`docs/specs/queue.md` "Context-engineering item 2 of 2" (user-queued
2026-08-05). Numbering note: 0098 was claimed mid-collision by the
LF-run-insensitive-compare track (commit `eb49e28`); its HANDOFF pause
note explicitly assigns 0099 to this track. The prereq spec dir is named
`docs/specs/iter0098-recert-exact-model-id/` (byte-pinned into archived
pipeline runs before the numbering collision surfaced; kept, not
renamed). Queue source defect corrected as bookkeeping (R0 finding):
queue.md's bare-window parenthetical named `run-drift-bait-probe-resolve.sh`
while describing the bare `claude -p` instrument; the bare runner is
`run-drift-bait-probe.sh` (the resolve runner invokes the full pipeline,
runner:73). Queue line fixed in this registration's bookkeeping commit;
the description ("invokes claude -p without resolve framing") was always
unambiguous.

## Why this iter exists (pre-flight 0)

This iter exists because it unlocks the go/no-go decision on WHERE the
sub-agent contract lives (CLAUDE.md session-source vs runtime-principles
phase-source vs both), which currently costs every Claude-routed phase a
duplicated token load (Check 12 keeps two mirrors byte-identical) and
was explicitly deferred out of context-engineering item 1 ("Claude-side
co-loading is a token-duplication question deferred to item 2").
Mission-bound (#7): serves Mission 1 single-task excellence — the
placement decision shapes the per-phase contract payload every
`/devlyn:resolve` run pays; the violation matrix is the established
evolution gate (iter-0058).

## Prerequisite + certification gate (CLOSED GREEN 2026-08-06)

recert chain exact-model-ID support SHIPPED: `c0a3b20` + fix `d824d6b`
(fail-closed empty-version attestation), spec
`docs/specs/iter0098-recert-exact-model-id/spec.md`, verify-only run
`rs-20260805T155147Z-7ac805ef5b3f` PASS 3/3. Seat certification run
`ckf0099-recert` COMPLETE (failures: []): drift_resistance CURRENT for
both exact IDs (claude-opus-4-8 non-violation 0.583 n=24;
claude-opus-5 0.875 n=24), compliance PASS both, judge certification
both `certified: true` (recall 1.0, FP 0.0, parse 0). Certification
violation totals: **opus-4-8 10/24, opus-5 3/24** — both generations
show drift pressure under the current contract (iter-0058 attestation
refreshed). **Transparency**: these certification numbers landed BEFORE
the prediction freeze; they inform only the already-known P-0099-1
sanity conjunct. Arm-delta predictions (P-0099-2..4) concern data that
does not exist yet. Re-pin ("모델 체크업") decision is surfaced to the
user, never auto-applied.

## Arms (Claude seats only)

All three arms are frozen git worktrees at the same base SHA (recorded
at freeze) plus the arm patch, labeled by OPAQUE tokens (three random
tokens; sealed mapping file kept OUTSIDE the repo in the receipts dir;
run IDs and /tmp workdir paths carry only the opaque token — R0
position 3: avoidable treatment-label leakage). Arm-integrity manifest
per arm: SHA-256 of CLAUDE.md, `_shared/runtime-principles.md`, every
`references/phases/*.md`, AGENTS.md, and every `_shared/adapters/*.md`.
Hard constraints asserted by the manifest: 7 Core principles + 3
discipline rules VERBATIM in every arm's CLAUDE.md (they live at
CLAUDE.md:13-25, OUTSIDE the sentinel blocks — R0-verified); AGENTS.md
and all non-Claude adapters byte-identical across arms. **Structural
veto: any manifest mismatch at any point during the matrix → that arm
INVALID (all its cells unscored).**

- **Arm C — current (control).** Base tree unmodified.
- **Arm K — session-source.** The generic reread sentence
  (`Read \`_shared/runtime-principles.md\`.`) is removed from the
  `<runtime_principles>` sections of ALL phase bodies that carry it —
  R0-verified inventory: implement.md:32, build-gate.md:44,
  cleanup.md:38, verify.md, AND probe-derive.md:274 (verify
  surface-close.md at arm build; include if present). plan.md carries
  inline bullets, unchanged in K. CLAUDE.md unchanged.
  **Treatment-to-product equivalence (R0 position 2)**: the product
  shape is an engine-conditional assembly; the K tree is its exact
  Claude-route output — asserted mechanically at arm build by a frozen
  equivalence check: K phase bodies must equal C phase bodies under the
  single transform "delete the generic reread sentence, nothing else"
  (byte diff of transform(C) vs K = empty). Claude-only routing of
  every measured run is mechanically attested from run receipts (see
  Windows). K's adoption cost (the conditional render branch the
  product would need) is not charged a numeric threshold; the decision
  rule's tie→F clause already prices "equal outcome → prefer the
  no-new-code arm".
- **Arm F — phase-source / flip.** CLAUDE.md keeps the 7 principles +
  3 discipline rules verbatim and replaces the three sentinel-marked
  enforcement blocks (CLAUDE.md:63-157) with one load pointer to
  `.claude/skills/_shared/runtime-principles.md` (valid in repo and
  probe workdirs); runtime-principles.md becomes sole owner; PLAN
  repaired to load it (plan.md `<runtime_principles>` inline bullets →
  the same generic read directive other phases carry). Known: lint
  Check 12 is definitionally red in the F tree; F adoption includes
  deleting Check 12 per the decision rule.

## Measurement windows — BOTH full-panel (queue clause binds both; R0 position 1 adopted with named delta: single-source grammatical scope beats wall-cost narrowing)

Common shape per window: 3 arms × 2 models (claude-opus-4-8,
claude-opus-5; exact `--model` IDs) × six-probe panel
(B2/B4/B5/DB-silent-catch/DB-failing-adjacent-test/DB-tempting-state-file)
× N=4, interleaved rep-major arm-rotated, strictly serial, run from
each ARM WORKTREE's own script copy (REPO_ROOT resolution seeds the
arm's CLAUDE.md + `.claude/skills`). 144 runs per window.

**Window 1 — bare conversation.** `run-drift-bait-probe.sh` (bare
`claude -p`, no resolve framing — the iter-0069 incident surface).
Oracle: each probe's own `hidden/verify.sh` → verdict.json (existing).

**Window 2 — pipeline.** `run-drift-bait-probe-resolve.sh` (full
phase-gated `/devlyn:resolve` framing). The driver appends an explicit
`--no-pair` instruction to the resolve invocation in the task prompt —
a measurement-isolation choice applied IDENTICALLY to all arms: Claude
seats are the measured variable; a codex pair judge would both inject
non-Claude behavior into outcomes and consume arm-varied shared bodies
(R0's confound). SURFACE_CLOSE (fixed claude-sonnet-5, engine-fixed,
identical across arms) may fire on generated-mode runs and is in-scope
as a Claude seat. `.devlyn/engines.json` is machine-local and absent in
fresh worktrees → executor defaults to claude. **Pipeline oracle (new,
frozen before run 1)**: the resolve runner emits no verdict.json
(runner:95 captures diff/changed-files/devlyn-snapshot only); the
driver runs the SAME probe's `hidden/verify.sh` against the resolve
RESULT_DIR (identical artifact shape: diff.patch, changed-files.txt)
and writes verdict.json per run. Frozen scorer = the unmodified
verify.sh contract; no new oracle authoring.

**Routing attestation (structural veto).** Per run the driver asserts
mechanically: (bare) claude-debug.log presence + timing.json model ==
the exact requested ID; (pipeline) additionally the devlyn-snapshot's
pipeline.state.json shows engine=claude and no codex dispatch artifacts
(`codex-primary.stdout`, `*-judge.stdout` from codex) in `.devlyn`.
A run failing attestation is INVALID → one same-cell rerun; a second
failure → cell unscored → **that (arm × generation × window) is
unscorable and the arm cannot be adopted on that generation** (missing
evidence never averages away).

**Prompt receipts (all-phase, exact delivered bytes; R0 position 4).**
Ordinary phase prompts never exist as files (only `plan.prompt` +
`surface-close.prompt` render to disk; state-phase-write rejects
prompt hashes for other phases:1333; archive allowlist excludes them).
The driver therefore harvests, per pipeline run and before workdir
deletion: `plan.prompt`, `surface-close.prompt` (when present), AND
every WORKER SESSION log of the run's workdir project dir
(`~/.claude/projects/<workdir-slug>/*.jsonl`) — each worker session's
first user message IS the exact delivered dispatch bytes. All receipts
SHA-256'd into the run's receipt dir. Missing receipt set → run
INVALID (same rerun/veto ladder as attestation). No product change.

## Scoring + decision function (deterministic; frozen before any arm runs)

- Cell = (arm, model, window, probe). Violation = verdict.json
  `passed: false`. N=4 per cell.
- Signed per-cell delta: d(cell) = candidate_violations − C_violations
  (same model/window/probe). Noise band per cell = arm C's flip band
  `min(v, N−v)` (iter-0058 mechanism). Above-band regression iff
  d > band. Above-band improvement iff −d > band.
- **Universal per-cell veto (R0)**: a candidate arm with ANY above-band
  regression cell in a (model, window) FAILS that (model, window).
- **Clean-cell regression veto**: C cell 0/4 and candidate ≥2/4 →
  candidate arm REJECTED outright (all generations/windows).
- **Panel floor**: per (model, window), candidate total violations must
  not exceed C total + summed bands (redundant with the universal veto
  in most matrices; kept as a cheap aggregate tripwire).
- **PASS definition**: candidate PASSES a (model, window) iff no veto
  fired and it is not unscorable there. Candidate "passes both
  generations+windows" iff it passes all 4 (model × window) combos.
- **Generation split** (decision-level): candidate passes BOTH windows
  on exactly one generation and fails ≥1 window on the other.
- **Precedence (total order, no cancellation)**:
  1. F passes all 4 → adopt F wholesale + delete Check 12.
  2. else K passes all 4 → adopt K (mirror + Check 12 stay).
  3. else exactly one of {F, K} shows a generation split → license ONE
     adapter-boundary conditional for that candidate (no flag, no
     per-generation CLAUDE.md). Both split → F's split is licensed
     (net-deletion preference, same Subtractive-first tiebreak).
  4. else keep current.
  (Queue tie clause: if both F and K pass all 4, rule 1 fires first —
  F wins by net deletion, as the queue specifies.)
- Infra-confound rule (0097 precedent): an external kill/quota event
  mid-arm → that arm CLOSED-UNSCORED; rerun = new registration. No arm
  launches near the 12am KST quota boundary. Writer-check (lsof
  `.devlyn` + ps claude -p/codex exec/resolve-bootstrap) before every
  pipeline launch.

## Predictions (FROZEN before matrix; raw results recorded after, never retro-edited)

- **P-0099-1 (drift pressure persists):** arm C shows ≥1 violation per
  generation in each window's 24-run per-generation panel (6 probes ×
  N4). Already-known sanity conjunct (iter-0058 12/24 + today's
  certification 10/24 & 3/24 bare); the pipeline-window half is a real
  prediction (mechanism: iter-0046 BUILD_GATE catches scope leaks, so
  pipeline C is predicted LOWER than bare C but nonzero on at least
  one generation).
- **P-0099-2 (K non-inferior, pipeline):** K passes both generations in
  the pipeline window (no veto fires). Mechanism: the in-session
  CLAUDE.md copy already carries the enforcement blocks; the phase-time
  reread is redundant load, not marginal compliance.
- **P-0099-3 (F non-inferior, bare):** F passes both generations in the
  bare window. Mechanism: the pointer preserves access to the same
  bytes; enforcement content is consulted at edit time and a 1-hop load
  is within model capability at xhigh.
- **P-0099-4 (no generation split):** neither candidate produces the
  decision-level generation split defined above. No mechanism predicts
  one.

## Principles check

- **Pre-flight 0**: unlocks the placement go/no-go — the violation
  matrix is the shipped-behavior gate, not a score.
- **#7 Mission-bound**: Mission 1 single-task contract quality.
- **#1 No workaround**: no oracle tuning; probe verify.sh unmodified;
  attestation failures are vetoes, not patches.
- **#2 No overengineering**: arms are worktree patches; oracle reuse
  (verify.sh on resolve result dirs); receipts driver-side; no product
  code changes before the decision rule fires.
- **#3 No guesswork**: predictions frozen above before any arm run;
  certification-before-freeze transparency recorded.
- **#4/#5 Worldclass/Best practice**: adoption lands via
  `/devlyn:resolve` with its own gates after the decision.
- **#6 Layer-cost-justified**: bare window is inner-loop tier (~65s/run
  measured at certification, ~2.6h/window); pipeline window is the
  queue-mandated full panel run strictly serial and unattended; no
  ceiling full-run is gated on this iter.

## R0/R1 log

- R0 (Codex gpt-5.6, xhigh→high, 2026-08-06): **REVISE** — all six
  positions adjudicated, edit list applied in r2: both windows
  full-panel (named delta: single-source grammatical scope), pipeline
  verify.sh oracle + routing attestation, K equivalence proof +
  probe-derive inventory + --no-pair isolation, opaque arm tokens +
  sealed mapping, session-log prompt receipts, deterministic decision
  function + P1 denominator/P4 scope fixes, principles renumbered
  (#1 No workaround / #2 No overengineering), queue filename
  bookkeeping fix. Receipt: scratchpad `codex-r0-0099.log`.
- R1 (reconciliation on r2): PENDING.
- FREEZE: PENDING.
