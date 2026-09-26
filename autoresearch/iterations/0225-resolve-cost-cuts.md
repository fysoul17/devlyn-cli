# 0225 — cut full resolve's own time and tokens

2026-09-27. **Status: REGISTERED, frozen before implementation.** Design converged between root (Opus 5.5) and Astra (gpt-6-astra, ultra, read-only): independent R0s, then R1 `CONVERGED`. Registration review: R0 REVISE (8, all adopted) → R1 REVISE (2, adopted) → R2 FREEZE. The raw record is in `.devlyn/0221/s9-diag/` (diagnosis R0s, four per-cell cost ledgers, three cut designs, merge, Astra cost R0/R1).

## Why

The user's priority (2026-09-27): "resolve의 불필요한 과도한 시간과 토큰을 잡아먹는게 문제인데 … 그게 가장 우선인거 같아", and "모두 astra ultra와 함께 깊게 고민하고 best practice 로 수정해". [0221](0221-subtraction-direction.md) closed without a replacement, so full resolve's cost is unchanged. In 0224, published 3.2.1 (F) spent ≈3× native's wall and ≥3–9× its OUTPUT and completed 0/4 cells ([RESULT](../experiments/0224/RESULT.md) table).

## What the evidence says

- **Stops.** Every F product misses at least one real requirement, so each BLOCKED is a correct outcome:
  - D4-claude: a test reader thread cannot be terminated.
  - D4-codex: timeout cleanup leaves FIFO/symlink fixtures behind. It also stopped earlier, because the image lacked the project's declared type checkers.
  - Both I0185 cells: release-recovery and terminal-alias defects.

  In one cell the stop *reason* was wrong. In I0185-codex, the round-0 lock-release HIGH was repaired; then the round-1 judge hashed the wrong contract file, and that false CRITICAL triggered the two-strike halt.
- **Resolve defects on main `62eb2d98`:**
  1. The owner hand-builds the VERIFY packet (`verify.md:10,13`; `SKILL.md:302-303`), so a packet can name the wrong contract or forbid commands.
  2. "Second `NEEDS_WORK`" (`SKILL.md:337`) contradicts `SKILL.md:23` and `state-schema.md:125`. No script enforces `max_rounds`; the owner hand-edits `rounds.global`.
  3. A missing tool becomes a HIGH product finding and halts the run before VERIFY (`build-gate.md:51` vs `:64`; `SKILL.md:285`). The engines handled this differently.
  4. VERIFY missed the real I0185 release and terminal-alias defects in both configs.
  5. A relative `--devlyn-dir` falsely BLOCKs Claude judges, because `judge-role-evidence.py:103` compares an unresolved path.
- **Where F's cost goes** (phase intervals, which overlap; these are not additive savings):
  - Owner main-thread work in D4-claude: 607.8 of 1277.7 s, 52.8k output (5× native's whole run) and 14.6M cache-read. This includes useful reasoning.
  - VERIFY owner work: 235.6 s, plus 81.5 s of "parallel" judges that ran serially (over three rounds).
  - D4-codex polling: 474,798 input tokens.
  - BUILD_GATE/CLEANUP rounds found nothing in 7 of 7 cases. SURFACE_CLOSE produced two docstrings.
  - The reviews did buy real repairs: bounded waits in D4, and stranded-lock handling and marker rollback in I0185. Useful repairs are not waste.

## Plan (one PR per step, in order)

1. **Contracts:**
   - delete the competing VERIFY stop rule so `max_rounds` is the only budget, with the published default staying 4;
   - make a script own the repair counter, with atomic admission;
   - resolve the path at `judge-role-evidence.py:103`.
   Static checks: relative and absolute paths agree, a wrong path is rejected, exhausted and shared budgets hold, duplicate admission is refused, and terminal `NEEDS_WORK` is kept apart from infra `BLOCKED`.
2. **Scripted VERIFY:**
   - delete the owner-authored packets, the wording-triggered no-tools route (`adapters/codex.md:17`), the judge-side re-hash, the orchestration prose inside judge prompts, and pair-reason completeness (telemetry only, `verify.md:134`);
   - the existing renderer derives the authoritative inputs;
   - one foreground supervisor starts both judges as children, and one call collects, validates and merges;
   - no owner "focus" slot.
   Static checks: transport tampering, missing inputs, timeout distinctions, concurrent stub starts, child failures.
3. **One final mechanical gate:**
   - delete the duplicate BUILD_GATE/CLEANUP execution and the SURFACE_CLOSE worker, moving doc upkeep into IMPLEMENT;
   - keep the language, browser, literal and probe checks, and scope/untracked enforcement after artifact cleanup, behind one cheap final source/index/untracked seal that any changed input invalidates;
   - commands the spec, repo or CI require stay binding. A tool proven absent whose supply is prohibited gives an infra `BLOCKED`, and only a genuinely optional inferred check may skip, visibly.
   Negative fixtures cover every moved guarantee, including a required-tool failure.
4. **Fewer owner turns:**
   - delete API-discovery reads, hand-written deterministic state edits, routine polling and repeated report composition;
   - expose the exact supported commands, and render one report that serves both the final message and the archive;
   - load probe text only when probes are enabled (including automatic selection).

   Static checks: bootstrap/state parity, report/verdict agreement, archive integrity and conditional loading.
5. **Contract-first PLAN:** delete copied acceptance sections and competing restatements, and pass the canonical contract bytes. Keep the scope binding, the needed risk/boundary decisions and the conditional gates.
   - Add executable witnesses for defect 4: release recovery, physical aliases, fixture cleanup, temporary-file preservation.

   Static checks: source identity, immutable scope and gate preservation.
6. **Claude inline IMPLEMENT:** a separate arm, landed only after its own comparison. Delegation stays whenever roles or identities differ or cannot be verified, and exact role/model/effort matching is enforced.

   Static checks: role/effort matching, scope and evidence requirements.

**Kept:**
- fresh cross-engine judges with the pair on by default;
- review → reproduce → repair → fresh review;
- bounded execution and fail-closed explicit routes;
- the red-first bar, sealed evidence and the worst-verdict merge;
- scoped staging, branch ownership and archive integrity.

**Defect mapping:**
- Defects 2 and 5 are fixed in step 1, defect 1 in step 2 and defect 3 in step 3.
- Defect 4 gets the step-5 executable witnesses. Removing prompt text alone does not count as fixing recall.

## Confirmation (registered before any run)

### Static

Repository lint and self-tests, plus each step's negative fixtures.

### Replay (after step 2)

Render packets for the 7 archived VERIFY rounds and run both judges (14 calls). The replay passes only if:

- the five binding HIGHs are retained:
  - s6-04 r1: unbounded writer-readiness wait;
  - s6-04 r2: a reader thread survives cleanup;
  - s6-16 r0: the published install marker is not rolled back;
  - s6-16 r1: a preexisting temporary file is deleted after `EEXIST`. This preservation failure is distinct from the r0 marker failure;
  - s6-07 r0: one failed lock removal strands the lock;
- 0 input `BLOCKED`s;
- the two judges' runs overlap in time;
- artifact integrity is unchanged.

If the replay fails, the failure is recorded, step 2 may be revised once, and the replay is repeated on the same 7 rounds. After a second failure, steps 2–5 are held as a bundle, no live comparison of the cuts runs, and only step 1 can ship.

### Live

Live runs start only after the user approves invoking resolve (0201 rule 5 still holds). Approving comparison runs is not merge approval.

- **Arms.** The control is the step-1 build: published behavior plus the budget and path fixes, still carrying defects 1 and 3. The candidate is steps 1–5. The comparison therefore measures the combined effect of the defect fixes and the cuts, and no saving is attributed to a single step.
- **Runs.** {D4, I0185} × {claude, codex} × {control, candidate} = 8 runs, n=1 each. On top of these, 2 Claude step-6 runs are compared against the candidate.
- **Dispatch order (frozen):**
  1. D4-claude-control
  2. D4-claude-candidate
  3. I0185-codex-candidate
  4. I0185-codex-control
  5. I0185-claude-control
  6. I0185-claude-candidate
  7. D4-codex-candidate
  8. D4-codex-control
  9. D4-claude-inline
  10. I0185-claude-inline
- **Setup.** Provisioning is identical, with the project's declared type checkers present. Every run is pinned to `--max-rounds 2`.
- **Faults.** The apparatus, stop rows and affected-bundle re-dispatch follow 0222 and [0224 "Before any rule is computed"](../experiments/0224/DESIGN.md) items 1–3. A fix that changes only grading means re-grading, never re-running.
- **Usage.** A step-2 candidate records both judges' usage. Missing usage is UNKNOWN, and a PARTIAL total is a lower bound.

### Adoption, per config k

A task pair is eligible only if all of these hold:

1. no false completion and no scope violation;
2. the candidate's completion is no worse than the control's;
3. the candidate passes every public check and oracle row the control passes;
4. the candidate has no reproduced HIGH/CRITICAL that the control lacks;
5. the candidate completed the mandatory obligations. That means the final mechanical gate on the final source and the final review (both judges when available), and a terminal verdict derived from them. This obligation list, not phase order, decides eligibility.

An ineligible pair blocks adoption in k; it is never dropped from the two-task totals.

With both pairs eligible, the candidate is adopted in k if either test passes:

- **Wall:** summed wall ≤ 0.85 × the control's, and OUTPUT ≤ 1.10 × the control's.
- **OUTPUT:** summed OUTPUT ≤ 0.75 × the control's.

Every OUTPUT inequality must be proved by valid bounds: the candidate's usage must be COMPLETE, and it is compared against the control's lower bound. Otherwise the result is INCONCLUSIVE, which means not adopted.

### Release

- Step 1 ships on its own static checks, as a correctness fix with no saving claimed.
- Steps 2–5 ship as a bundle only if the candidate is adopted in both configs. A rejection, or configs that disagree, holds the bundle; attributing the failure to a single step needs a new registration.
- Step 6 ships only if the steps 2–5 bundle is adopted in both configs and, on both Claude tasks against the candidate, eligibility rules 1–5 hold, summed wall ≤ 0.9× the candidate's, and the role/model/effort match is verified.
- Delivery is push + PR. Merging needs the user's authorization, and npm publish stays with the user.

## Predictions (before implementation)

A ratio is the candidate's two-task sum over the control's, per config.

1. Static checks pass. The replay passes, with 0 input `BLOCKED`s and all five binding HIGHs retained.
2. The wall ratio falls in [0.55, 0.65] for claude and [0.65, 0.75] for codex. These are targets, not established savings; a ratio outside its interval falsifies the prediction.
3. The candidate loses no public check or oracle row. I0185 stays incomplete in both arms, because the cuts do not fix recall.
4. With COMPLETE candidate usage, the percentage OUTPUT reduction exceeds the percentage wall reduction in each config.
