# iter-0067 — ceiling tranche 2 (instrument fixes first, then re-measurement)

status: IN-FLIGHT 2026-07-08 — phase 1 (judge-fix trio) CLOSED + committed
(3e64cba); phase-2 R0 NO-GO → all MUST-FIX landed → R1 GO (12d54e1);
phase-2 tranche `iter0067-t2` (SW3/SW4/SW5, self-driving arm→eval→gate→judge
→verdict, neutral judge prompt) LAUNCHED and running unattended. Closure
(R1-on-results + verdict adjudication + HANDOFF/DECISIONS) pending the run.

**Serves**: Mission 1 ceiling axis — NORTH-STAR ceiling contract / ops test
#17. Tranche-1 verdict was FAIL-pilot on LC3; iter-0065 + iter-0066 shipped
every product lever licensed from that pilot. Tranche 2 re-measures. HANDOFF
orders the work: "FIRST fix 0064 follow-ups #3".

## Why this exists (pre-flight 0)

One sentence: tranche-1's measurement had three instrument defects that
must be fixed before tranche 2 can produce a valid LC verdict — SW2's
subjective rankings were LOST entirely (both judges absent from the
aggregate), the codex judge produced zero valid rankings anywhere, and the
SW objective rows carry a mislabeled reporting field — and this iter is the
last attribution run before the next ceiling go/no-go decision (the
measurement-iter carve-out in PRINCIPLES #0).

Mission-bound (#7): Mission 1 ceiling gate; tranche 2 is the decision run.

## Phase 1 — judge-fix trio (0064 follow-up #3; instrument-only)

### Evidence (all opened this session)

- `ceiling-judge-aggregate.json` (iter0064-t1): `tasks` carries per-judge
  rows for FS1 + SW1 only, sonnet only — SW2 has empty `per_judge` on all
  four axes; codex absent everywhere.
- **Defect 1 (codex string deltas)**: `ceiling-judge.py:313` — the prompt's
  schema example shows `"strict_win_deltas":[]` and never the delta OBJECT
  shape; codex returned string deltas; `validate_response` (`:117` "delta
  entries must be objects") correctly rejected them. 0064 R1 ruling stands:
  fix the prompt schema-first per official structured-output guidance,
  do NOT relax the validator.
- **Defect 2 (sonnet timeout on big packets)**: `call_sonnet`
  (`ceiling-judge.py:148`) hard-codes `timeout=300`; `call_with_retry`
  (`:256`) retries only `parse_error:` — a transport timeout is terminal on
  attempt 1. SW2's packet = task text + three large django diffs; sonnet
  timed out → rankings lost. codex path has the same 300s bound (`:207`).
- **Defect 3 (f2p_total mislabel, reporting-only)**: SW1 A1
  `objective.json` says `f2p_passed: 1, f2p_total: 64`; SW2 A1 `4/417`.
  `ceiling-eval.sh:99` computes `len(instance.get("FAIL_TO_PASS"))` — the
  SWE-bench instance serializes FAIL_TO_PASS/PASS_TO_PASS as JSON STRINGS,
  so `len()` counts characters. Verdict-neutral (gate keyed on `resolved`),
  but every human-read ratio is wrong.

### Fix (frozen)

1. `ceiling-judge.py` prompt: show the exact delta object schema
   (`{"winner":"P2","loser":"P1","delta":"<one concrete sentence>"}`) inside
   the axis example + "output ONLY the JSON object, no prose before or
   after". Validator byte-for-byte unchanged.
2. `ceiling-judge.py` transports: judge call timeout 300 → 900 (both
   engines — xhigh reasoning over three large diffs; observed sonnet loss
   at 300); `call_with_retry` also retries ONCE on
   `transport_error: timeout` (other transport errors stay terminal).
3. `ceiling-eval.sh`: JSON-decode FAIL_TO_PASS / PASS_TO_PASS when they
   arrive as strings before `len()`.

### Predictions (phase 1, frozen before implementation)

- **P1**: re-running the judge on the UNCHANGED tranche-1 SW2 artifacts
  (same `--select` rows, same patches, output to a fresh run dir —
  tranche-1 aggregate stays immutable) produces, for BOTH judges, valid
  rankings on all four axes: SW2's lost rankings are recovered and the
  codex judge produces its first valid ceiling rankings. Mechanism:
  defect-1 prompt + defect-2 timeout were the only loss paths.
- **P2**: the recovered SW2 + re-judged FS1/SW1 A-vs-C outcomes are
  RECORDED RAW as instrument validation only — tranche-1's shipped verdict
  (FAIL-pilot) is never retro-edited; any judge-fix-induced ranking delta
  vs the tranche-1 aggregate is listed, not re-adjudicated.
- **P3**: SW objective rows re-derived from the existing tranche-1 eval
  reports show `f2p_total` equal to the instance's true FAIL_TO_PASS test
  count — verified NOW against `hidden/instance.json` (both stored as JSON
  strings): SW1 django-13230 = 1, SW2 django-13265 = 4 (so A1 rows become
  1/1 and 4/4, consistent with `resolved: true`); `resolved` values
  unchanged.

### Loss conditions (phase 1)

- **L1**: P1 falsified for the sonnet judge (still no valid SW2 rankings at
  900s) → packet size itself is the root cause; STOP, re-design (packet
  segmentation or per-axis calls) with its own pre-registration — do not
  ship tranche 2 on a judge that cannot rank its largest row.
- **L2**: P1 falsified for the codex judge (schema-first prompt still
  yields invalid shapes on 2 attempts) → codex judge drops from the
  tranche-2 panel (sonnet-only, honestly labeled single-judge), logged for
  a dedicated structured-output iter.
- **L3**: P3 falsified (decoded totals still wrong) → revert defect-3 edit,
  keep the mislabel documented as reporting-only.

## Phase 2 — tranche-2 rows (gated on phase 1 PASS + R0 GO)

Frozen corpus (hashes in `manifest.json` `tranche2`; dataset-order proof in
`corpus/tranche2-dataset-order.json`):

- **Corpus = three fresh holdout rows ONLY**: SW3-django-13315 (row 53),
  SW4-django-13321 (row 54), SW5-django-13401 (row 55) — the
  mechanically-next django instances of SWE-bench Lite after tranche-1's
  rows 51-52 (frozen-walk continuation; replacement order 13447/13448/
  13551). Oracle smoke 3/3 gold resolved. **Tranche-1 regression re-runs
  DROPPED (R0 SHOULD-FIX 1, subtractive)**: re-running SW1/SW2/FS1 A-arm
  here would double-count pilot rows in the phase-2 aggregate; the 0066
  skill-surface regression is already covered by iter-0066's own SW2
  re-run. Real-project row remains USER-GATED, not in this pre-registration.
- Arms/N/loss conditions/judge ordering: identical to the 0064
  pre-registration (objective-first, LC1-LC4, bare/copycat best-of-N,
  blind packets). Instrument changes vs 0064 = phase-1's three judge fixes
  + R0's harness fixes below.
- Judge panel: sonnet + codex, certified 2026-07-07 (identities unchanged;
  the ranking-prompt schema fix does not touch defect-recall certification
  — recert triggers on model/version change only, per NORTH-STAR).
- **Single-repo caveat (R0 POS-1, honest label)**: all three rows are
  django. The phase-2 verdict is a django-shaped ceiling probe, not a
  cross-repo claim; cross-repo breadth is a later tranche.

### R0 adopted edits (2026-07-07, before any arm run)

R0 verdict **NO-GO** (archive `/tmp/codex-iter0067/r0-response.log`) — it
caught that the harness could not run tranche-2 rows at all. All fixes
landed before launch:

- **MF1 (harness allowlist hardcoded to tranche-1)**: `run-ceiling-arm.sh`
  + `ceiling-eval.sh` rejected SW3/SW4/SW5. Root-cause fix: task allowlist
  is now manifest-derived (union of `tasks` + every `trancheN.tasks`),
  so it never goes stale — a new tranche needs no script edit.
- **MF2 (oracle gate hardcoded to `gold.iter0064` + `>=2`)**:
  `ceiling-gate.py oracle_smoke_ok()` now takes the gated tasks and
  requires per-instance resolved evidence from ANY
  `gold.*-oracle-smoke.json` (tranche-1 → iter0064 report, tranche-2 →
  iter0067 report). No run-id literal remains.
- **MF3 (row-order claim unreproducible)**:
  `corpus/tranche2-dataset-order.json` commits the live dataset slice
  (rows 50-57) proving 53-55 = 13315/13321/13401.
- **SF1 adopted**: tranche-1 regression rows dropped (above).
- **SF2 (judge example bias)**: the schema example repeated P2>P1>P3 on
  every axis. Neutralized — varied orders + a tie per the shape, explicit
  "illustrative shape only, do not copy this ordering." P1 re-validated on
  the neutral example (falsifier: material tie/win-rate shift = old example
  was biasing).
- **Logged, not blocking (R0 SHOULD-FIX)**: hidden fields are not staged
  into solver worktrees (same guarantee tranche-1 used; OS-level isolation
  is a separate hardening iter).

Regression guard: `--phase verdict` on iter0064-t1 (copied to scratch)
still reproduces FAIL-pilot, original artifact byte-unchanged; the only
verdict-json diffs are the run-id string + task iteration order.

### Pair protocol

- R0 on the frozen phase-2 corpus + this file: DONE (NO-GO → all MUST-FIX
  adopted). A bounded R1 confirms the fix diff (NEW evidence = the fixes)
  before arm launch.
- R1 on raw arm results after the tranche completes.

## Pair rounds

- Phase-1 R0: the fix trio is 0064's OWN R1-adopted follow-up list —
  pre-adjudicated there; a fresh R0 for phase 1 would re-litigate a closed
  adjudication (anti-asymptotic rule). R0 fires on phase 2's corpus freeze.
- (pending)

## Execution record (raw only)

- **Phase-1 implementation (2026-07-07, Codex CLI workspace-write xhigh,
  archive `/tmp/codex-iter0067/impl-response.log`)**: +19/−8 across the two
  scripts. Schema-first prompt (full delta-object example per axis +
  output-only instruction; `validate_response` byte-identical); timeouts
  300→900 both engines + one retry on `transport_error: timeout` only
  (unit-checked: timeout retries once, other transport errors terminal);
  f2p/p2p JSON-string decode. Orchestrator re-ran lint: "All checks
  passed." (Codex-sandbox npm EPERM was environmental.)
- **P3 PASS**: recount from existing tranche-1 eval reports — SW1 A1
  `1/1`, SW2 A1 `4/4`, `resolved` unchanged; matches the frozen
  prediction's now-verified instance counts exactly. Tranche-1 artifacts
  untouched.
- **P1 PASS (2026-07-07, run `iter0067-p1-judgefix` — tranche-1 patches
  copied to a fresh run dir, tranche-1 aggregate immutable)**: **24/24
  valid judge-axis cells** (3 tasks × 4 axes × 2 judges; tranche-1
  produced 8/24 — sonnet on FS1+SW1 only), zero transport/parse errors.
  SW2's lost rankings recovered; first valid codex-judge ceiling rankings.
- **P2 raw (recorded, not re-adjudicated)**: A-vs-C on subjective axes =
  C_win 24/24 (every task, axis, judge). Reproduces tranche-1's product
  finding #3 (judges prefer plausible-but-wrong copycat diffs over
  objectively-resolving devlyn diffs) now with cross-judge agreement —
  strengthens the pre-registered objective-first verdict ordering;
  tranche-1's shipped FAIL-pilot verdict is not re-opened.
- **SF2 falsifier FIRED (2026-07-07, `iter0067-p1b-neutral` vs
  `iter0067-p1-judgefix`, same tranche-1 patches)**: the P2>P1>P3-on-every-
  axis example WAS biasing judges. Original example → A/C/tie **0/24/0**;
  neutral example → **5/19/0** — SW2 flipped 0/8 → 4/4 (sonnet+codex each
  recovered A-wins the biased example suppressed); SW1 0/8 → 1/7; FS1
  unchanged 0/8. Interpretation: the neutral prompt is the trustworthy
  instrument (adopted for tranche 2). The subjective-axis copycat lean
  survives directionally (19/24 C_win) so the **objective-first ordering
  safeguard is still load-bearing** — and the fact that a worked-example
  order could move 5 cells is itself the strongest argument for never
  letting subjective axes override objective acceptance checks. Tranche-1's
  finding #3 magnitude was prompt-inflated; its DIRECTION (subjective
  judges lean plausible-but-wrong) holds. Tranche-1's shipped verdict is
  not re-opened (different prompt, immutable artifact).
- **Phase-2 corpus staged + frozen (2026-07-07)**: SW3-django-13315 /
  SW4-django-13321 / SW5-django-13401 (rows 53-55, the frozen walk's next
  django instances — verified against the live dataset order);
  `task.txt` = problem_statement verbatim; oracle smoke **3/3 gold
  resolved** via official harness (`iter0067-oracle-smoke`, report copied
  to `results/oracle-smoke/`); manifest `tranche2` section frozen with
  sha256 hashes + replacement order 13447/13448/13551.
