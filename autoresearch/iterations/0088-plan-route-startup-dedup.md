---
id: "0088-plan-route-startup-dedup"
title: "PLAN route determinism, then startup semantic dedup re-measurement"
kind: optimization
status: STAGE A SHIPPED 1312cb7; STAGE B CLOSED-FAIL protocol-failed-at-controls 2026-08-02 (H1-v3 UNSCORED)
complexity: medium
depends_on: ["0087-startup-semantic-dedup"]
---

# iter-0088 — PLAN route determinism (Stage A), then H1-v3 re-measurement (Stage B)

## Why this iteration exists

Pre-flight 0: this iter exists because it unlocks the blocked go/no-go on the
only data-named residual wall target — startup + interphase orchestrator gaps
(`0075:135-139`; corrected `-22c` baseline: startup 193,016 ms of elapsed
2,068,641 ms, `0087:14-19`) — whose converged mechanism H1-v3 closed UNSCORED
when iter-0087 protocol-failed (`0087:357-364`). Mission-bound (#7): Mission 1
skill-routing repair and single-worktree wall measurement; no M1.5 surface.

HANDOFF Next-work #1's conditional ("if H1-v3 remains the best startup lever")
was answered on the record by all three seats: yes — no competing registered
mechanism exists (`0077:383-390`; Grok/Codex negative-existence searches).

## Seats and rounds (all actually executed 2026-08-01)

Seats: **Opus 5** (headless `claude -p --model claude-opus-5`, attested
`claude-opus-5` firstParty in modelUsage), **Codex CLI gpt-5.6-sol** (Terra,
codex-monitored, read-only, xhigh), **Grok 4.5** (headless allowlist
`read_file,grep,list_dir`, `--no-memory`, MCP disabled). Orchestrator: Fable 5
(never a test arm). R0: three independent GO-WITH-EDITS on the same target.
R1: unanimous Q1=Stage-A-first; final CONFIRM-FREEZE (Grok, Opus conditional)
/ GO-WITH-EDITS-OBJECT-pending-exact-text (Codex). Seat transcripts:
session scratchpad `r0-*.{log,json,md}`, `r1-*.{log,json,md}`.

**Named deltas and kills this round** (evidence over claim):

- ORCH R0 D3 ("launcher preflight asserts engines bytes + requested PLAN
  model; route violation = launcher defect") — KILLED by Opus F1/F2/F6,
  orchestrator-verified: `run-ceiling-arm.sh:375` authors the arm's
  `{"executor":"codex"}` bytes itself (self-assert is tautological), the
  invoke at `:264` carries no `--engine`, and route resolution happens
  product-side at PHASE 0 step 2. A post-product-start route violation is
  treatment evidence, never a free launcher defect (T1, `0087:319-324`).
- ORCH R0 D2 ("429/OAuth lumped, fixed count + backoff") and Grok R0
  ("max 1 auto re-invoke + 30 s sleep") — KILLED by E4: T1R's 429 is a
  session-limit exhaustion with a stated multi-hour reset
  (`~/.local/share/nx01/iter0087-treatments/F7/T1R/transcript.txt` line 1:
  `"You've hit your session limit · resets 3:30pm (UTC)"`, request
  12:20:28Z, zero tokens, empty modelUsage). Short backoff provably dies
  identically. Grok withdrew with this named delta.
- Grok R0 Option R (route conjunct only, no Stage A) — REVERSED by Grok
  itself at R1 with named delta E2/E5/E6; criterion
  **Route-Determinism-Before-Envelope**.
- Opus R0 "controls at bare HEAD are engine-confounded" — WEAKENED then
  RE-STRENGTHENED in corrected form: all four 0087 control states record
  `phases.plan.engine="claude"` under `state.engine="codex"`, but that field
  is caller-written (`state-phase-write.py:1390-1391`) — a self-reported
  proxy, not a model receipt; PLAN `model_effective` is structurally null
  without an engine session log (`:1406-1408`; PLAN absent from
  `WORKER_SESSION_ARTIFACT_PHASES`, `:52-56`). Route claims must score raw
  worker-session receipts, never state fields (HANDOFF "score the frozen
  conjunct, never a proxy").
- Packet defects orchestrator acknowledges (binding-lesson receipts): "0085
  BLOCKED, 0086 BLOCKED" (both SHIPPED; the BLOCKED items were runs inside
  them — Opus F7); E6's "lint half separable" (false — `313304c`'s lint
  lines live inside H1-dependent Check 6k, absent at HEAD; Opus finding 2);
  `state-phase-write.py:2492` citation (correct cite `:1406-1408`; Grok +
  Opus independently).
- ORCH adjudication A1 (contested D2 wait rule): ADOPT Opus flat constant +
  single probe; REJECT Codex's vendor-string reset parser. Named criterion:
  **the single non-error health probe carries correctness** (a wrong wait
  cannot cause premature launch — the probe blocks it), so the wait constant
  is liveness-only, and on a liveness-only surface subtractive-first rejects
  a parser with no observed failure it prevents. The 4 h constant covers the
  one observed announcement (3 h 09 m) and is honestly labeled n=1-anchored.
- ORCH adjudication A2 (route contract direction): ADOPT Codex — PLAN is
  **orchestrator-fixed**, not "always Claude": Claude Code uses its native
  Claude worker; Codex CLI / oh-my-pi keep their own fresh worker
  (`engine-preflight.md:18`, `:35`). Under this experiment's Claude
  orchestrator, PLAN = native Claude worker requesting Sonnet (preserves
  `0087:219`).

## STAGE A — PLAN route determinism (ships first, no arms)

**Observed failure**: F7/T1 opened PLAN on the executor pin instead of the
registered Sonnet route and burned a treatment arm (`0087:319-324`). The
enabling defect is live at HEAD: five staged surfaces teach PLAN∈executor
against the reference contract — majority on the wrong side (4-vs-2):

| Surface | Says |
|---|---|
| `config/skills/devlyn:resolve/SKILL.md:57` | role resolution (`--engine` > pin > default) over a default set including PLAN |
| `CLAUDE.md:43` | "Executor — PLAN/IMPLEMENT/CLEANUP + primary VERIFY judge" |
| `AGENTS.md:39` | "executor (PLAN/IMPLEMENT/CLEANUP) defaults to `claude`", pin-overridable |
| `config/skills/devlyn:engines/SKILL.md:43` | "pin the executor (PLAN/IMPLEMENT/CLEANUP + primary VERIFY judge)" |
| `config/skills/_shared/engine-preflight.md:18` | Executor = IMPLEMENT/CLEANUP/primary VERIFY — PLAN excluded (reference contract) |
| `config/skills/devlyn:resolve/SKILL.md:104` | "Engine: Claude" (Claude-orchestrator special case, wrong for other CLIs) |

`run-ceiling-arm.sh:371-372` copies CLAUDE.md/AGENTS.md into every arm;
`claude-isolation.py:305-306` launches with `--setting-sources project,local`.
There is **no invoke-level lever** that yields deterministic PLAN routing
without swapping the whole executor (Opus, verified) — the fix is product
text, root cause ("delete the line that makes the flip possible").

**Stage A surface (closed list)**: rewrite `resolve/SKILL.md:57` and `:104`
to the orchestrator-fixed contract ("PLAN is orchestrator-fixed and never
inherits `--engine`, an executor pin, or `state.engine`; executor role
resolution applies only to IMPLEMENT / CLEANUP / primary VERIFY judge" —
route half of `313304c`, re-derived, no H1-v3 bytes); align `CLAUDE.md:43`,
`AGENTS.md:39`, `devlyn:engines/SKILL.md:43`; `engine-preflight.md` is
asserted unchanged; one **newly-authored** lint conjunct (no `313304c` 6k
cherry-pick — those lines are H1-dependent) enforcing that no surface
enumerates PLAN in the executor role. Tracked mirrors + refresh of the
untracked local `.claude/skills` mirror (it is NOT pinned by any commit —
`git ls-files` empty; `0087:183-184`'s "tracked" wording is wrong, do not
copy it). Nothing else. **Surfaced explicitly (not silent)**: this narrows
user-visible `--engine`/pin semantics — a user pinning `executor codex`
today could read PLAN as pin-governed; after Stage A, PLAN never follows the
pin. Authorized by the observed T1 failure (HANDOFF forbidden-list allows
CLAUDE.md/AGENTS.md edits on observed failure). Commit message must state
the narrowing.

**Stage A gates (all execution, not assertion)**:

1. Full `bash scripts/lint-skills.sh` green including the new conjunct.
2. Exact three-surface parity for changed skill files.
3. **Live canary matrix, two free-form runs at the Stage-A commit, no H1
   bytes**: (a) `engines.json` `{"executor":"codex"}`, no flag; (b) explicit
   `--engine codex`. Each must resolve executor codex for the executor roles
   AND the retained raw PLAN worker-session receipt must attest the
   orchestrator-fixed Claude route, with the arm-level requested model
   (outer CLI `--model`) recorded. State fields alone are insufficient
   (proxy rule above).
4. Formal `/devlyn:resolve --verify-only` on the Stage A diff, zero
   CRITICAL/HIGH (this reviews the diff; it cannot prove the route —
   verify-only skips PHASE 1-4, `SKILL.md:67` — the canaries are the proof).
5. Three-seat sign-off on the actual Stage A diff.

## STAGE B — H1-v3 re-measurement (registers now, freezes after Stage A)

**Mechanism carried intent-identical from `0087:57-97`** (ordered one-return
co-location; free-form only; parent keeps deterministic halts/classification;
one repository discovery pass; immutable criteria before plan in one worker
return; 0.85 matched-envelope criterion per pair; startup must not increase;
quality/halt gates and rejection rules of `0087:137-167` carry forward
unchanged except as amended below). Unscored ≠ falsified; redesign would be
drift. Candidate product surface = `0087:169-197` list MINUS the route
sentences Stage A already fixed (candidate is mechanism-pure).

### D1 — receipt lifecycle (total, precedence-ordered, fail-closed)

Decisive criterion: **NO-PRODUCT-INFORMATION FRONTIER** (Codex). Every
launcher invoke request produces a receipt; classification is by outcome,
never by absence (Grok). Boundary: only a harness-side mismatch detected and
receipted **before spawning the arm's outer CLI process** is
`PROTOCOL-BLOCKED` (not an attempt). Once the outer CLI process spawns,
classify in fixed order:

1. **COMPLETE** — every registered identity/receipt field exists, startup and
   PLAN spans closed, treatment ordering/hash attestations present. Later
   phases irrelevant. **Requested-PLAN-model receipt is arm-level**: the outer
   CLI `--model` argument recorded in the launch receipt (plus any explicit
   worker override). `phases.plan.model_requested` may be null when the worker
   inherits the session model — execution-caught 2026-08-01: the Stage-A pin
   canary ran the registered route with `plan.model_requested: null`
   (`state-phase-write.py:1392-1395` setdefaults null), so a state-field
   non-null conjunct would stochastically fail healthy rows (F12/C2 was the
   first receipt of this class).
2. **NULL-ATTEMPT** — provider invocation occurred AND provably zero primary+
   auxiliary usage AND no `pipeline.state.json` AND no PHASE-0/PLAN marker
   AND no generated criteria/plan/product write. Proof source frozen: the
   outer CLI JSON result envelope (`is_error`, `api_error_status`, `usage`,
   `modelUsage`) — reachable in the frozen recipe
   (`claude-isolation.py:312-313` `--output-format json` →
   `run-ceiling-arm.sh:557` transcript.txt; satisfiability verified this
   session against the real T1R envelope). `invoke_exit` corroborates, never
   classifies (0081 silent-exit-0 lesson).
3. **INCOMPLETE** — everything invoked that is neither provably COMPLETE nor
   provably NULL. Missing or malformed evidence defaults HERE, never to
   NULL. (`tokens>0 ∧ no state` is unobserved → stricter side; Opus/Grok
   both adopted with named delta `0087:342-344`.)

**Eligibility is orthogonal to completeness**: any invoked attempt whose
available receipt proves an effective-route violation fails the row **without
replacement**, whether COMPLETE or INCOMPLETE; missing route evidence stays
INCOMPLETE and is not inferred as a violation (closes the T1-shape loophole
where a wrong-route attempt consumes an ordinary replacement).

**Budgets (declared here, before any arm)**: one NULL replacement and one
INCOMPLETE replacement per matched pair; a replacement reruns BOTH arms from
fresh worktrees; second occurrence of either class fails the row unscored;
COMPLETE is never replaced regardless of ratio.

### D2 — provider-failure policy (replacement, never retry)

- 429/capacity: classify under D1. The single applicable replacement may
  launch only after **4 hours** (frozen constant, n=1-anchored to the
  observed 3 h 09 m announcement) have elapsed since the failed invoke's
  recorded invoke timestamp, and only after **exactly one** health probe —
  a minimal one-token `claude -p --output-format json` on the **arm's pinned
  CLI binary and arm HOME** (Treatment-Seat Identity Fidelity; host-CLI
  passes attest nothing) — returns a non-error envelope. Probe failure closes
  the row `provider-unavailable`; no second wait, no second probe, no loop.
- OAuth / invalid-grant / revoked credential: classify under D1; zero
  same-cohort retries; **no in-flight `/login`** (binding cohort rule);
  abort the pair, repair out of band, then the single applicable replacement
  reruns both arms.
- A second provider-null outcome in the same pair fails the row as
  provider-unavailable — non-evidence about H1.
- No adaptive backoff, no reset-string parser (ORCH adjudication A1), no
  reusable queue, no transport-wrapper change, no credential rotation
  between arms, no provider/model switch, no candidate edit mid-row (any
  candidate correction resets registration and controls).

### D4 — arm-byte attestation

After staging and before invoke, hash and receipt the **arm-materialized**
`.devlyn/engines.json` bytes and the staged skill-tree digest (extends
`write_settings_staging_receipt()` at `run-ceiling-arm.sh:378`); never the
repo source file (`0087:349-355`). Load-bearing, not belt-and-braces: the
local `.claude/skills` mirror is untracked, so no git identity pins it.

### D5 — controls and matched identity

- Freeze the **exact** post-Stage-A control-baseline commit + product-tree
  digest + harness-tree digest after registration FREEZE ("HEAD ≥ X"
  rejected: an inequality is not an identity).
- Four fresh controls F7×2 + F12×2 at that identity. Candidate materialized
  once from the frozen H1 surface; differs from control only on that
  surface. Any other product change, any harness change after the first
  control, or any candidate edit after digest-freeze → full control
  recapture.
- Within each pair, match: task/fixture snapshot, runner+harness digest,
  launcher invocation, staged engines bytes, staged settings, CLI/Node
  binary identities, credential/account identity, requested PLAN model, and
  effective PLAN route.
- Every PLAN dispatch (including the one allowed plan re-spawn) requires the
  arm-level requested-model receipt above plus **experiment-side
  worker-session attestation of effective engine and model** (0087 Terra
  canary recipe, `0087:266-275`); explicitly NOT a product transcript parser
  (`0087:133-135` stands).

## STAGE A — EXECUTED RESULTS (2026-08-01/02, all five gates green)

1. Full `lint-skills.sh` exit 0 "All checks passed" including strengthened
   Check 6k (exact-locks on every surface declaration + location-bound: the
   sentence must appear inside `<engine_routing>` AND the PHASE 1 header;
   per-path existence guard). Red-tests: pre-change bytes FAIL, `:104`
   removal FAIL, reordered enumeration FAIL, conjunction prose FAIL, missing
   `.agents` path FAIL, both-sentences-in-one-section FAIL, current tree
   PASS.
2. Three-surface parity clean (config / `.agents` / local `.claude`).
3. Live canary matrix 2/2 by raw receipts (durable:
   `~/.local/share/nx01/iter0088-stagea/`): pin case
   `rs-20260801T142910Z-ebe9e011e4a1` — `state.engine=codex`
   (`engine_source: engines.json`), `phases.plan.engine=claude`, PLAN worker
   sessions attest `claude-sonnet-5` native Agent, IMPLEMENT wrapper-attested
   `gpt-5.6-sol`; flag case `rs-20260801T142846Z-0716be9b07d5`
   (`--engine codex`) — `engine_source: flag`, `phases.plan.engine=claude`,
   all worker sessions `claude-sonnet-5`, full pipeline completed.
4. Formal verify-only `rs-20260801T152441Z-4add8821d052`: **PASS**, zero
   findings (mechanical + codex primary + claude pair). A first formal run
   `rs-20260801T145334Z-df1c3e76ee57` returned NEEDS_WORK with two
   verdict-binding findings — both fixed in fix round 1: (i) 6k count was
   location-blind → location-bound sed-window checks; (ii) the `:57` rewrite
   had scoped role resolution to "Executor role resolution for
   IMPLEMENT/CLEANUP/primary VERIFY judge", silently dropping BUILD_GATE
   from the resolution chain (an unregistered second change, orchestrator's
   spec wording at fault) → unqualified "Role resolution (…)" restored;
   BUILD_GATE ambiguity stays byte-status-quo (Opus F11 mention-only
   honored).
5. Three-seat sign-off: Grok SIGN-OFF; Opus SIGN-OFF conditional on F1
   (resolved via option (b): claim boundary narrowed + README named
   residual) with F2/F4 fixed and F5 disclosed; Codex OBJECT resolved by
   its own accepted falsifier (exact-locks + executed red-tests) AND by its
   primary-judge PASS with zero findings on the final diff in the formal
   run above.

## FREEZE conditions (registration → FROZEN only when ALL hold)

1. Stage A gates 1-5 pass by execution, receipts retained.
2. Satisfiability canary executed by a seat (not asserted): D1 classification
   exercised against the real T1R envelope + one real control receipt;
   effective-model recovery re-executed against the surviving F12 A1 raw
   session AND one Stage-A canary worker receipt.
3. Exact control baseline commit + digests recorded in this file.
   **RECORDED 2026-08-02**: control baseline commit
   `1312cb731c9fc04ed03086d0ad2d7f27b75cda6b` (post-Stage-A); product-tree
   digest (`HEAD:config/skills`) `08d7c2a8efe00ae14bf6d48117ee968604c1ac83`;
   harness-tree digest (`HEAD:benchmark/ceiling`)
   `99464f6f16f3218f2b765ef252ed46e4a7698d19`. Any product or harness byte
   change after the first control invalidates these per D5.
   **AMENDED 2026-08-02, pre-control (zero arms captured)**: executing D4
   against the recorded digest exposed a freeze omission —
   `write_settings_staging_receipt()` at `99464f6f…` receipts only settings
   bytes, so D4's named locus did not exist and the satisfiability canary had
   scoped D4 out ("read as classification context, not executed"). Codex seat
   adjudication (durable receipt
   `~/.local/share/nx01/iter0088-stageb/seats/r0-codex-d4.log`) REVERSED the
   orchestrator's experiment-side-watcher reading via its pre-accepted
   falsifier; named criterion **EXPLICIT INSTRUMENTATION LOCUS** (D4 names the
   authoring site; D5 says "experiment-side" where external observation is
   intended). Minimal harness extension landed as `454bc34` — additive
   receipt fields, `schema_version` stays 1 (`nodeg-cell.py:786` pins it) —
   and was exercised by execution: `test-ceiling-harness.sh` real-A-arm
   exact-equality vs source-tree recompute, `test-nodeg-cell.sh`, full skill
   lint, all green. Control baseline re-recorded: commit
   `454bc3494bb36d5490c9d8fe80f1dde41735d283`; product-tree digest unchanged
   `08d7c2a8efe00ae14bf6d48117ee968604c1ac83`; harness-tree digest
   `86043ad3ab524385926682a0c704817c14901157`. Executed-discovery receipt: a
   live main-repo staging carries 463 git-ignored files under `config/skills`
   (workspace dirs + pycache) absent from a fresh worktree — Stage B arms
   stage from the clean detached worktree; the historical-cohort implication
   is surfaced, not folded (Goal-locked).

Per the binding lesson: a freeze is not frozen until a seat has tried to
satisfy every conjunct by execution.

## FROZEN — 2026-08-02

All three conditions hold. Terra executed the satisfiability canary
mechanically (`~/.local/share/nx01/iter0088-stagea/freeze-canary/satisfiability/`
— `run_canary.py` + `report.{json,md}`): T1R → NULL-ATTEMPT with every
zero-usage/no-artifact conjunct byte-verified; F7/C1 → COMPLETE (startup
239,944 ms, PLAN 116,316 ms; blocked tail correctly ignored); F12 A1
eight-field recovery equal to `0087:266-275` including effective
`claude-sonnet-5`; Stage-A PLAN worker `claude-sonnet-5` native Agent.
`{"ok": true, "unsatisfied": []}`. Orchestrator (Fable 5) independently
cross-checked the T1R envelope, F7/C1 spans, and Stage-A worker receipts
against raw bytes this session. Next execution step: sequential control
capture F7×2 + F12×2 at the amended baseline `454bc34` (freeze condition 3
AMENDED entry; cohort seat pins, updater-proof binary copies, no `/login`
while in flight), then the mechanism-pure H1-v3 candidate and treatments
under D1-D5.

## STAGE B EXECUTED — CLOSED protocol-failed-at-controls (2026-08-02)

Sequenced per the frozen registration at amended baseline `454bc34` (D4-locus
AMENDED entry above). Cohort seats: pinned Claude Code 2.1.215 (`90608b5c…`),
Codex 0.144.5 vendor binary, Node v20.19.0; run id `iter0088sbc`; receipts +
runbook durable at `~/.local/share/nx01/iter0088-stageb/`.

| Arm | D1 | D4 | startup ms | PLAN ms | envelope ms |
|---|---|---|---:|---:|---:|
| F7/C1 | COMPLETE | green | 213,270 | 103,220 | 316,490 |
| F7/C2 | COMPLETE | green | 154,197 | 102,936 | 257,133 |
| F12/C1 | COMPLETE | green | 156,297 | 207,677 | 363,974 |
| F12/C2 | INCOMPLETE #1 | green | — | — | unscored |
| F12/C3 (repl.) | INCOMPLETE #2 | green | — | — | unscored |

All five arms: `state.engine=codex`, PLAN orchestrator-fixed claude, outer CLI
requested `sonnet`, every observed PLAN dispatch effective `claude-sonnet-5` —
Stage A's route contract never flipped once.

**F12/C2 (INCOMPLETE #1)**: the arm's parent composed the PLAN worker prompt
with the canonical body under an **H2** heading; the frozen finder (H1
literal — an executed freeze-canary conjunct, `recovery_checks.py:130`)
matched nothing; fail-closed. The worker itself is the unique `plan.md`
Writer, sidechain, `claude-sonnet-5`. Codex REJECTED the orchestrator's
proposed Write/Edit-based replacement selector — criterion **ALL-DISPATCH
DOMINANCE** (it under-covers pre-write failed dispatches); two orchestrator
packet claims refuted (no plan sha exists in state; the H1 literal WAS
frozen). Replacement consumed (`seats/r1-codex-f12c2.log`).

**F12/C3 (INCOMPLETE #2)**: **three PLAN dispatches** (r0; "ROUND 1,
CORRECTING ROUND 0"; "ROUND 2, narrow sync fix" — state records two
superseded NEEDS_WORK rounds then PASS), breaching the product cap of one
out-of-scope re-spawn + halt-on-second-failure, plus a RISK_PROBES activation
no other F12 arm took (C1 was small-surface demoted). Receipt sources
disagree on startup by 516 s (state-span recompute 697,569 vs
`attribution.startup_ms` 181,191 — rounds 0-1 fall outside the state plan
span). Codex criterion **FROZEN-ORACLE PLUS CONTRACT-CAP**; Grok: two
independent frozen failure paths. INCOMPLETE #2 → **F12 pair-2 row fails
unscored** per the declared D1 budgets.

**Consequence — stop-all, cross-vendor unanimous** (Codex **FOUR-CONJUNCT
DECISION REACHABILITY**: no remaining arm can alter the registered four-pair
go/no-go; Grok **SHIP-CREDIT CONJUNCT EXHAUSTION**;
`seats/r2-{codex,grok}-f12row.log`). No candidate materialized, zero
treatment arms run, no ratio scored. **H1-v3 remains UNSCORED, not
falsified.** Reuse requires a new registration and new controls (0087
precedent). Citation hygiene for that registration: 0087's
independent-conjunct sentence sits at `0087:107`, outside this file's literal
carry ranges — 0088's own four-pair comparator text closed the gap this time;
restate it locally next time.

**Predictions vs outcomes**: P-SB-C1 **FALSIFIED** (two INCOMPLETEs, one
replacement consumed, one row dead); P-SB-C2 held on every captured arm;
P-SB-C3 held 5/5 (harness D4 receipt green everywhere); P-SB-C4 held on the
three COMPLETE envelopes.

**Durable findings**:

1. **Product-side PLAN-region stochasticity at fixed control bytes — the
   cohort-killer and the leading next lever candidate**: 2/5 controls (both
   F12, two distinct classes) produced out-of-instrument receipt shapes:
   (a) instrument-visible heading-level variance in worker-prompt
   composition (H2 for H1); (b) an invented multi-round PLAN correction loop
   past the contract cap + divergent auto-probe routing. The
   violation-matrix lesson (prose contracts are probabilistic) surfacing
   inside the product's own orchestration.
2. **D4 arm-byte attestation shipped** (`454bc34`) and ran green on all five
   arms — engines bytes `5c05302a…`, staged skill tree == pinned source.
3. **A live main-repo staging carries 463 git-ignored files** under
   `config/skills` (workspace dirs + pycache) absent from a fresh worktree —
   historical cohorts staged unpinned bytes; this cohort staged clean (48).
4. Orchestrator seat record: two positions reversed by seats on named
   criteria + one self-caught packet correction (startup-absorption
   wording); all reversals recorded with deltas.

**Advisories frozen for the next registration** (both seats): all-dispatch
oracle supporting the registered 1-or-2 dispatch shape (attest every
dispatch, reject ≥3, round-aware envelope); explicit `startup_recomputed ==
attribution.startup_ms` COMPLETE conjunct; parent composition determinism
either stabilized first or registered as its own scored gate; stop-all +
independent-conjunct text restated in-registration; non-ship measurement
arms only if pre-registered.

## Rejection rules (Stage B)

All of `0087:155-167` carry forward (0.85 breach on any valid pair; startup
increase; two discovery passes; criteria loss/shading; halt migration into
LLM judgment; worker resume / product transcript parser / deterministic
runner / BUILD_GATE transport dependency), plus: an effective-route violation
receipt on any arm rejects that row without replacement; no failure in this
iter authorizes M1.5 work.

## Claim boundary

Stage A PASS claims only: PLAN routing is single-valued across the enumerated
staged surfaces (the closed five-file list + `.agents` mirrors) and
behaviorally deterministic on the two canary paths. **Named residuals**: `README.md:109/:112`
(slash-form and comma-form PLAN∈executor) — README is user territory per
HANDOFF, so it was surfaced 2026-08-01 and **RESOLVED 2026-08-02 on explicit
user directive**: both lines aligned to the orchestrator-fixed contract and
`README.md` added to Check 6k's negative enumeration scan (red-tested: the
pre-fix `:109` line is caught; the frozen copycat corpus fixture
`benchmark/ceiling/corpus/copycat-doc.md` is deliberately NOT scanned);
`devlyn:engines/SKILL.md` is absent from `critical_path_files`
(`lint-skills.sh:58-93`) so Checks 6/6a never compared its mirror — root
cause of the pre-existing doctor-catalog drift the Stage A sync also healed
(disclosed in the commit message), follow-up not folded (Goal-locked). Stage B PASS claims only
what `0087:199-205` claimed. Neither claims whole-cohort wall improvement,
spec-mode generalization, dispatcher authorization, or transport repair.

## Principles check

0. Not score-chasing: removes a receipted arm-killer (T1) and re-opens the
   blocked wall go/no-go. ✅
1. No overengineering: Stage A is a closed 5-file list + one lint conjunct;
   D-texts add no new runtime machinery (parser rejected, retry loop
   rejected). ✅
2. No guesswork: every class boundary and constant is receipt-anchored or
   labeled n=1; predictions before arms; satisfiability by execution. ✅
3. No workaround: route fix lands in the product contract, not an
   experiment-side conjunct alone; the conjunct remains as fail-closed
   detector (prose is probabilistic — violation-matrix precedent). ✅
4/5. Worldclass/best practice: fail-closed everywhere; vendor primitives
   (CLI JSON envelope) over hand-rolled parsing. ✅
6. Layer-cost-justified: no added model calls; Stage A canaries are two
   bounded runs. ✅
7. Mission-bound: Mission 1 only; M1.5 explicitly out. ✅

<!-- devlyn:verification -->
## Verification

- Stage A: gates 1-5 above, all by execution.
- Freeze: conditions 1-3 above.
- Stage B: registered comparator over four matched pairs; three-seat final
  gate + Fable 5 orchestrator verification before any ship credit.

```json
{
  "verification_commands": [
    {
      "cmd": "git diff --check",
      "exit_code": 0
    }
  ],
  "max_deps_added": 0
}
```
