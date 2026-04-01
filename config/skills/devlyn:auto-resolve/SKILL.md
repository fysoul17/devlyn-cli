---
name: devlyn:auto-resolve
description: Fully automated build-evaluate-polish pipeline for any task type — bug fixes, new features, refactors, chores, and more. Use this as the default starting point when the user wants hands-free implementation with zero human intervention. Runs the full cycle — build, evaluate, fix loop, simplify, review, clean, docs — as a single command. Use when the user says "auto resolve", "build this", "implement this feature", "fix this", "run the full pipeline", "refactor this", or wants to walk away and come back to finished work.
---

Fully automated resolve-evaluate-polish pipeline. One command, zero human intervention. Spawns a subagent for each phase, uses file-based handoff between phases, and loops on evaluation feedback until the work passes or max rounds are reached.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<pipeline_workflow>

## PHASE 0: PARSE INPUT

1. Extract the task/issue description from `<pipeline_config>`.
2. Determine optional flags from the input (defaults in parentheses):
   - `--max-rounds N` (2) — max evaluate-fix loops before stopping with a report
   - `--skip-review` (false) — skip team-review phase
   - `--skip-clean` (false) — skip clean phase
   - `--skip-docs` (false) — skip update-docs phase

   Flags can be passed naturally: `/devlyn:auto-resolve fix the auth bug --max-rounds 3 --skip-docs`
   If no flags are present, use defaults.

3. Announce the pipeline plan:
```
Auto-resolve pipeline starting
Task: [extracted task description]
Phases: Build → Evaluate → [Fix loop if needed] → Simplify → [Review] → [Clean] → [Docs]
Max evaluation rounds: [N]
```

## PHASE 1: BUILD

Spawn a subagent using the Agent tool to investigate and implement the fix. The subagent does NOT have access to skills, so include all necessary instructions inline.

Agent prompt — pass this to the Agent tool:

Investigate and implement the following task. Work through these phases in order:

**Phase A — Understand the task**: Read the task description carefully. Classify the task type:
- **Bug fix**: trace from symptom to root cause. Read error logs and affected code paths.
- **Feature**: explore the codebase to find existing patterns, integration points, and relevant modules.
- **Refactor/Chore**: understand current implementation, identify what needs to change and why.
- **UI/UX**: review existing components, design system, and user flows.
Read relevant files in parallel. Build a clear picture of what exists and what needs to change.

**Phase B — Define done criteria**: Before writing any code, create `.claude/done-criteria.md` with testable success criteria. Each criterion must be verifiable (a test can assert it or a human can observe it in under 30 seconds), specific (not vague like "handles errors correctly"), and scoped to this task. Include an "Out of Scope" section and a "Verification Method" section. This file is required — downstream evaluation depends on it.

**Phase C — Assemble a team**: Use TeamCreate to create a team. Select teammates based on task type:
- Bug fix: root-cause-analyst + test-engineer (+ security-auditor, performance-engineer as needed)
- Feature: implementation-planner + test-engineer (+ ux-designer, architecture-reviewer, api-designer as needed)
- Refactor: architecture-reviewer + test-engineer
- UI/UX: product-designer + ux-designer + ui-designer (+ accessibility-auditor as needed)
Each teammate investigates from their perspective and sends findings back.

**Phase D — Synthesize and implement**: After all teammates report, compile findings into a unified plan. Implement the solution — no workarounds, no hardcoded values, no silent error swallowing. For bugs: write a failing test first, then fix. For features: implement following existing patterns, then write tests. For refactors: ensure tests pass before and after.

**Phase E — Update done criteria**: Mark each criterion in `.claude/done-criteria.md` as satisfied. Run the full test suite.

**Phase F — Cleanup**: Shut down all teammates and delete the team.

The task is: [paste the task description here]

**After the agent completes**:
1. Verify `.claude/done-criteria.md` exists — if missing, create a basic one from the agent's output summary
2. Run `git diff --stat` to confirm code was actually changed
3. If no changes were made, report failure and stop
4. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): phase 1 — build complete"` to create a rollback point

## PHASE 2: EVALUATE

Spawn a subagent using the Agent tool to evaluate the work. Include all evaluation instructions inline.

Agent prompt — pass this to the Agent tool:

You are an independent evaluator. Your job is to grade work produced by another agent, not to praise it. You will be too lenient by default — fight this tendency. When in doubt, score DOWN, not up. A false negative (missing a bug) ships broken code. A false positive (flagging a non-issue) costs minutes of review. The cost is asymmetric.

**Step 1 — Read the done criteria**: Read `.claude/done-criteria.md`. This is your primary grading rubric. Every criterion must be verified with evidence.

**Step 2 — Discover changes**: Run `git diff HEAD~1` and `git status` to see what changed. Read all changed/new files in parallel.

**Step 3 — Evaluate**: For each changed file, check:
- Correctness: logic errors, silent failures, null access, incorrect API contracts
- Architecture: pattern violations, duplication, missing integration
- Security (if auth/secrets/user-data touched): injection, hardcoded credentials, missing validation
- Frontend (if UI changed): missing error/loading/empty states, React anti-patterns, server/client boundaries
- Test coverage: untested modules, missing edge cases

**Step 4 — Grade against done criteria**: For each criterion in done-criteria.md, mark VERIFIED (with evidence) or FAILED (with file:line and what's wrong).

**Step 5 — Write findings**: Write `.claude/EVAL-FINDINGS.md` with this exact structure:

```
# Evaluation Findings
## Verdict: [PASS / PASS WITH ISSUES / NEEDS WORK / BLOCKED]
## Done Criteria Results
- [x] criterion — VERIFIED: evidence
- [ ] criterion — FAILED: what's wrong, file:line
## Findings Requiring Action
### CRITICAL
- `file:line` — description — Fix: suggested approach
### HIGH
- `file:line` — description — Fix: suggested approach
## Cross-Cutting Patterns
- pattern description
```

Verdict rules: BLOCKED = any CRITICAL issues. NEEDS WORK = HIGH issues that should be fixed. PASS WITH ISSUES = only MEDIUM/LOW. PASS = clean.

Calibration examples to guide your judgment:
- A catch block that logs but doesn't surface error to user = HIGH (not MEDIUM). Logging is not error handling.
- A `let` that could be `const` = LOW note only. Linters catch this.
- "The error handling is generally quite good" = WRONG. Count the instances. Name the files. "3 of 7 async ops have error states. 4 are missing: file:line, file:line..."

Do NOT delete `.claude/done-criteria.md` or `.claude/EVAL-FINDINGS.md` — the orchestrator needs them.

**After the agent completes**:
1. Read `.claude/EVAL-FINDINGS.md`
2. Extract the verdict
3. Branch on verdict:
   - `PASS` → skip to PHASE 3
   - `PASS WITH ISSUES` → skip to PHASE 3 (issues are shippable)
   - `NEEDS WORK` → go to PHASE 2.5 (fix loop)
   - `BLOCKED` → go to PHASE 2.5 (fix loop)
4. If `.claude/EVAL-FINDINGS.md` was not created, treat as PASS WITH ISSUES and log a warning

## PHASE 2.5: FIX LOOP (conditional)

Track the current round number. If `round >= max-rounds`, stop the loop and proceed to PHASE 3 with a warning that unresolved findings remain.

Spawn a subagent using the Agent tool to fix the evaluation findings.

Agent prompt — pass this to the Agent tool:

Read `.claude/EVAL-FINDINGS.md` — it contains specific issues found by an independent evaluator. Fix every CRITICAL and HIGH finding. Address MEDIUM findings if straightforward.

The original done criteria are in `.claude/done-criteria.md` — your fixes must still satisfy those criteria. Do not delete or weaken criteria to make them pass.

For each finding: read the referenced file:line, understand the issue, implement the fix. No workarounds — fix the actual root cause. Run tests after fixing. Update `.claude/done-criteria.md` to mark fixed items.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): fix round [N] complete"` to preserve the fix
2. Increment round counter
3. Go back to PHASE 2 (re-evaluate)

## PHASE 3: SIMPLIFY

Spawn a subagent using the Agent tool for a quick cleanup pass.

Agent prompt — pass this to the Agent tool:

Review the recently changed files (use `git diff HEAD~1` to see what changed). Look for: code that could reuse existing utilities instead of reimplementing, quality issues (unclear naming, unnecessary complexity), and efficiency improvements (redundant operations, missing early returns). Fix any issues found. Keep changes minimal — this is a polish pass, not a rewrite.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): simplify pass complete"` if there are changes

## PHASE 4: REVIEW (skippable)

Skip if `--skip-review` was set.

Spawn a subagent using the Agent tool for a multi-perspective review.

Agent prompt — pass this to the Agent tool:

Review all recent changes in this codebase (use `git diff main` and `git status` to determine scope). Assemble a review team using TeamCreate with specialized reviewers: security reviewer, quality reviewer, test analyst. Add UX reviewer, performance reviewer, or API reviewer based on the changes.

Each reviewer evaluates from their perspective, sends findings with file:line evidence grouped by severity (CRITICAL, HIGH, MEDIUM, LOW). After all reviewers report, synthesize findings, deduplicate, and fix any CRITICAL issues directly. For HIGH issues, fix if straightforward.

Clean up the team after completion.

**After the agent completes**:
1. If CRITICAL issues remain unfixed, log a warning in the final report
2. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): review fixes complete"` if there are changes

## PHASE 5: CLEAN (skippable)

Skip if `--skip-clean` was set.

Spawn a subagent using the Agent tool.

Agent prompt — pass this to the Agent tool:

Scan the codebase for dead code, unused dependencies, and code hygiene issues in recently changed files. Focus on: unused imports, unreachable code paths, unused variables, dependencies in package.json that are no longer imported. Keep the scope tight — only clean what's related to recent work. Remove what's confirmed dead, leave anything ambiguous.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): cleanup complete"` if there are changes

## PHASE 6: DOCS (skippable)

Skip if `--skip-docs` was set.

Spawn a subagent using the Agent tool.

Agent prompt — pass this to the Agent tool:

Synchronize documentation with recent code changes. Use `git log --oneline -20` and `git diff main` to understand what changed. Update any docs that reference changed APIs, features, or behaviors. Do not create new documentation files unless the changes introduced entirely new features with no existing docs. Preserve all forward-looking content: roadmaps, future plans, visions, open questions.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): docs updated"` if there are changes

## PHASE 7: FINAL REPORT

After all phases complete:

1. Clean up temporary files:
   - Delete `.claude/done-criteria.md`
   - Delete `.claude/EVAL-FINDINGS.md`

2. Run `git log --oneline -10` to show commits made during the pipeline

3. Present the report:

```
### Auto-Resolve Pipeline Complete

**Task**: [original task description]

**Pipeline Summary**:
| Phase | Status | Notes |
|-------|--------|-------|
| Build (team-resolve) | [completed] | [brief summary] |
| Evaluate | [PASS/NEEDS WORK after N rounds] | [verdict + key findings] |
| Fix rounds | [N rounds / skipped] | [what was fixed] |
| Simplify | [completed / skipped] | [changes made] |
| Review (team-review) | [completed / skipped] | [findings summary] |
| Clean | [completed / skipped] | [items cleaned] |
| Docs (update-docs) | [completed / skipped] | [docs updated] |

**Evaluation Rounds**: [N] of [max-rounds] used
**Final Verdict**: [last evaluation verdict]

**Commits created**:
[git log output]

**What to do next**:
- Review the changes: `git diff main`
- If satisfied, squash pipeline commits: `git rebase -i main` (combine the chore commits into meaningful ones)
- If not satisfied, run specific fixes: `/devlyn:team-resolve [specific issue]`
- For a final human review: `/devlyn:team-review`
```

</pipeline_workflow>
