# iter-0061 — F6 structural closure: AGENTS.md as the binding entry for Codex-CLI orchestration (+ stamping sentinel fix)

status: PRE-REGISTERED 2026-07-05 (predictions locked BEFORE any A/B run)

**Trigger**: HANDOFF Frontier C (2026-07-05). F6 mechanism established via
`iter0060-g2-pair` recon: codex-cli 0.141 has NO binding skill-invocation
semantics — skill content is advisory; the orchestrator model reads
`SKILL.md` via shell when it chooses to. F6's structural variables:
advisory discovery × invocation-framing strength. Compliance cells PASS
because their prompt is a strong framing (`run-compliance-cell.sh:113-116`:
"Follow the skill's full phase-gated pipeline… do not skip phases"); the F6
repro used an ORDINARY invocation (`codex exec -s workspace-write --json
"/devlyn:resolve …"`, iter-0040 Round 3 addendum) and the repro repo had NO
AGENTS.md. Binding-entry candidate: AGENTS.md — codex loads it
unconditionally, and `node bin/devlyn.js agents codex` already installs it
into real projects (`bin/devlyn.js:629-657`). AGENTS.md:39 already carries
the F6-targeting sentence (shipped iter-0059): "If you are Codex
orchestrating `/devlyn:resolve`, the phase machinery is mandatory regardless
of task size; if you will not run it, say so explicitly and stop — do not
silently degrade to ad-hoc execution."

## Why this iter exists (pre-flight 0)

User-visible failure being closed: a real Codex-CLI user in a
devlyn-installed project invokes `/devlyn:resolve` ordinarily and the
pipeline silently degrades to ad-hoc execution (F6, reproduced 2/2 in
iter-0040 R2+R3). Go/no-go this unlocks: whether the
"Codex CLI experimental as orchestrator" label in CLAUDE.md/AGENTS.md can be
narrowed to a measured condition (iter-0040 R3 pair criterion:
"ordinary-invocation non-skippability" passes mechanically), and whether F6
needs further structural work or is already closed for the shipped install
path.

## Hypothesis (falsifiable)

H-0061: with the devlyn AGENTS.md present in the project (the exact file the
installer ships), an ORDINARY `/devlyn:resolve` invocation through
`codex exec` no longer silently degrades to ad-hoc execution — it either
runs the phase-gated pipeline (mechanical compliance PASS) or explicitly
refuses and stops. Without AGENTS.md, the identical invocation reproduces
F6.

Falsifier (arm B): any arm-B rep that produces a non-empty ad-hoc code diff
with no `.devlyn/pipeline.state.json` (live or archived) and no explicit
refusal — that is F6 surviving the binding entry, and prose-in-AGENTS.md
joins prose-in-SKILL.md as pre-falsified (iter-0033g class).
Falsifier (arm A): if arm A stops reproducing F6, the baseline moved
(model/CLI drift) and the A/B is uninterpretable as designed — record, do
not reinterpret.

## Piece 0 (prerequisite) — stamping sentinel false-BLOCKED fix

**Observed defect** (iter-0040 R3 addendum, verified this session):
`stampInstalledSkillDir` (`bin/devlyn.js:351-370`) replaces ALL
`__DEVLYN_SKILL_DIR__` occurrences in every installed `.md`, including the
guard's comparison literal (`SKILL.md:35`,
`if [ "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__" ]`). A stamped install
that executes the `<runtime_paths>` block with `CLAUDE_SKILL_DIR` unset
(codex/omp always) compares the stamped default to the stamped literal —
equal — and false-positives `BLOCKED:shared-dir-unresolved`. Unexercised
until now only because codex never executed the block (F6 skip). Arm B's
entire purpose is to make codex execute that block, so the bug sits exactly
on this iter's critical path: it would convert a would-be hypothesis PASS
into an infrastructure FAIL (no state file → `state_found` FAIL).

**Fix** (the iter-0040 R3 designed shape): stamp ONLY the assignment-default
occurrence. In `stampInstalledSkillDir`, replace the exact pattern
`${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}` with
`${CLAUDE_SKILL_DIR:-<stamped path>}`; the sentinel comparison literal on
the guard line stays intact. Placeholder census (this session): the ONLY
occurrences across `config/skills/` are the assignment+guard line pairs in
`devlyn:resolve/SKILL.md:34-35`, `devlyn:ideate/SKILL.md:34-35`,
`devlyn:engines/SKILL.md:16-17`, `_shared/codex-config.md:12-13` — so
assignment-only replacement is total, no third shape exists.

**Post-fix semantics** (all three install paths):
- Claude native render: `CLAUDE_SKILL_DIR` set → unchanged.
- Stamped install (codex/omp): assignment default = real path ≠ sentinel →
  guard passes → correct.
- Raw `cp -R` (unstamped, e.g. compliance-cell sync): default stays
  placeholder → guard trips → honest BLOCKED — correct fail-closed.

**Mechanical verification** (before/after pair, recorded in Results):
`HOME=<tmp> node bin/devlyn.js agents codex` in a throwaway cwd; inspect
installed `devlyn:resolve/SKILL.md:34-35`. Before fix: BOTH lines stamped
(bug demonstrated). After fix: line 34 stamped, line 35 literal intact.

## A/B design

- **Repo shape** (per rep, fresh): throwaway git repo, `src/util.js` with
  one existing trivial function, NO package.json — the exact iter-0040 R3
  F6 repro shape.
- **Task literal** (fixed, all reps; reconstruction of the R3 shape — the
  original session-scratch literal was not preserved):
  `/devlyn:resolve "Add an add(a, b) function to src/util.js in the existing style, with a focused test."`
- **Invocation** (ORDINARY — no framing sentences):
  `codex exec -C "$WORK_DIR" -s workspace-write --json "<task literal>"`.
- **Global state** (constant across arms): real stamped install via
  `node bin/devlyn.js agents codex` + `agents omp` from a neutral setup dir
  AFTER piece 0 ships (covers both candidate skill dirs —
  `~/.codex/skills` and `~/.agents/skills` — loader precedence unresolved
  per iter-0046). `~/.codex/AGENTS.md` exists on this machine (personal
  instructions, 0 devlyn references — verified `grep -c devlyn` = 0);
  ambient constant for both arms, recorded not removed.
- **Arm A** (control): repo WITHOUT AGENTS.md. Expected: F6 reproduces.
- **Arm B** (treatment): identical repo + the packaged root `AGENTS.md`
  copied verbatim into the repo root before the baseline commit — exactly
  what `installInstructionsForCLI` writes on a missing file
  (`bin/devlyn.js:645-648`).
- **N and order** (R0 edit 1 adopted — iter-0058 flip-band rule is binding
  for A/B claims): 4 reps per arm, interleaved
  A1 → B1 → A2 → B2 → A3 → B3 → A4 → B4. No mid-matrix extension; the
  matrix is the matrix.
- **Abort criterion** (guardrail G5): a rep exceeding 30 min wall with no
  new file activity under the workdir is killed and recorded as timeout —
  not silently rerun.

### Outcome classifier (mechanical, exact precedence — R0 edits 3-6 adopted)

Evaluated top-down; first match wins; anything unmatched is UNCLASSIFIED
(openly adjudicated in R1, never silently binned):

1. **INFRA** — transcript contains the EXPANDED-PATH sentinel
   `BLOCKED:shared-dir-unresolved: /` (colon-space-slash = the guard's echo
   with a resolved absolute path). The unexpanded source forms
   (`…: $DEVLYN_SKILL_DIR/../_shared`, `…: $CODEX_MONITORED_PATH`) do NOT
   match — F6 runs dump the whole SKILL.md into the transcript via `sed`
   (iter-0040 R2/R3), so matching the bare sentinel would false-positive on
   file-dump content. Sentinel list is exactly this one entry; growth
   requires pre-registration.
2. **PIPELINE** — `check-compliance-cell.py --cli codex` overall PASS, AND
   (R0 edit 6, "avoid" option) if `verify_evidence.method` is
   `honest_blocked`, the rep's preserved `diff.patch` must be empty — the
   checker's own BLOCKED branch tests `workdir/diff.patch`, which no runner
   writes (`check-compliance-cell.py:127-131` vs
   `run-compliance-cell.sh:148`), so `diff_empty` is vacuously true there;
   the classifier enforces it against the real artifact. Checker gap logged
   as follow-up candidate, not patched mid-iteration.
3. **F6** — no `.devlyn/pipeline.state.json` (live or archived) AND
   non-empty `diff.patch`.
4. **HONEST-STOP** — no `.devlyn/` directory AND empty `diff.patch` AND the
   FINAL agent message in the `--json` event stream contains the
   case-sensitive substring `BLOCKED:` (the contract's own refusal
   vocabulary, AGENTS.md:39 / SKILL.md fail-closed forms). A polite prose
   refusal without that vocabulary lands UNCLASSIFIED by design.
5. **UNCLASSIFIED** — everything else, including partial machinery
   (`.devlyn/` exists but compliance FAIL) and crashed/empty transcripts.

The rep runner emits `outcome.json` per rep recording the class and which
rule fired; the runner script is preserved at
`benchmark/probes/results/iter0061-runner.sh` for provenance. Scoring
artifacts per rep (preserved under
`benchmark/probes/results/iter0061-<arm><n>/`): `transcript.txt`,
`diff.patch`, `compliance-check.json`, `timing.json`, `outcome.json`,
`devlyn-snapshot/` (when `.devlyn/` exists).

## Predictions (locked BEFORE the first run)

- **P1**: Arm A reproduces F6 in 4/4 reps (no `.devlyn/`, non-empty ad-hoc
  diff).
- **P2a** (R0 P2-split adopted): Arm B produces non-F6 outcomes in 4/4
  reps.
- **P2b**: Arm B's modal outcome is PIPELINE (compliance PASS), not
  HONEST-STOP — the execution claim, separate from the
  silent-degrade-closure claim.
- **P3**: With piece 0 shipped, no arm-B transcript contains a
  `BLOCKED:shared-dir-unresolved` false positive.
- **P4** (piece-0 guard): installed-file inspection shows assignment-line
  stamped + guard-literal intact for BOTH `~/.codex/skills` and
  `~/.agents/skills` installs; `bash scripts/lint-skills.sh` passes;
  `config/skills` ↔ `.claude/skills` mirror parity unchanged (piece 0
  touches only `bin/devlyn.js`, no skill-source edits).

## Decision tree (pre-agreed; ship rule per R0 edit 2)

- **Ship rule**: docs narrowing requires stable A = F6 4/4 AND
  B = non-F6 4/4 — a delta of 4/4, above any observed flip band by
  construction. Anything weaker (any flip in either arm) is reported as
  canary evidence only, no doc change.
- P1+P2a confirmed at 4/4 → F6 class is closed by the shipped install path
  (AGENTS.md is the binding entry). Ship: narrow the "Codex CLI
  experimental as orchestrator" sentence in CLAUDE.md engine-roles +
  AGENTS.md:39 to the measured condition (ordinary invocation +
  devlyn AGENTS.md present = phase-gated; minimal repos WITHOUT AGENTS.md
  remain the documented failure shape). DECISIONS entry; HANDOFF Frontier C
  closes.
- Arm B 4/4 HONEST-STOP → silent-degrade class closed but orchestration
  does not execute; label stays experimental with the refusal behavior
  documented; frontier stays open on execution.
- Arm B any F6 rep → H-0061 not shippable; if F6 is B's modal outcome,
  prose-in-AGENTS.md is falsified alongside prose-in-SKILL.md and the next
  candidate must be structural (e.g., wrapper entry point), NOT another
  prose strengthening round (anti-asymptotic, iter-0033g); a single B flip
  = canary-only report with the flip band recorded.
- Arm A any non-F6 rep → control instability; the 4/4 ship rule already
  fails; record raw results, report canary-only, re-diagnose before any
  ship.
- Any INFRA rep → stop the matrix, root-cause, re-run the affected rep
  only after the cause is fixed and documented.
- Any UNCLASSIFIED rep → adjudicated openly in R1 with the raw transcript
  quoted; never silently re-binned.

## Risk register

- R1: stamping fix regresses the omp install path — bounded by P4
  installed-file inspection; omp never verbatim-executed the block in any
  observed run (iter-0040 R3), and post-fix semantics table covers all
  three install paths.
- R2: codex loader precedence (`~/.codex/skills` vs `~/.agents/skills`,
  iter-0046 unresolved) selects a stale copy — mitigated by installing
  identical stamped content to both dirs before rep 1.
- R3: arm B engages the pipeline and spawns a pair judge needing network
  inside the workspace-write sandbox — VERIFY auto-pair is capability-gated
  (proceeds solo + reports skip, CLAUDE.md route-selection rule), and G1
  evidence (`iter0060-g1-codex`) shows the codex cell completing solo with
  `pair_judge: null`; predicted non-blocking.
- R4: single-session model nondeterminism — bounded by N=2 interleaved +
  the pre-registered extension rule, consistent with the iter-0058
  flip-band discipline.
- R5: the reconstructed task literal differs from the lost R3 original —
  both are trivial-add shapes; F6 was also reproduced on the F1 fixture
  task in iter-0040 R2, so the class is not literal-sensitive; recorded as
  a known limitation.

## Pair rounds

- **R0 adversarial** (Codex GPT-5.5 xhigh, read-only, own file:line
  citations; log `/tmp/codex-iter0061/r0-response.log`, 245s): verdict
  SHIP-WITH-EDITS; named decisive criterion adopted:
  **"Ordinary-Invocation Non-Skippability Above Flip-Band."** Falsifiers
  (a)(b)(c) did not fire; (d) fired against the as-written N=2 ship rule.
  All 6 edits adopted BEFORE any run: N=4/arm interleaved; 4/4-stable ship
  rule; exact-precedence classifier + UNCLASSIFIED bucket; HONEST-STOP
  fixed-substring test; INFRA single-sentinel list; diff_empty enforced
  classifier-side against the preserved `diff.patch` (checker gap at
  `check-compliance-cell.py:127-131` logged as follow-up, not patched
  mid-iteration). P2 split into P2a/P2b. One classifier trap found on my
  side while implementing edit 5 and folded into the design: the bare
  sentinel string appears in F6 transcripts as SKILL.md file-dump content,
  so INFRA matches only the expanded-path form.
- **R1 reconciliation**: (after raw results; below)

## Principles check

(to be completed at closure; pre-flight 0 answered above)

## Results

### Piece 0 — raw evidence (2026-07-05, recorded after each step)

- **Bug demonstrated BEFORE fix** (isolated `HOME`, real installer):
  installed `devlyn:resolve/SKILL.md:35` guard read
  `if [ "$DEVLYN_SKILL_DIR" = "<stamped absolute path>" ]` — i.e., the
  comparison literal was stamped; with `CLAUDE_SKILL_DIR` unset the guard
  compares the stamped default to itself → false-BLOCKED guaranteed on
  verbatim execution.
- **Fix shipped**: `bin/devlyn.js` `stampInstalledSkillDir` now replaces
  only `${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}` (assignment-default);
  guard literal untouched.
- **AFTER fix** (isolated `HOME` re-install): all 4 placeholder-bearing
  files (`devlyn:resolve/SKILL.md:34-35`, `devlyn:ideate/SKILL.md:34-35`,
  `devlyn:engines/SKILL.md:16-17`, `_shared/codex-config.md:12-13`) show
  assignment stamped + guard literal `__DEVLYN_SKILL_DIR__` intact; the
  only remaining placeholder occurrences in the installed tree are the 4
  guard lines.
- **P4 CONFIRMED**: real `node bin/devlyn.js agents codex` + `agents omp`
  installs → `~/.codex/skills/devlyn:resolve/SKILL.md:34` stamped
  `/Users/aipalm/.codex/skills/devlyn:resolve`,
  `~/.agents/skills/devlyn:resolve/SKILL.md:34` stamped
  `/Users/aipalm/.agents/skills/devlyn:resolve`, both guard literals
  intact; `bash scripts/lint-skills.sh` "All checks passed."; resolve /
  ideate / runtime-principles mirror parity clean (piece 0 touched only
  `bin/devlyn.js`).

### A/B matrix — raw results

Order as executed. Artifacts: `benchmark/probes/results/iter0061-<arm><n>/`.

| Rep | Outcome | Rule fired | Wall (s) |
|---|---|---|---|
| A1 | F6 | no pipeline.state.json AND non-empty diff.patch | 160 |
| B1 | PIPELINE | check-compliance-cell.py overall PASS | 901 |
| A2 | F6 | no pipeline.state.json AND non-empty diff.patch | 140 |
| B2 | PIPELINE | check-compliance-cell.py overall PASS | 1102 |
| A3 | F6 | no pipeline.state.json AND non-empty diff.patch | 80 |
| B3 | PIPELINE | check-compliance-cell.py overall PASS | 959 |
| A4 | F6 | no pipeline.state.json AND non-empty diff.patch | 160 |
| B4 | PIPELINE | check-compliance-cell.py overall PASS | 781 |

### Prediction outcomes (raw, matrix complete 2026-07-05)

- **P1 CONFIRMED**: Arm A = F6 4/4 (walls 160/140/80/160s; every rep:
  `state_found: false`, non-empty ad-hoc diff).
- **P2a CONFIRMED**: Arm B = non-F6 4/4.
- **P2b CONFIRMED**: Arm B = PIPELINE 4/4 (not merely non-F6; walls
  901/1102/959/781s; every rep all 4 mechanical assertions PASS; B1-B4
  archived states each show all 6 phases PASS, `engine: codex`,
  `sub_verdicts {mechanical: PASS, judge: PASS, pair_judge: null}`).
- **P3 CONFIRMED**: expanded-path sentinel
  `BLOCKED:shared-dir-unresolved: /` appears in 0 of 8 transcripts.
- **P4 CONFIRMED**: recorded in piece-0 results above.
- No INFRA, HONEST-STOP, UNCLASSIFIED, or watchdog rep anywhere in the
  matrix. Ship rule (A=F6 4/4 AND B=non-F6 4/4, delta 4/4 above any flip
  band by construction) FIRES.

B1 detail (first-ever ordinary-invocation codex pipeline pass): all 4
assertions PASS (`verify_evidence.method: sub_verdicts_with_artifacts`);
archived state `rs-20260705T005514Z-000001b329f1` shows all 6 phases PASS,
`engine: codex`, `sub_verdicts {mechanical: PASS, judge: PASS, pair_judge:
null}`, archive ran; no `BLOCKED:shared-dir-unresolved` anywhere in the
transcript (P3 holding).
