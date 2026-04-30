---
iter: "0030"
title: "Shadow-suite v0 — 6 frozen tasks for bare-vs-L1 categorical reliability measurement"
status: ACTIVE — phase-A (infra + 1 task) ships first; phase-B (5 remaining tasks) ships after smoke
type: measurement infrastructure
shipped_commit: TBD
date: 2026-04-30
mission: 1
---

# iter-0030 — shadow-suite v0

## Why this iter exists (PRINCIPLES.md pre-flight 0)

User direction 2026-04-30 (logged in HANDOFF Block 4): real-project trial too expensive and not bare-comparable. Instead, generate small-but-tricky tasks inside the benchmark and measure bare-vs-L1 categorical reliability on them. Codex deep R0 verdict: do it as a **frozen shadow suite alongside the golden F1-F9** (option (c)), hybrid generation (LLM proposes → Codex/human curates → frozen). Sequencing: v0 (6 tasks) → v1 (18 tasks) → decision-grade (30 tasks).

The shadow suite is **measurement infrastructure**, not a quality gate. Per Codex's 8-condition trust rule: shadow can redirect work but cannot bless Mission 1 by itself. F1-F9 still controls release.

## Mission 1 service (PRINCIPLES.md #7)

Single-task L1 surface only. No Mission 2 substrate. Hard NOs untouched.

## Hypothesis

**Structural hypothesis**: A frozen shadow suite of 6 tasks (1 per failure class, mutations of F1-F9) discovered under `benchmark/auto-resolve/shadow-fixtures/` and gated by a `--suite shadow` flag will produce bare-vs-L1 DQ-rate readings on diverse failure classes — without contaminating golden F1-F9 ship-gate.

**Falsifiable predictions** (acceptance gate):
1. `benchmark/auto-resolve/shadow-fixtures/` exists with 6 task subdirectories (S1–S6), each containing the 6 fixture files per `benchmark/auto-resolve/fixtures/SCHEMA.md`.
2. `bash scripts/lint-skills.sh` passes.
3. `bash scripts/lint-shadow-fixtures.sh` (NEW) passes — schema validity + reference-solvability dry-run for all 6 tasks.
4. `bash benchmark/auto-resolve/scripts/run-suite.sh --suite shadow --dry-run` lists the 6 tasks without running models.
5. Golden F1-F9 unaffected: `bash benchmark/auto-resolve/scripts/run-suite.sh F1 --dry-run` still works.

## Failure-class coverage (6 tasks per Codex R0)

| ID | Failure class | Mutation source | Trap shape |
|---|---|---|---|
| S1 | spec-compliance (precise output literal) | F1-cli-trivial-flag | spec asks for `--lang <code>` flag with localized greeting; trap = subtle output-format requirement (newline / quote shape) |
| S2 | multi-file scope leak | F7-out-of-scope-trap | bait in `lib/` and `server/`; spec only allows touching `bin/cli.js` + `tests/cli.test.js` |
| S3 | build-gate runtime (failing test → fix) | F5-fix-loop-red-green | pre-existing failing test for an off-by-one bug; spec asks for fix + new edge case test |
| S4 | security CRITICAL (dep audit) | F6-dep-audit-native-module | spec asks to add a feature that tempts adding a vulnerable dep; expected behavior = use built-in instead |
| S5 | silent-catch | F2-cli-medium-subcommand | spec asks for a `health` subcommand with EACCES-distinct error reporting; silent-catch trap |
| S6 | scope leak (single-bait, non-file) | F4-web-browser-design (re-shaped) | spec asks for new flag; bait = nearby refactor opportunity that's explicitly out-of-scope |

## Scope (phase-split for safe ship)

**Phase A (this commit)**:
- `benchmark/auto-resolve/shadow-fixtures/` directory + `README.md` describing the suite.
- **S1 task** as a worked example (all 6 files: `metadata.json`, `spec.md`, `task.txt`, `expected.json`, `setup.sh`, `NOTES.md`).
- `--suite shadow` flag in `run-suite.sh` (auto-discover from shadow-fixtures/ instead of fixtures/).
- `scripts/lint-shadow-fixtures.sh` — schema validity check for all shadow tasks.
- iter-0030 file with phase-A→B split documented.

**Phase B (next commit, after phase-A smoke verifies)**:
- S2-S6 tasks (5 fixtures × 6 files = 30 files).
- Reference-solvability dry-run for each.
- Final smoke: `--suite shadow --dry-run` lists all 6.
- iter file → SHIPPED.

This split is per **CLAUDE.md "Goal-locked execution"**: ship the smallest reversible unit that proves the mechanism works (S1 + suite flag + lint), then expand. If phase-A smoke surfaces a problem (e.g. `--suite shadow` flag conflicts with auto-discovery), we revert Phase A only and replan — not 30 files of failed work.

## Acceptance gate (pre-registered)

**Phase A acceptance**:
1. iter-0030 file exists at `autoresearch/iterations/0030-shadow-suite-v0.md`.
2. `benchmark/auto-resolve/shadow-fixtures/S1-cli-lang-flag/` contains all 6 fixture files.
3. `bash scripts/lint-shadow-fixtures.sh` exit 0.
4. `bash benchmark/auto-resolve/scripts/run-suite.sh --suite shadow --dry-run` exit 0 AND lists S1.
5. `bash benchmark/auto-resolve/scripts/run-suite.sh F1 --dry-run` still exit 0 (golden suite unaffected).

**Phase B acceptance** (deferred to next commit):
1. All 6 shadow tasks present.
2. Each task's `verification_commands` runs against a hand-written reference solution and passes (reference-solvability).
3. `--suite shadow --dry-run` lists all 6.
4. iter file → SHIPPED with commit SHA bake.

## Codex pair-review

R0 verdict from earlier session (`019dde77`, 2026-04-30): shadow-suite design verified — frozen 6-task v0, separate `--suite shadow` flag, location outside `fixtures/F*` to avoid muddying ship-gate. Phase split was added during execution per Goal-locked-execution rule (smallest reversible commit ships first).

R-final triggered only if phase-A smoke fails OR if a shadow task surfaces a hidden trap during phase-B authoring.
