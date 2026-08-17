---
id: "0103-opus-line-regression-cell"
title: "Opus-line regression cell — opus-4.8 vs opus-5 on the sealed 0102 discovery corpus"
kind: instrument
status: DESIGN-FROZEN 2026-08-16 — R0 sol REVISE ×5 + grok REVISE ×5 all adopted; R2 sol FREEZE + grok FREEZE (zero findings). Derived-scorer byte pin recorded at apparatus freeze (§ Sequencing 3)
complexity: medium
depends_on: ["0102-executor-quality-discovery-corpus"]
---

# iter-0103 — opus-4.8 vs opus-5 on the 0102 discovery corpus

## Motivation (user-directed, 2026-08-16)

The felt regression that started this measurement lineage was
"opus-4.8 did well; opus-5 got strange" (2026-07-28 diagnosis: part of
the felt regression was an uncertified seat + one mis-score, but not
all of it; iter-0099 seat certification showed a raw signal opus-4-8
10/24 vs opus-5 3/24 on a weakly discriminating instrument; iter-0100
SATURATED at Δ=0.0). The 0102 matrix cell (opus-5 vs fable-5) decides
the forward executor seat but CANNOT attribute a regression without
the 4.8 baseline — whichever way it lands. The 0102 corpus is the
first instrument in three iterations to calibrate mid-band (sonnet
mean 39/80, interior 30/32), so the regression question is now
answerable at low marginal cost. User go-ahead 2026-08-16.

## Engine order (FROZEN — R0103 both-seat finding 1)

Ordered tuple everywhere: `ENGINES = ("claude-opus-5",
"claude-opus-4-8")`. The scorer's per-task differences are
`fail(ENGINES[0]) − fail(ENGINES[1])` = fail(opus-5) − fail(opus-4-8);
a positive difference means opus-5 fails more (regression direction).
Driver `ALLOWED_ENGINES`, launcher `ENGINES`, derived scorer
`ENGINES`, and the launch-receipt `engines` field all carry this exact
ordered pair.

## Inherited by reference (all FROZEN)

- Corpus: the sealed 0102 candidate —
  `~/.local/share/nx01/iter0102/freeze/candidate-manifest.json`
  (file sha256 `80f0a12ddb6df006c4137ecbc96c557742f8bbe74b0cacf65466c3af6dcd8887`,
  tree `294eeadea37889e99f8dee1dc6021d353ac1f835fda46d6b1827480cc9a0fe5b`,
  32 tasks / 1045 files). No corpus edits; a frozen-file change is a
  spec violation.
- Apparatus bases: the FREEZE-ARMed 0102 matrix apparatus
  (`mx-driver.py` 49f30de8… / `mx-launcher.py` 2123c400… /
  `run-bounded.py` db9ed383… / launch gate 759be106…). Schedule
  mechanism (128 cells, ABBA interleave), BOUND_SEC, pinned CLI
  `013a1cf1…`, per-row exact-ID modelUsage attestation, failure
  taxonomy, opaque workdirs, manifest double binding: byte-preserved.
- Operational rules carried verbatim from 0102: both-seat
  infra-authenticity adjudication before burning a replacement
  launch; MISS + success-subtype/empty-attestation rows → CONTESTED
  escalation to the user; difficulty-oracle prohibition (no
  sonnet/opus/fable invocation on any corpus workdir outside the
  scheduled arm runs).

## Enumerated deltas (COMPLETE list — R0103 grok-1/grok-4, sol-3)

1. **Scorer re-pin** (0102-precedent single-transformation re-pin):
   base = sealed `benchmark/executor-quality/scripts/score-cohort.py`
   (`399b0691…`, untouched in the repo); transformation = replace
   every literal `"claude-fable-5"` with `"claude-opus-4-8"`; output =
   `~/.local/share/nx01/iter0103/apparatus/score-cohort-0103.py`,
   byte-pinned at freeze (pin recorded in this file's freeze
   amendment + the 0103 freeze inventory). The transformed
   `--self-test` must pass in full and is recorded pre-arm. ENGINES
   order in the base is already `("claude-opus-5", …)` — the
   transformation preserves the frozen order above. The repo's 0102
   scorer and `scripts.sha256` are NOT modified.
2. **Driver/launcher**: `ALLOWED_ENGINES` / `ENGINES` → the frozen
   ordered pair (+ docstrings). Nothing else.
3. **Launch gate** (base 759be106…): `LAUNCHER` unchanged
   (`mx-launcher.py`); `ENGINE = "claude-sonnet-5"` (stale
   calibration-lineage constant; see Deviations note) → `ENGINES`
   ordered pair, and the receipt field `engine` → `engines`
   (the ordered pair, verbatim); `FREEZE_FILE` →
   `frozen-0103-apparatus.sha256`; inventory/`required` entries →
   {mx-driver.py, mx-launcher.py, run-bounded.py,
   candidate-manifest.json, score-cohort-0103.py,
   launch-detached.py}; `SCRIPTS`-relative scorer entry → the derived
   scorer's absolute path; docstrings. Nothing else.

## Design (knobs FROZEN — R0103 sol-4/sol-5)

- 2 reps × 32 tasks × 2 engines = 128 scored runs, ABBA, fresh cohort
  run-id `mx3-<UTCSTAMP>Z`, attempts 1..3.
- **Lanes = 2, FROZEN** (the launcher's default; no `--lanes` argument
  is passed and none is added to the gate). Lane count is evidenced by
  the schedule shape in the cohort output (two lane dirs × 64 rows).
- **Launch window, FROZEN**: no launch between 23:00 and 01:00 KST.
- Seat availability precheck (DONE 2026-08-16): pinned CLI 2.1.226
  attests canonical `claude-opus-4-8` (modelUsage exact-ID, 1-turn
  smoke, receipt in session log).

## Pre-registered prediction (single — R0103 both-seat terminal-bijection finding)

- **P-0103-1**: the derived scorer's terminal token IS the decision;
  the frozen bijection to this cell's narrative is:
  `H1_CONFIRMED` (bootstrap CI lower bound > 3/20 on
  fail(opus-5) − fail(opus-4-8)) ⇔ P-0103-1 CONFIRMED — a
  live-signal-sized opus-line regression is evidenced at this shape;
  `H1_MATERIAL_GAP_REFUTED` (CI upper bound < 3/20) ⇔ P-0103-1
  REFUTED — narrative alias `OPUS_LINE_MATERIAL_GAP_REFUTED`, scorer
  token authoritative; remaining candidates (true repo scale,
  session-horizon effects) are NEW registrations;
  `INCONCLUSIVE_AT_PILOT_N` and `SATURATED` (both engines ≥ 63/64
  all-clean; band non-transfer datum) carried verbatim, neither
  confirms nor refutes.

## Information boundary (R0103 grok-5)

This registration must be FROZEN before the orchestrator reads any
0102 matrix cohort row CONTENT or score. As of DRAFT r2, only
opaque row COUNTS (watcher `wc -l`) have been observed. The 0102
evaluation runs only after 0103 FREEZE; this cell's own launch waits
further until the 0102 cohort completes (no lane/quota contention).

## Diagnostics (non-decisional)

Cross-cohort opus-5 consistency: opus-5's per-task q vector in this
cohort vs the 0102 matrix cohort — a diagnostic table only; no
decision rule attaches. Role-level failure detail stays in
per-attempt `oracle.json` receipts.

## Deviations noted at registration

The live 0102 matrix launch receipt (`mx-20260815T234335Z`) carries
`engine: "claude-sonnet-5"` — a stale calibration-lineage constant,
non-load-bearing (scoring reads per-row ledger attestation), logged
in `~/.local/share/nx01/iter0102/matrix/operator-deviations.log`, NOT
retroactively edited (0089 Attestation-Result Fidelity). Root-fixed
here by enumerated delta 3.

## Sequencing

1. This registration → 2-seat design review round 2 → FREEZE
   (freeze amendment records the derived-scorer byte pin).
2. 0102 matrix cohort completes → 0102 evaluation + records.
3. 0103 apparatus build (terra byte-surgery, orchestrator full-diff
   review) → freeze inventory → sandbox tamper probes → two-seat
   FREEZE-ARM ×2 → launch → ONE evaluation → DECISION recorded here
   + memory.

## Receipts layout

`~/.local/share/nx01/iter0103/` — apparatus/ (incl. derived scorer),
freeze file, attempt dirs, cohort receipts, evaluation output.

## Execution log

**Sequencing 2 DONE (2026-08-17 22:45 KST)** — 0102 CLOSED
`H1_MATERIAL_GAP_REFUTED` (attempt 2 `mx-20260817T121817Z`; attempt 1
infra-invalid by account session limit, both-seat adjudicated — see
0102 § Execution log). Information boundary held: this file was
untouched between its FREEZE commit `c3af2a8` and this entry; the
first 0102 row content read by the orchestrator was 2026-08-17 21:00
KST, after freeze.

**Sequencing 3 — apparatus build (2026-08-17 22:42-22:50 KST, terra
byte-surgery, `~/.local/share/nx01/iter0103/BUILD-SPEC.md` →
`BUILD-REPORT.md`; orchestrator full-diff review PASS: every hunk is
an enumerated delta).** Byte pins (candidate freeze inventory
`frozen-0103-apparatus.sha256`):
`mx-driver.py` 955979e2… (base 49f30de8… + `ALLOWED_ENGINES` member +
docstring) · `mx-launcher.py` ee8b2f69… (base 2123c400… + `ENGINES`
tuple + docstring) · `run-bounded.py` db9ed383… (byte copy) ·
**derived scorer `score-cohort-0103.py` cc9f6068facc9a3b17ae059b572ddb9fd1584d568f5878687ce3906a6962be28**
(= repo 399b0691… with the single `"claude-fable-5"` literal →
`"claude-opus-4-8"`, sha recomputed independently by orchestrator via
sed; `--self-test` SELF_TEST_OK; repo scorer + `scripts.sha256`
untouched) · `launch-detached.py` 15446c06… (base 759be106… + delta 3;
`SCRIPTS` constant left unreferenced — unenumerated deletion not
allowed) · `candidate-manifest.json` 80f0a12d… (inherited by absolute
reference). Sandbox tamper probes 6/6 fail-closed + `--attempt 4`
range control refused (BUILD-REPORT § 5). Two-seat FREEZE-ARM audit
(sol + grok, packet `freeze-audit-packet.md`) dispatched 22:58 KST.

**FREEZE INVENTORY (immutable root; full digests — sol R1 F1 closure).**
The candidate `frozen-0103-apparatus.sha256` byte-for-byte:

```
955979e2941a61c8136b11335ca863edd0c94aa17c758d9c4a8d80787e8cd394  mx-driver.py
ee8b2f691619d5213e638605e2814f0baffa7ae55bad35231196814680564b3a  mx-launcher.py
db9ed3832e444449263a5ca3bdeccba41d91722ef2070115107b6caf82424ca5  run-bounded.py
80f0a12ddb6df006c4137ecbc96c557742f8bbe74b0cacf65466c3af6dcd8887  candidate-manifest.json
cc9f6068facc9a3b17ae059b572ddb9fd1584d568f5878687ce3906a6962be28  score-cohort-0103.py
15446c0608e0d4eee379bc1fb3b07388f7393bce73b7f0d964f37e707142bcbf  launch-detached.py
```

Pre-committed operational rules (zero apparatus byte change; close the
coordinated {apparatus, freeze-file} tamper class sol raised — the
gate learns driver/launcher/self hashes from the mutable freeze file):
- **R-A (pre-launch)**: immediately before the gate runs, the live
  `frozen-0103-apparatus.sha256` must equal the six 64-hex entries
  above (exact full-digest comparison against `git show` of this
  file at its committing revision), AND the six live files must hash
  to them; any mismatch → no launch.
- **R-B (pre-score)**: before the derived scorer runs, the launch
  receipt `apparatus_sha256` map (driver, launcher, run-bounded,
  candidate-manifest, score-cohort-0103.py, launch-detached.py) must
  equal the same six full digests; mismatch → cohort UNSCORED
  (infrastructure-invalid launch), never scored.
- Sol R1 F2 (launcher docstring index convention) CONVERGED-REFUTED:
  `enumerate` 0-based index, base convention preserved.

**Two-seat FREEZE-ARM ×2 ACHIEVED (2026-08-17 23:20 KST).** grok R0
FREEZE-ARM (zero findings; synthetic-ledger proofs a-f against the
derived scorer, terminal bijection, information boundary, ops). sol
R0 REVISE ×2 → R1: F2 (launcher docstring index) CONVERGED-REFUTED;
F1 (gate learns driver/launcher/self hashes from the mutable freeze
file — coordinated tamper class) HELD with a valid falsifier against
my 8-hex committed pins → closed by committing the full inventory +
R-A/R-B above (`6ec8e5e`) → sol R2 FREEZE-ARM (zero findings).
Record + logs: `~/.local/share/nx01/iter0103/FREEZE-ARM-RECORD.md`.
Launch = attempt 1 (`mx3-<UTCSTAMP>Z`) after 01:00 KST under the
recorded conditions (exclusive account, exact-ID smoke, R-A).
