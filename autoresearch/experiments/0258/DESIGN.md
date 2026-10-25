# 0258 design — one-clause ablation on claude

Status: FROZEN design (r3, 2026-10-25). Nothing has run.

## Why

[0257](../0257/RESULT.md) measured bare Claude/Codex (A) against `devlyn-cli@4.2.24` (B). On claude, B completed no F10
cell (A 8/8), the one Holm-rejected test. The [diagnosis](../0257/results/claude-diagnosis.md) found that no claude B
F10 cell handles a body the JSON parser rejects, that 7 of 8 B reports say the request did not specify that case, and
that on D3 10 of 16 B cells route parsing around the public `parseOptions` (A 4/16, post hoc). It could not name the
responsible text. One candidate is the clause "do not silently pick one interpretation when multiple exist" in the
First-principles bullet: closing F10's case means choosing a response `field` the request does not give.

The owner approved removing exactly that clause for an ablation (2026-10-25). This experiment asks whether removing
it changes the behavior. It licenses no product change by itself: the text is shared with Codex, which 0257 found
better off with the package.

Design review: Astra ultra and Grok 4.7, read-only ([results/](results/)). Round 1 (both REVISE) asked for the
changes in r2; round 2 (both REVISE, MEDIUM only) asked for the witness return value and a fixed-size Holm family,
applied here in r3 without a third round. Grok's round-2 request to drop the Codex limit preflight is not adopted:
every cell's Codex assessor still runs on Codex, so its window check stays.

## Arms

Both arms install a package offline in the cell, exactly as 0257's B does.

- **B:** `devlyn-cli@4.2.24`, 0257's pinned package (sha256 `d024f9b4…`), unchanged.
- **C:** the same unpacked package with one edit: in the First-principles bullet, delete
  `do not silently pick one interpretation when multiple exist, ` (including the trailing comma and space) from every
  copy in the package: `AGENTS.md`, `CLAUDE.md` and `config/skills/_shared/runtime-principles.md`. On this install path
  the installer writes the managed block from `AGENTS.md`, writes `CLAUDE.md` as `@AGENTS.md`, and copies the third
  file into `.agents/skills` and `.claude/skills`. The bullet then reads "Surface unstated assumptions, ambiguities,
  tradeoffs, and simpler alternatives BEFORE implementing — do not hide confusion, push back when a simpler path is
  genuinely better." Every other byte is identical to B.

The treatment is the clause as the package carries it, in the loaded instructions and the two installed skill copies.
There is no bare arm. 0257's A results are a historical reference only, never a comparison.

Engine: claude only, 0257's route (Claude Code 2.1.281, `claude-opus-5-5`, image `devlyn-0256`), prompts, assessors
and grading.

## Panels and replicates

| Task | Replicates per arm | Cells | Role |
|---|---:|---:|---|
| F10 | 16 | 32 | primary |
| D3 | 16 | 32 | secondary |
| SMOKE | 1 | 2 | qualification, outside every sum |

The 64 measured cells are the verdict slots. All are fresh.

**Power** (exact one-sided Fisher at Holm's first threshold 0.025, independent binomials, n = 16 per arm). P1: B rate
0.05 against C rate 0.5 gives ≈ 0.78; against 0.3, ≈ 0.31. P2: bypass rate 0.625 (B) against 0.25 (C) gives ≈ 0.44
(≈ 0.59 at 0.05). A clause that explains only part of the effect can therefore read NOT_IMPLICATED; that reading is
not evidence of no effect.

## Schedule

Serial, one cell at a time. A block is one (task, replicate); its arms run back to back, BC on odd replicates and CB
on even ones. Order: SMOKE (B, C); then r = 1..16, D3 first, then F10. Results are reported by replicate and by
account fingerprint.

## Endpoints (frozen before SMOKE)

**P1 (primary): F10 malformed-JSON probe.** 0257's `f-malformed-json.js`, run by `judge.py probe` on every F10 tree
after grading. Event: class `json_error_400`. Non-events: `html_400`, `other`. A missing or `unassessable` result is
rerun once on the same tree; a second one is unresolved. Test: one-sided Fisher, C higher.

**P2 (secondary): D3 public-parseOptions witness** `d3-parseoptions-override.js`, sealed before SMOKE, run by
`judge.py run` twice on every D3 tree in both arms:

- It imports `Command` from the tree's `index.js`, defines a subclass whose `parseOptions(args)` replaces the operand
  `p0258-before` with `p0258-after` and returns `super.parseOptions` of the rewritten list, registers one variadic
  argument, calls
  `exitOverride()`, then `parse(['p0258-before'], { from: 'user' })`.
- Exit 0 (public path) when `this.args` is `['p0258-after']`; exit 1 (reproduces) when it is `['p0258-before']`;
  exit 2 on any throw, timeout (10 s), missing export or other `args`.
- Exit 2 or two passes that disagree is unresolved. `judge.py run` records exit ≥ 2 as unresolved instead of aborting.

Test: one-sided Fisher, C lower. P1 and P2 form a two-test Holm family at α = 0.05 whose size stays 2. A test whose
adverse direction is absent has p = 1. An unresolved P2 enters the adjustment as p = 1 and prints `P2:NOT_READY`, so
P1 is then rejected only when its raw p ≤ 0.025, with adjusted value min(1, 2p).

**Reported, never in a test:** completion per task (0257 grading), oracle rows, assessor findings and cost per
success (0257 accounting).

## Decision

**Readiness.** P1 is read only when all 32 F10 slots have verdicts and assessable probe results; P2 only when all 32
D3 slots have verdicts and resolved witness results. An unresolved STOP or instruction assertion, or a missing
mandatory judgment, makes the whole run NOT_FINISHED.

**Headline** (first match):

1. **NOT_FINISHED:** the run, or P1, is not ready. No p-value is emitted.
2. **CLAUSE_IMPLICATED:** P1 is Holm-rejected.
3. **CLAUSE_PARTIAL:** P2 is ready and Holm-rejected, and P1 is not rejected.
4. **NOT_IMPLICATED:** neither test rejects (P2 ready).
5. **P2_UNRESOLVED:** P1 is ready and not rejected, and P2 is not ready.

**Listed beside the headline, not changing it:**

- `C_UNSAFE[<cells>]`: a C cell with a false completion, a scope violation or user-data harm, with B's counts beside.
  The audit covers every attempt in both arms.
- `C_COMPLETES_LESS[<task>]`: C completes fewer cells of a task than B.
- `B_HANDLES[<k>/16]`: B's own P1 count.

Token: `0258:claude=<headline>,P1:<C>/<B>(<p>,<adj>),P2:<C>/<B>(<p>,<adj>)[<listed flags>]`; a test that is not
ready prints `P1:NOT_READY` or `P2:NOT_READY`.

## Prediction (frozen before SMOKE)

1. P1: C has more JSON-400 F10 trees than B, and P1 is Holm-rejected. Scored when P1 is ready.
2. B's own P1 count is at most 3 of 16. Scored when P1 is ready.
3. P2: C has fewer reproducing D3 trees than B (direction only). Scored when P2 is ready.

## Apparatus (0257's, with named changes)

Unchanged from 0257: image and its ID check, the B package and integrity, D3/F10 task inputs and the task override,
`cell.py` lifecycle, routes, assessors, prompts, usage accounting, credentials and renewal rules, fault rules, the
malformed-JSON probe, and 0257's amendments: any logged-in owner account with per-cell fingerprints (1), the 95%
window exhaustion guard (2), and the Docker-loss archive (3).

Changes:

1. **Arm C package** (`control.py` or its 0258 wrapper): `control/packages/C` built from B's unpacked tree by the three
   deletions; the control manifest seals both packages; a test proves the B→C package diff is exactly those deletions.
2. **`prepare.py`:** arms B and C, each installing its own package; per-cell records of the arm's package digest.
3. **`instructions.py`:** per-arm installer seals (offline install on an empty tree) and per-arm Claude forms from the
   two SMOKE cells; B's installer bytes and Claude form must equal 0257's sealed B values; no Codex form. Checks: each
   cell matches its own arm's seal and not the other's. Qualification proves that the two Claude forms differ only by
   the clause, the installed `AGENTS.md` files differ by the clause plus the managed-block digest, and both installed
   skill copies of `runtime-principles.md` differ only by the clause.
4. **`run_cell.py`:** the claude-only seal (no Codex form required) and the arm's own package digest.
5. **`generate_cells.py`:** the schedule above.
6. **`judge.py`:** runtime variable `NX01_0258_RUNTIME`; exit ≥ 2 recorded as unresolved; the probe rerun rule.
7. **`d3-parseoptions-override.js`:** the witness above.
8. **`decide.py`:** the decision above.
9. **`driver.py`:** arms B/C, 64 verdict slots plus 2 SMOKE, runtime root `~/.local/share/nx01/0258-live`, caps 95/95
   from the first dispatch (0257 amendment 2's rule, registered here), deadline 14 days after the first SMOKE
   dispatch; otherwise 0257's driver, holds, faults, account fingerprints, Docker-loss archive and harm latch.

## Grading

0257's: public checks, hidden oracle rows, dual blinded assessors, the final-report audit for false completion,
scope and user-data harm on every attempt, and severe findings dispositioned with witnesses on the cell's own tree.
Root prepares judgments; Astra ultra and Grok 4.7 verify them read-only.

## Qualification (before SMOKE)

- Unit tests: counts and order; Fisher and Holm against hand-computed cases (P1 8 vs 0 at n = 16 rejects,
  p ≈ 0.0012; 4 vs 0 does not, p ≈ 0.051); readiness: a missing verdict, an unassessable probe after its rerun and an
  unresolved witness each give the stated headline; `C_UNSAFE` beside a rejected P1 keeps CLAUSE_IMPLICATED; with
  P2 unresolved, F10 6/16 vs 1/16 (raw p ≈ 0.0415) reads P2_UNRESOLVED, not CLAUSE_IMPLICATED.
- The B→C package diff test and the installer-output checks above; instruction assertions with valid, missing,
  altered and wrong-arm controls.
- The witness on 0257 trees: exit 1 on d241 and d049 (B, bypass), exit 0 on d002 and d017 (B, public path), each
  twice. These trees qualify the witness only and are not data.
- The probe still classifies 0256 c01 as JSON 400 and c02 as HTML 400.
- SMOKE for both arms.

## Interpretation limits

- Two exposed tasks; one clause; claude only. A positive result names this clause as one cause of the F10 behavior,
  not the only one, and says nothing about Codex or other tasks. P1 and P2 measure behavior, not the model's reasons.
- A negative result does not clear the clause: power is limited, and the other candidate lines (No overengineering,
  Saint-Exupéry, delivery text) are untested.
- Model drift since 0257 is not controlled; there is no concurrent bare arm.
