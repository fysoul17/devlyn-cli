# Prospective consultation: dependent-child lifetime before pair

You are independently advising devlyn-cli's owner. This is a design decision, not implementation authorization. Recommend **no change** if that is the best-supported answer. Do not assume a new instruction will improve behavior.

## Decision and constraints

The user's priority is: establish a minimal, efficient solo harness first; consider automatic pair only for residual failures; defer ideate work. The North Star is hands-free, engineer-quality delivery across capable engines. Compare wall/input/output per correctly delivered task, charging every failed attempt and child; quality must not regress. Zero successes gives no finite per-success cost. A lower cost with unfinished delivery is not success.

Should the observations below license one additional minimal solo hypothesis before the proposed 0238 pair study, or should solo remain unchanged? If another hypothesis is justified, what is the smallest decisive validation that distinguishes it from another generic “finish properly” sentence?

The existing CF confirmation block and all registered inputs/criteria remain fixed. Do not infer an arm effect from its partial results, rescue/regrade f02, select a baseline from unfinished comparisons, or claim gain over bare. 0238 pair is prospective, not admitted. Preserve authentication/account checks and the registered outer watchdog. Any proposed native execution setting is a separate prospective contract, not a rescue of this cell; justify its scope against the instruction-first priority. No configuration bypass, new orchestration framework, or mandatory-review expansion is requested.

## Established observations

- Finished `f02-CF-CONFIG-claude-C-r1-auth1` used Claude Code **2.1.296**, `claude -p`, Opus 5.5/max. All 12 source-oracle rows and 22 public tests passed, but delivery was incomplete: changed files were never committed. Exit 0, identity MATCH, usage COMPLETE. This is one trace, not evidence that C caused the failure.
- The owner **read the complete** installed `task-completion.md` and `runtime-principles.md` with `cat` early in the run (`run/stdout:10–11`; complete combined output, 17,853 characters). Completion guidance explicitly says to finish the whole request, that messages/conversation end are not delivery boundaries (`task-completion.md:3–9`), and **“Wait for your children, stop your dev servers and task writers, then leave the task tree”** (`:170–172`). That last instruction introduces delivery cleanup and writer attestation. Missing/truncated guide loading does not explain this trace.
- The owner chose an independent, read-only native `Agent` review, explicitly **`run_in_background: true`** (`stdout:1189`). This was native delegation, not an independent peer CLI. The launch result promised a later completion notification and permitted other work or a response meanwhile. The owner then ended its turn saying it would allocate and commit after the review returned (`:1408`). The review therefore became a completion dependency.
- The reviewer continued working, then was system-killed **600.134 seconds after** the owner's final response. `run/stderr:1` explicitly names **`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`**: background tasks still running ten minutes after the last turn were stopped. This was the native post-final-turn wait ceiling, **not** the experiment's 5,400-second watchdog or a subagent stall timeout. Native final statistics: one background child, zero completed, one system-killed; no parent continuation or delivery.
- Official docs define that ceiling as 600,000 ms by default in `-p`, resetting when the owner takes a turn to handle a background result. Foreground children block the main conversation. With fork mode off (the `-p` default), `run_in_background: false` requests foreground when the result is needed; omission defaults to background. No foreground counterfactual was measured. The startup catalog did not advertise `TaskOutput`; do not invent an available wait primitive.
- Direct completion guidance has no explicit native foreground/await execution rule. **Ideate alone** has a drain-specific rule to keep the turn alive until exit, run foreground or await background completion (`devlyn-ideate/SKILL.md:120`). f02 did not invoke/read that skill body. Ideate remains out of scope.
- **0232 already recorded this failure class:** a background final review was lost after the owner promised to return; it explicitly left that as evidence that could license a later challenger. Its historical CLI details do not establish f02's timer behavior. **0235 tested and rejected generic done prose:** an appended sentence requiring verified requested/failure/compatibility behavior produced 2/4 completions versus B's 2/4 and two false completions; that line was stopped. Do not relabel the same proposal as new.

## Requested answer

Give a concise recommendation and strongest counterargument. Distinguish an existing obligation that the model failed to obey from a missing execution contract. Is the right action no change, a narrow solo candidate, or some other smaller evidence-backed action?

If proposing a candidate, specify its exact behavioral delta, smallest placement/scope, and falsifiable prediction. Explain why it is distinct from 0235, how it preserves useful independent native parallelism, and what evidence would make you reject it. Do not assume independent review is necessary on every task.

Specify the minimum prospective validation: separate native mechanism evidence from actual model compliance and final delivery; identify controls, negative/regression cases, stopping rule, and required whole-run wall/input/output accounting including every child and failure. Separate research validation cost from task execution cost. State what remains unknown; do not promise a sentence fixes f02 or generalizes across engines.

## Sources

- Detailed retained audit: `autoresearch/experiments/0237/results/f02-child-lifecycle-audit.md`; finalized integrity audit: `confirmation-source-audit.md`, f02-auth1 section.
- Raw finished cell: `/Users/aipalm/.local/share/nx01/0237-live/out-confirmation/f02-CF-CONFIG-claude-C-r1-auth1/`; sibling `verdict-f02-CF-CONFIG-claude-C-r1-auth1.json`.
- Product: `config/skills/_shared/task-completion.md`; `config/skills/devlyn-ideate/SKILL.md:120`.
- History: `autoresearch/iterations/0232-harness-ladder.md:276–279,396–399`; `0235-definition-of-done.md:18–20,82`.
- Official, checked 2026-10-10: [foreground/background](https://code.claude.com/docs/en/sub-agents#run-subagents-in-foreground-or-background), [native input semantics](https://code.claude.com/docs/en/agent-sdk/subagents#agentdefinition-configuration), [post-final-turn ceiling](https://code.claude.com/docs/en/env-vars).
