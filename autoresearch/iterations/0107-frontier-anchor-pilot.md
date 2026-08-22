---
id: "0107-frontier-anchor-pilot"
title: "Frontier-anchor pilot — re-anchor the repo-scale band on the matrix engines"
kind: instrument
status: REGISTERED-FROZEN 2026-08-22 — trio freeze complete (FREEZE-0107-REG-GROK + FREEZE-0107-REG-SOL after r1b/r1c residual folds; fable adjudication); next = apparatus derivation (terra single-writer)
complexity: medium
depends_on: ["0105-repo-scale-discovery-corpus"]
---

# iter-0107 — frontier-anchor pilot

## Why this iter exists (pre-flight 0)

0105 closed TERMINAL `MECHANISM_REJECTED`: the four frozen EQ4P
prototypes sit ABOVE the sonnet calibration band (mean > 3/5,
interior < 3, one prototype at q=1; per-task numerics sealed; do NOT
identify which prototype ceilinged). The sonnet band was a PROXY for
the direct requirement — that the MATRIX engines (opus-5 vs
opus-4-8) land in the interior where differences are visible. User
requirement-level reframing (2026-08-21): do NOT lower difficulty on
an extrapolation; a hard corpus is potential headroom (golden suite
was retired for saturating EASY;
`feedback_pair_measurement_needs_headroom`). Both directions are
currently guesses: "too hard for frontier too" extrapolates the
sonnet result; "frontier will be interior" extrapolates the 0102
ordering (sonnet 0.49 · opus-4-8 0.475 · opus-5 0.29-0.31 at 32-file
shape). No guesswork: measure the anchor engines directly on the
frozen prototypes. Change the QUESTION, not the trees.

## Decisive criterion

The registration is FROZEN-worthy iff a fresh session could execute
it mechanically and its PROCEED/REJECT answers exactly one
question — "is the frozen EQ4P difficulty usable for an opus-5 vs
opus-4-8 repo-scale matrix?" — with no unscored ambiguity, no
leakage of sealed 0105 outcomes into design, and no scope beyond the
anchor decision.

## Principles check

- **Pre-flight 0** (FIRST) ✅ Passes — this iter exists because it
  unblocks the go-no-go decision for the repo-scale corpus
  successor — whether the frozen EQ4P difficulty advances or
  difficulty re-derivation is evidenced — after 0105's terminal
  REJECT left that question unmeasured.
- **#7 Mission-bound** (SECOND) ✅ Passes — this iter serves
  Mission 1's ceiling-instrument track because it decides whether
  the unchanged EQ4P difficulty can advance to a separately
  registered opus-5 vs opus-4-8 repo-scale matrix corpus.
- **#1 No workaround** ✅ Passes — fail-closed gates carried (launch
  gate digest pins, ordinal locks, three-route verdict domain; no
  config bypass).
- **#2 No overengineering** ✅ Passes — anchor decision only; no
  corpus stage, no new flags, no adaptive control flow;
  `APPARATUS_INVALID` token and receipt-bound quiet-account
  attestation declined for lack of a learned failure.
- **#3 No guesswork** ✅ Passes — this iter IS the measurement; both
  direction hypotheses are named as unmeasured extrapolations in
  pre-flight 0.
- **#4 Worldclass** ✅ Passes — 0105 freeze/derivation discipline
  carried in kind (digest pins, reversal proofs, sealed boundary,
  trio audit before launch).
- **#5 Best practice** ✅ Passes — 0103 ABBA two-engine shape as the
  established precedent; exact `Fraction` arithmetic; standard
  clause-isolated self-tests.
- **#6 Optimized** ✅ Passes — 16 fixed runs at peak concurrency 2
  close the question in one detached launch (~2× the measured 0105
  pilot wall); the adaptive opus-5-first alternative was rejected at
  R0 because its saved runs do not pay for its added control flow
  and temporal asymmetry (BILATERAL DECISION SUFFICIENCY).

## Registered treatment

**16-run anchor pilot**: the four 0105 EQ4P prototype trees
BYTE-IDENTICAL (pins carried verbatim: UA1 `453093a6…` · MI1
`40b6db84…` · AF1 `0d567197…` · BD1 `ad69e711…`; manifest
`78d153da…`, canonical tree `ff97a3e4…`) × 2 reps × engine tuple
`("claude-opus-5", "claude-opus-4-8")` (ORDERED, 0103 precedent;
exact IDs everywhere — schedule, receipt, scorer).

**Derivation is FILE-LEVEL, never lane-root-level** (SEALED CAUSAL
ISOLATION): the new lane root is `~/.local/share/nx01/iter0107/pilot/`;
the ONLY readable 0105 sources are these digest-pinned files —
`pilot-driver.py` `77ae280f…`, `pilot-launcher.py` `e86d8b38…`,
`run-bounded.py` `db9ed383…`, `launch-detached.py` `cfbda3af…`,
`score-pilot-0105.py` `31916d00…` (as scorer-derivation base),
`pilot-manifest.json` `78d153da…`. Reading, listing, or copying
`~/.local/share/nx01/iter0105/pilot/attempt-*`, `DECISION*`, or any
verdict/receipt carrier is PROHIBITED for every seat and writer in
this lane (0105 per-task outcomes stay sealed and are not an input).

### Complete delta classes (frozen NOW; exact bytes reversal-proven at derivation)

- **driver** (2): docstring/iter label; `ALLOWED_ENGINES` → the two
  anchor IDs. Taxonomy carried VERBATIM (combined stdout+stderr
  `INFRA_FAILURE`, zero-turn ⇒ infra except the registered rc=124
  censoring branch ⇒ terminal f=1; `--engine` per-row plumbing
  already exists in the base). **No opus-specific taxonomy delta**:
  the classifier is engine-agnostic; auxiliary/helper `modelUsage`
  handling must NOT be "fixed" in this lane.
- **launcher**: `ENGINE` → ordered `ENGINES` tuple; docstring
  (base's "0105 8-run sonnet … single engine" description →
  0107 16-run two-engine); schedule = the 0103 two-lane ABBA
  formula frozen EXACTLY as `ENGINES[(i + rep + group) % 2]` with
  the 2-lane task split (source precedent
  `iter0103/apparatus/mx-launcher.py:22-33`), instantiated for
  4 tasks × 2 reps × 2 engines = 16 rows — every `(engine, task,
  rep)` cell exactly once, engine order balanced across lanes and
  reps, peak concurrency 2 (unchanged from 0105). No `--lanes` flag.
  Adjudicated over serial-per-engine (TIME-SYMMETRY: serial confounds
  engine with account time window; ABBA is the 0103-proven two-engine
  shape on this account — the 0102 attempt-1 session-limit failure
  was account noise, refuted as a schedule property by the clean
  same-shape attempt 2 and 0103 attempt 1).
- **launch gate**: `ENGINE` → ordered `ENGINES`; docstring/contract
  text (base's "exact sonnet identity" line → two-engine identity);
  receipt field
  `engine` → `engines` (exact ordered list) + schedule digest;
  `FROZEN` map → derived driver/launcher digests +
  `score-pilot-0107.py`; freeze-inventory filenames. Ordinal locks,
  attempt cap 3, `start_new_session` carried.
- **scorer**: NEW frozen `score-pilot-0107.py` derived from
  `31916d00…` with enumerated deltas: `ENGINES` tuple;
  `row_count == 16`; cells `(engine, task, rep)` complete-matrix
  validation; per-engine aggregation; **delete `has_total_failure`**
  (0105's C2, superseded by gate 3 below); § Decision rule verbatim.
  q semantics carried from `31916d00…`: per rep
  `f = Fraction(failed, total)`, or `Fraction(1)` for
  catastrophic/incomplete; `q(e,t) = (f(e,t,1) + f(e,t,2))/2`;
  `mean(e) = Σ_t q(e,t)/4`; exact `Fraction` throughout.

Non-deltas (byte-carried on purpose): `BOUND_SEC = 1800`
(OUTCOME-INDEPENDENT CENSORING CONTROL — not raised for opus),
`EFFORT = "high"`, `TOOLS`, pinned CLI
`~/.local/share/nx01/pins/claude-2.1.226-iter0100/claude`
(`013a1cf1…`), `run-bounded.py`, prompt = task goal only, scrubbed
env, opaque workdir copytree, manifest/tree pins.

### Scorer self-tests (all clause-isolating, reachable, synthetic 16-row)

1. both-ceiling: both engines `[1, 2/5, 2/5, 2/5]` (mean `11/20`,
   interior 3) — gates 1-2 pass, ONLY gate 3 rejects.
2. single-ceiling: e0 `[1, 2/5, 2/5, 2/5]`, e1
   `[2/5, 2/5, 2/5, 2/5]` — PROCEED (replaces 0105
   `e-total-prototype`).
3. different-task dual ceiling: e0 `[1, 2/5, 2/5, 2/5]`, e1
   `[2/5, 1, 2/5, 2/5]` (both means `11/20`, interiors 3, no shared
   ceiling task) — PROCEED (not a both-ceiling).
4. per-engine band isolation: e0 `[4/5, 4/5, 4/5, 4/5]` (mean `4/5`
   out of band, interior 4), e1 `[1/5, 1/5, 1/5, 1/5]` — REJECT via
   gate 1 only (pooled mean `1/2` must not rescue).
5. per-engine interior isolation: e0 `[1, 0, 2/5, 2/5]` (mean
   `9/20` in band, interior 2 < 3), e1 `[2/5, 2/5, 2/5, 2/5]` —
   REJECT via gate 2 only (no shared-task ceiling, so gate 3 is not
   triggered).
6. both-floor tolerated: both engines `[0, 2/5, 2/5, 2/5]` (mean
   `3/10` in band, interior 3) — PROCEED.
7. catastrophic carry per engine (0105 `h`: total=0 cat ⇒ f=1).
8. complete-cell validation: missing/duplicate `(engine, task, rep)`
   ⇒ UNSCORED; wrong engine id ⇒ UNSCORED.
9. determinism double-run byte-identical.

Additionally at derivation freeze: the driver taxonomy fixture set
runs once per exact ID (success, combined-stream 429/529/
session-limit, zero-turn success/error, rc=124 empty attestation,
wrong engine, multi-engine attestation, non-success after turns,
false-positive infra text).

## Decision rule (frozen at registration; scorer implements verbatim)

Let q_e(t) be as defined above.

**PROCEED** iff ALL of:
1. for EACH engine e: mean(q_e) ∈ [1/10, 3/5];
2. for EACH engine e: ≥3 of 4 prototypes interior (0 < q_e(t) < 1);
3. NO prototype has BOTH engines at q == 1.

Gate 3 rationale is OUTCOME-INDEPENDENT (bilateral differential
observability, stated before any 0107 row exists — not derived from
the sonnet ceiling): a both-ceiling task is zero contrast for a
difference instrument; a SINGLE-engine ceiling is contrast, not a
defect, and gate 2 already caps each engine at one non-interior
slot. The asymmetry with the floor is deliberate and frozen: joint
impossibility is fatal; a single both-floor prototype is tolerated
as an apparatus-health control (0105-inherited asymmetry —
`has_total_failure` had no floor twin; no learned failure motivates
a floor ban).

**Verdict domain (three routes, conserved)**:
- Valid complete ledger failing any gate → terminal
  `BAND_REANCHOR_REJECTED`: the frozen EQ4P difficulty is unusable
  for the registered matrix pair; the evidenced next step is
  difficulty re-derivation under a NEW registration. This token is
  NOT `MECHANISM_REJECTED` and licenses no in-lane edits — no
  retuning of prototypes, rule, or taxonomy inside this lane.
- Transient provider-invalid ledger (429/session-limit/zero-turn
  infra rows) → UNSCORED; relaunch ONLY on byte-identical digests,
  max 3 attempts, quieter window; a third transient failure →
  terminal `BAND_REANCHOR_UNSCORED` (answers neither PROCEED nor
  REJECT).
- Non-transient invalidity (schema/attestation/apparatus) → STOP and
  surface to the user; no blind retry.

**What PROCEED licenses (STAGE-LICENSE PRECISION)**: exactly one
fact — the frozen four-task, two-rep EQ4P anchor passes the
registered matrix-engine band gate, licensing a separately
registered successor. It does NOT establish corpus-level validity,
and — nested-screen caveat carried from `0102-*.md:325-328` — the
pilot floor `1/10` is weaker than the calibration floor `1/5`, so a
PROCEED at mean ∈ [1/10, 1/5) does not predict a 32-task calibration
PASS. Two reps support only this coarse floor/interior/ceiling gate;
no population-rate, stability, or engine-ordering inference is
claimed. Batches 01-08, sealing, calibration re-anchoring, and the
matrix are the successor registration's scope (0105 Sequencing items
4-8 are NOT inherited by silence); the mx-driver taxonomy corners
(success+empty-modelUsage f=1; no rc=124 censoring branch) remain
registered at that successor's matrix derivation.

## Pre-registered prediction

- **P-0107-1**: the frozen scorer returns PROCEED. Falsifier: any
  valid scored REJECT. (The earlier ordering prediction P-0107-2 was
  DELETED at R0 — EXPOSURE-MINIMALITY: it is unfalsifiable at the
  registered exposure and decision-free; the sealed verdict retains
  the data for any later user-ruled unsealing.)

## Information boundary

Carried in-kind from 0105: this registration is FROZEN before any
0107 row content or score is read; per-task outcomes stay SEALED
from corpus authoring; post-run exposure = one line
(PROCEED/REJECT/UNSCORED) + the decision-receipt digest. The sealed
0105 sonnet per-task outcomes remain sealed and are NOT an input to
this design or its apparatus (see the file-level derivation
prohibition above).

## Sequencing

1. Registration R0 (done, folded) → commit → R1 seat review → trio
   FREEZE.
2. Apparatus derivation: terra single-writer, digest-pinned brief
   (the six 0105 source files above ONLY), complete delta list +
   reversal proof vs the 0105 bases; trio freeze audit
   (`FREEZE-0107-PILOTLAUNCH-{SOL,GROK}`).
3. Launch: quiet account (operator rule, user-overridable as in
   0105), outside 23:00-01:00 KST, same-day sequential per-engine
   exact-ID smokes (`modelUsage == {claude-opus-5}` then
   `{claude-opus-4-8}`, pinned CLI, neutral dir), detached; 16 rows
   at 2 lanes ≈ 2× the 0105 pilot wall (~60-240 min; informational,
   never a license to tighten `BOUND_SEC`).
4. Read ONLY `DECISION` + `DECISION.receipt.sha256`; record verdict;
   successor registration is user-gated.

## Execution log

- **2026-08-22 — DRAFT + R0 folded.** Contested positions C1-C5
  staged; sol GO-WITH-EDITS (11 findings) + grok GO-WITH-EDITS (13
  findings). Convergent adoptions: C1 16-run fixed both-engine
  (BILATERAL DECISION SUFFICIENCY / PAIR-BAND USABILITY); scorer
  formulas mechanical + clause-isolated self-tests (CLAUSE-ISOLATED
  REACHABILITY / ANTI-INERTIA SELF-TESTS); delete `has_total_failure`
  + /10 gloss; delta lists frozen at registration incl. gate
  `ENGINE→ENGINES` + receipt (grok cited the 0103 precedent deltas);
  file-level sealed derivation boundary (SEALED CAUSAL ISOLATION /
  QUESTION-NOT-TREES); three-route verdict domain (VERDICT-DOMAIN
  CONSERVATION; `APPARATUS_INVALID` token declined — non-transient
  invalidity surfaces to the user, no new token without a learned
  failure); stage-license precision + nested-screen caveat
  (STAGE-LICENSE PRECISION / PILOT-LICENSE-NOT-MODULE); P-0107-1
  mechanical rewrite; both-floor tolerated with frozen asymmetry
  rationale (JOINT-IMPOSSIBILITY-FATAL / EASY-CONTROL-TOLERATED —
  sol's ban branch declined per grok: no learned failure); taxonomy
  fixture set per exact ID; two-rep disclaimer; Principles check +
  Mission-bound added; ordered tuple everywhere; token
  `BAND_REANCHOR_REJECTED` kept (TOKEN-MATCHES-QUESTION).
  **Fable-adjudicated splits**: schedule = sol's ABBA over grok's
  serial-per-engine (named criterion TIME-SYMMETRY; grok's quota
  argument dissolves — concurrency and total volume are identical
  under both schedules, and 0102 attempt-2 + 0103 attempt-1 ran the
  concurrent two-engine shape clean on this account); P-0107-2 =
  sol's deletion over grok's DECISION-line mean exposure (named
  criterion EXPOSURE-MINIMALITY; REJECT's successor is difficulty
  re-derivation — corpus-level means are exactly the tunable signal
  the boundary exists to withhold). Sol's receipt-bound
  quiet-account attestation declined: operator rule, user-overridable
  (2026-08-21 override produced zero anomalies), no learned failure
  to mechanize. R0 logs: `/tmp/r0-0107/{sol,grok}.log` → archived at
  `~/.local/share/nx01/iter0107/registration/`.
- **2026-08-22 — R1.** grok `FREEZE-0107-REG-GROK` (13/13 folded or
  declined-accepted; fold-defect scan clean; both adjudicated splits
  verified un-refuted with the named criteria). sol REVISE ×3, all
  fold-precision (no adjudication contested): ABBA formula frozen
  literally as `ENGINES[(i + rep + group) % 2]` + stale
  launcher/gate docstring-identity deltas enumerated; self-test
  vectors pinned to exact fractions (tests 2-6 completed; sol's
  arithmetic verified — the prior "else interior" glosses would have
  broken gate isolation); Principles check rewritten to the
  PRINCIPLES.md contract shape (pre-flight 0 first, #7 second,
  #1-#6 statused) + the decisive criterion added as its own
  section. R1 logs archived at
  `~/.local/share/nx01/iter0107/registration/`.
- **2026-08-22 — sol re-confirmation r1b.** Residuals 1-2 confirmed
  closed; residual 3 re-opened on contract shape (statuses missing on
  pre-flight 0/#7, bare ✅, merged #4/#5) → folded: every entry now
  carries `✅ Passes`, #4/#5 split. Second re-confirmation below.
- **2026-08-22 — sol r1c FREEZE-0107-REG-SOL.** Residual 3 closed
  (all eight entries `✅ Passes`, #4/#5 split, order verified against
  `PRINCIPLES.md:150`); no fold-introduced contradiction.
  **REGISTRATION TRIO-FROZEN** — grok FREEZE (r1) + sol FREEZE (r1c)
  + fable adjudication. Logs archived at
  `~/.local/share/nx01/iter0107/registration/` (r0/r1/r1b/r1c).
- **2026-08-22 — apparatus derived + TRIO-FROZEN.** Terra single-writer
  derivation (six digest-pinned 0105 sources only; reversal proof
  6/6; taxonomy fixtures 11 cases × both exact IDs; schedule digest
  `f3c08953…`; scorer relocated to repo byte-identical `74077f40…`,
  pin `docs/specs/iter0107-pilot/scripts.sha256`, commit e62bff5).
  Freeze audit r1: grok FREEZE (boundary inclusivity code-verified,
  docstring residue judged benign) / sol REVISE ×4. Fable
  adjudication: all four sol findings ADOPTED — lane scorer into gate
  FROZEN (MIRROR-PIN-CONSISTENCY), run-id grammar + strict HERE
  containment (INPUT-ENFORCED-CONFINEMENT), receipt-failure killpg
  (RECEIPT-BEFORE-EFFECT), driver docstring identity
  (FROZEN-IDENTITY-CONSISTENCY; grok's benign call overruled at
  near-zero cost inside the open fix round). Terra fix-round 1
  applied A1-A4; re-freeze: sol FREEZE (probes re-run, 29 gate
  categories) + grok FREEZE (static-only per new rule below).
  Final pins: driver `e531f1bf…` · launcher `225889a0…` · gate
  `cba26f9d…` · scorer `74077f40…` · copies byte-identical.
  **Operational notes**: grok's r1 audit accidentally spawned a real
  launcher from a throwaway probe copy (killed; live lane verified
  clean, digests intact, no attempt/lock artifacts) — grok probe
  rounds are now STATIC-ONLY by prompt rule. Launch is HELD at peer
  request: the pyx-memory-v1 session's X23 benchmark runs a no-retry
  50-call sonnet pass on this account (~1-1.5h; hold expires 3h) —
  its completion also gives us the quiet window. Audit receipts:
  `~/.local/share/nx01/iter0107/pilot/audit/`.
