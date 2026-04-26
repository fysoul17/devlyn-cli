# 0006 — Foreground-only `codex exec` execution contract

**Status**: PROPOSED
**Started**: 2026-04-26
**Decided**: (not yet)

## Hypothesis

The iter-0005 full suite traced F2 (−82), F5 (−35), and F6's transcript-empty signature to a single behavioral pattern: the prompt-driven orchestrator non-deterministically chose to background `codex exec` (often piped to `tail -f` or wrapped in `Monitor`/`TaskOutput`), then issued Stop while that backgrounded subprocess was still running. The watchdog later killed the orphaned Codex + monitor pair, but no work product was captured. F4, F7, F8 — which used foreground `codex exec ... | tail -N` patterns — completed cleanly. Adding an explicit "foreground only" execution contract to `_shared/codex-config.md` and the inline auto-resolve default in `engine-routing.md` removes the orchestrator's choice between background and foreground; the only sanctioned shape is foreground. Predicted: F2 variant recovers (LocalShellTask kills → 0, transcript non-empty, margin ≥ +5), F5 follows, full suite returns to roughly the v3.7-final +10.6 region with the F7 win preserved.

## Mechanism

Why-chain (continues from iter 0005's full-suite refutation):

20. Why did iter 0005 fail full-suite even after fixing F7? → F2/F5 collapsed because Codex was backgrounded and never returned. F4/F9 also regressed on 0-kill / natural-exit runs, indicating the iter 0005 flags themselves shifted Codex behavior subtly (likely losing project-trust state).
21. Why does the orchestrator sometimes background Codex and sometimes not? → The orchestrator is a model interpreting a markdown skill file. Multiple `codex exec` examples exist in the codebase (some inline, some referenced); when the model improvises an invocation, it picks foreground or background based on local prompt context, recent tool-use patterns in the conversation, or simple sampling variance.
22. Why is background-with-tail unsafe specifically? → Background-with-tail introduces TWO long-running processes: the Codex subprocess and the `tail -f`/`Monitor` watcher. When the model issues Stop, the orchestrator's response ends but those background processes do not. macOS does not auto-reap them. The watchdog cleans them at metadata.timeout but no useful state was produced in the meantime.
23. Why is foreground-only the right level of fix? → It eliminates one bit of nondeterminism by removing a choice. The skill-prompt contract — read by the model at runtime — explicitly forbids the bad shape and prescribes the good one. No sandbox, flag, or process-group manipulation is required at the harness layer.
24. Why now and not iter 0005? → Iter 0005 reverted; we are choosing the next single hypothesis. Codex round 5 explicitly recommended `(a) foreground-only contract` over `(b) stream-json instrumentation` on the grounds that instrumentation makes failures observable but does not stop them.
25. Root: orchestrator pattern, not subprocess flags. Fix at level 25 — explicit skill-prompt contract that names the failure shape and the sanctioned shape.

## Predicted change

- F2 variant: LocalShellTask kills 2 → **0**, transcript ≥ 1 KB, diff_bytes ≥ 1 KB, score ≥ 85, margin ≥ +5.
- F5 variant: similar — LocalShellTask kills 1 → 0, score recovers, margin ≥ +5.
- F4 variant: no regression vs current iter-0005 state (already 0 kills); maybe small wall-time reduction.
- F7 variant: holds at margin +3-or-better (the iter-0005 win was independent of background pattern).
- F6 variant: LocalShellTask kills 1 → 0; the timed_out=false / invoke_exit=124 anomaly stops appearing (separate watchdog-classification fix is still warranted, but won't trigger as often).
- Suite avg margin: −7.1 → +10 region (return to v3.7-final ballpark, with F7 retained as a real win).
- Ship-gate: 2/8 → ≥7/9.

## Diff plan

Two surgical edits, no harness changes:

1. **`config/skills/_shared/codex-config.md`** — add a new section "Execution contract — foreground only" between the Notes block and the Availability check. The section names the failure shape (`&`, `tail -f`, `run_in_background`, `Monitor`/`TaskOutput`) and the sanctioned shape (single foreground, stream stdout, wait, capture). Includes a brief `Why this contract exists` paragraph pointing at iter 0005's full-suite evidence so future readers see the motivation.

2. **`config/skills/devlyn:auto-resolve/references/engine-routing.md`** — extend the "Codex call defaults" inline sentence with the same foreground-only constraint and a backreference to the canonical Execution contract section. This is the file the BUILD/FIX/etc. phases actually read at runtime; it must agree with `_shared`.

NOT in this diff:
- `--output-format=stream-json` instrumentation. Codex round 5 explicitly counter-recommended; instrumentation makes failures observable, not absent.
- Re-introducing iter 0005's three isolation flags. Those are on hold until a future measurement shows they are needed *separately* from the orchestrator fix.
- Inline `codex exec` mentions in `devlyn:ideate`, `devlyn:preflight`, `devlyn:team-resolve`, `devlyn:team-review`. None on the F2/F5 path; deferred to per-skill iterations as their own fixtures exercise them.

## Principles check (provisional, finalized after run)

| # | Principle | Status | Evidence |
|---|---|---|---|
| 1 | No overengineering | (provisional ✅) | Two text edits, ≈15 lines added. No new files, no harness changes, no flags. |
| 2 | No guesswork | ✅ | Hypothesis names the failure shape (background-with-tail), the metric (LocalShellTask kills = 0, margin ≥ +5 on F2), and the mechanism (orchestrator no longer chooses unsafe shape). Iter 0005's full-suite data already isolated the failure pattern. |
| 3 | No workaround | ✅ | The contract closes the orchestrator's degrees-of-freedom at the level the freedom exists (skill prompt). Not a sandbox flag, not a process-kill heuristic. |
| 4 | Worldclass production-ready | (filled after run) | |
| 5 | Best practice | (filled after run) | |

## Falsification gate

Before any full suite, gate sequentially:

1. **F2 alone** (~22 min). Pass criteria: `LocalShellTask kill requested` count = 0 in claude-debug.log; `diff_bytes > 0`; `files_changed > 0`; variant score ≥ 85; margin ≥ +5. Failure → re-diagnose with codex round 6 before any further runs.
2. **F5 alone** (~22 min). Same pass criteria as F2 but with F5's verify shape (4/5 expected since fixture's `node --test` passes). Failure → re-diagnose.
3. **Full suite** (~3-4 hr). Required for ship verdict per playbook.

## Actual change

(filled after F2 falsification + full suite)

## Lessons

(filled after run)

## Decision

(filled after run)
