# iter-0067 — ceiling tranche 2 (instrument fixes first, then re-measurement)

status: PRE-REGISTERED 2026-07-07 — phase 1 (judge-fix trio) frozen before
implementation; phase 2 (tranche rows) freezes its corpus before any arm run.

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

## Phase 2 — tranche-2 rows (gated on phase 1 PASS)

Frozen shape (rows themselves selected + hash-frozen only after phase 1):

- Corpus: tranche-1's three rows stay (regression anchors; A-arm re-runs on
  the 0066 skill surface) + new SW rows continuing the 0064 selection walk
  (next eligible rows after 51-52 in the frozen SWE-bench order; same
  eligibility rules), sized so total new arm-wall stays inside one
  overnight window. Real-project row remains USER-GATED and is NOT part of
  this pre-registration.
- Arms/N/loss conditions/judge ordering: identical to the 0064
  pre-registration (objective-first, LC1-LC4, bare/copycat best-of-N,
  blind packets) — tranche 2 changes the instrument ONLY via phase 1's
  three fixes.
- Judge panel: sonnet + codex as certified 2026-07-07 (identities
  unchanged since certification; the judge-quality certification measures
  defect recall, which the ranking-prompt schema fix does not touch —
  recertification triggers on model/version change only, per NORTH-STAR).
- Pair protocol: R0 on the frozen phase-2 corpus + this file BEFORE any
  arm run; R1 on raw results.

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
- **Phase-2 corpus staged + frozen (2026-07-07)**: SW3-django-13315 /
  SW4-django-13321 / SW5-django-13401 (rows 53-55, the frozen walk's next
  django instances — verified against the live dataset order);
  `task.txt` = problem_statement verbatim; oracle smoke **3/3 gold
  resolved** via official harness (`iter0067-oracle-smoke`, report copied
  to `results/oracle-smoke/`); manifest `tranche2` section frozen with
  sha256 hashes + replacement order 13447/13448/13551.
