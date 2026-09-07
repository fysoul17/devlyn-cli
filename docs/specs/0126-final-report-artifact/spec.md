# Persist the final report before completing its phase

## Goal and observed failure

Ordinary0123 explicit r2 (`rs-20260907T112121Z-b3d4b6fa6bae`, sourcea7a1f01) marks final_report complete and archives at11:52:10.749Z, then emits the report only as final assistant text at11:52:58.879Z. `phases.final_report.artifacts.log_file` is null and the74-file archive contains no final report. The required render→complete→archive order in `devlyn:resolve/SKILL.md` PHASE6 was not followed, as in the earlier0120 R4 closure failure. Preserve those original results.

The current archive already owns `final-report.md`; reuse that artifact and the existing state writer's `--log-file` surface. Make report persistence an explicit executable prerequisite of final-report completion, without a new reporter, dispatcher, engine route, flag or output-format experiment.

## Requirements

1. The installed resolve contract writes the required report sections to `.devlyn/final-report.md` before final_report completion and binds it through the existing state writer. User-facing text may follow archive, but cannot substitute for this retained artifact.
2. The current writer rejects missing, empty or unsafe report input before final_report completion, with a clear failure and without marking the phase completed or erasing prior verdict/evidence. Require the canonical nonsymlink regular file through `--log-file`, with exactly one first-line identity marker `<!-- devlyn:final-report run_id=<current run_id> -->` and a non-whitespace report body. This prevents another run's report from satisfying completion; it does not validate report semantics. Reuse `artifacts.log_file` and `output_sha256` to bind the completed bytes, without an mtime heuristic or new report serializer.
3. Preserve terminal verdict derivation, finish-gate precedence and report→complete→archive sequencing. Keep existing role/model evidence, engine dispatch, phase graph, canonical parser and review floors unchanged. Do not invent a worker invocation or substitute another phase/engine to bypass attestation.
4. Preserve0121's BLOCKED missing-PLAN-output closure path: the orchestrator can create a truthful BLOCKED report without PLAN output and then complete/archive normally. The missing report is not a missing plan and must not reopen IMPLEMENT or change the original failure into success.
5. Retain exactly one canonical runtime implementation and normal mirrors. Existing archive ownership includes the report; add only the preflight needed to rehash a present final-report binding before any move. Missing or altered bound reports and present malformed/null digests must fail without partial archive/state mutation. Historical completed states with the digest field absent keep their existing archival behavior; do not rewrite historical archives.

## Scope and verification

Smallest expected scope: `_shared/state-phase-write.py`, `devlyn:resolve/SKILL.md`, its state-schema reference, exact mirrors and existing required lint/self-test coverage. No customer AGENTS/CLAUDE research paragraphs, serializer helper, general timeout change, model default or benchmark mutation.

Before editing, predict the real red/green outcome. Exercise actual state-writer CLI completion with missing/empty/unsafe/stale report cases, valid matching report completion/archive, and the existing BLOCKED missing-PLAN-output path; preserve raw results. Assert failed completion does not advance lifecycle. Run required full skill lint once after the final source change. Independently review the final diff, then use a fresh packed ordinary unconfigured README task with the0123 clarification. The old r2 remains canonical PASS_WITH_ISSUES but unaccepted; no manual report insertion, phase rescue or success relabeling.
