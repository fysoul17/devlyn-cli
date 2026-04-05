---
name: devlyn:auto-resolve
description: Fully automated build-evaluate-polish pipeline for any task type — bug fixes, new features, refactors, chores, and more. Use this as the default starting point when the user wants hands-free implementation with zero human intervention. Runs the full cycle — build, evaluate, fix loop, simplify, review, clean, docs — as a single command. Use when the user says "auto resolve", "build this", "implement this feature", "fix this", "run the full pipeline", "refactor this", or wants to walk away and come back to finished work.
---

Fully automated resolve-evaluate-polish pipeline. One command, zero human intervention. Spawns a subagent for each phase, uses file-based handoff between phases, and loops on evaluation feedback until the work passes or max rounds are reached.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<pipeline_workflow>

<autonomy_contract>
This pipeline runs hands-free. The user launches it to walk away and come back to finished work, so the quality of this run is measured by how far it gets without human intervention. Apply these behaviors throughout every phase:

1. **Make decisions autonomously and log them in the final report.** When you would otherwise ask the user something ("Should I commit this?", "Ready to proceed?", "Which approach?"), pick the safe default, proceed, and record the decision in PHASE 8's report so the user can review it at the end.
2. **Run only the phases defined below, in the order given.** Doc updates, roadmap edits, changelog entries, and planning-doc changes belong in PHASE 7 (Docs). Resist inserting them earlier as freelance pre-work.
3. **Delegate all file changes to spawned subagents.** As the orchestrator, your actions are: parse input, spawn phase agents, read handoff files (`.devlyn/*.md`), run `git` commands, branch on verdicts, and emit the final report.
4. **Continue through the pipeline by default.** Stop only for: (a) a subagent reporting an unrecoverable failure, (b) PHASE 1 producing zero code changes, (c) `max-rounds` reached — in which case continue to PHASE 3 with a warning rather than halting. Every other situation means move on to the next phase.
5. **Treat questions as a signal to act instead.** If you notice yourself drafting a question to the user mid-pipeline, convert it into a decision + log entry and spawn the next phase.
</autonomy_contract>

## PHASE 0: PARSE INPUT

1. Extract the task/issue description from `<pipeline_config>`.
2. Determine optional flags from the input (defaults in parentheses):
   - `--max-rounds N` (2) — max evaluate-fix loops before stopping with a report
   - `--skip-review` (false) — skip team-review phase
   - `--security-review` (auto) — run dedicated security audit. Auto-detects: runs when changes touch auth, secrets, user data, API endpoints, env/config, or crypto. Force with `--security-review always` or skip with `--security-review skip`
   - `--skip-clean` (false) — skip clean phase
   - `--skip-browser` (false) — skip browser validation phase (auto-skipped for non-web changes)
   - `--skip-docs` (false) — skip update-docs phase
   - `--with-codex` (false) — use OpenAI Codex as a cross-model evaluator/reviewer via `mcp__codex-cli__*` MCP tools. Accepts: `evaluate`, `review`, or `both` (default when flag is present without value). When enabled, Codex provides an independent second opinion from a different model family, creating a GAN-like dynamic where Claude builds and Codex critiques.

   Flags can be passed naturally: `/devlyn:auto-resolve fix the auth bug --max-rounds 3 --skip-docs`
   Codex examples: `--with-codex` (both), `--with-codex evaluate`, `--with-codex review`
   If no flags are present, use defaults.

3. **If `--with-codex` is enabled**: Read `references/codex-integration.md` and run the "PRE-FLIGHT CHECK" section to verify Codex MCP server availability before proceeding.

4. Announce the pipeline plan:
```
Auto-resolve pipeline starting
Task: [extracted task description]
Phases: Build → [Browser] → Evaluate → [Fix loop if needed] → Simplify → [Review] → [Security] → [Clean] → [Docs]
Max evaluation rounds: [N]
Cross-model evaluation (Codex): [evaluate / review / both / disabled]
```

## PHASE 1: BUILD

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` to investigate and implement the fix. The subagent does NOT have access to skills, so include all necessary instructions inline.

Agent prompt — pass this to the Agent tool:

Investigate and implement the following task. Work through these phases in order:

**Phase A — Understand the task**: Read the task description carefully. Classify the task type:
- **Bug fix**: trace from symptom to root cause. Read error logs and affected code paths.
- **Feature**: explore the codebase to find existing patterns, integration points, and relevant modules.
- **Refactor/Chore**: understand current implementation, identify what needs to change and why.
- **UI/UX**: review existing components, design system, and user flows.
Read relevant files in parallel. Build a clear picture of what exists and what needs to change.

**Phase B — Define done criteria**: Before writing any code, create `.devlyn/done-criteria.md` with testable success criteria. Each criterion must be verifiable (a test can assert it or a human can observe it in under 30 seconds), specific (not vague like "handles errors correctly"), and scoped to this task. Include an "Out of Scope" section and a "Verification Method" section. This file is required — downstream evaluation depends on it.

**Phase C — Assemble a team**: Use TeamCreate to create a team. Select teammates based on task type:
- Bug fix: root-cause-analyst + test-engineer (+ security-auditor, performance-engineer as needed)
- Feature: implementation-planner + test-engineer (+ ux-designer, architecture-reviewer, api-designer as needed)
- Refactor: architecture-reviewer + test-engineer
- UI/UX: product-designer + ux-designer + ui-designer (+ accessibility-auditor as needed)
Each teammate investigates from their perspective and sends findings back.

**Phase D — Synthesize and implement**: After all teammates report, compile findings into a unified plan. Implement the solution — no workarounds, no hardcoded values, no silent error swallowing. For bugs: write a failing test first, then fix. For features: implement following existing patterns, then write tests. For refactors: ensure tests pass before and after.

**Phase E — Update done criteria**: Mark each criterion in `.devlyn/done-criteria.md` as satisfied. Run the full test suite.

**Phase F — Cleanup**: Shut down all teammates and delete the team.

The task is: [paste the task description here]

**After the agent completes**:
1. Verify `.devlyn/done-criteria.md` exists — if missing, create a basic one from the agent's output summary
2. Run `git diff --stat` to confirm code was actually changed
3. If no changes were made, report failure and stop
4. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): phase 1 — build complete"` to create a rollback point

## PHASE 1.5: BROWSER VALIDATE (conditional)

Skip if `--skip-browser` was set.

1. **Check relevance**: Run `git diff --name-only` and check for web-relevant files (`*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.html`, `page.*`, `layout.*`, `route.*`). If none found, skip and note "Browser validation skipped — no web changes detected."

2. **Run validation**: Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the Agent tool:

You are a browser validation agent. Read the skill instructions at `.claude/skills/devlyn:browser-validate/SKILL.md` and follow the full workflow to validate this web application. The dev server should be started, tested, and left running (pass `--keep-server` internally) — the pipeline will clean it up later. Write your findings to `.devlyn/BROWSER-RESULTS.md`.

**After the agent completes**:
1. Read `.devlyn/BROWSER-RESULTS.md`
2. Extract the verdict
3. Branch on verdict:
   - `PASS` → continue to PHASE 2
   - `PASS WITH ISSUES` → continue to PHASE 2 (evaluator reads browser results as extra context)
   - `PARTIALLY VERIFIED` → continue to PHASE 2, but flag to the evaluator that browser coverage was incomplete — unverified features should be weighted more heavily
   - `NEEDS WORK` → features don't work in the browser. Go to PHASE 2.5 fix loop. Fix agent reads `.devlyn/BROWSER-RESULTS.md` for which criterion failed, at what step, with what error. After fixing, re-run PHASE 1.5 to verify the fix before proceeding to Evaluate.
   - `BLOCKED` → app doesn't render. Go to PHASE 2.5 fix loop. After fixing, re-run PHASE 1.5.

## PHASE 2: EVALUATE

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` to evaluate the work. Include all evaluation instructions inline.

Agent prompt — pass this to the Agent tool:

You are an independent evaluator. Your job is to grade work produced by another agent, not to praise it. You will be too lenient by default — fight this tendency. When in doubt, score DOWN, not up. A false negative (missing a bug) ships broken code. A false positive (flagging a non-issue) costs minutes of review. The cost is asymmetric.

**Step 1 — Read the done criteria**: Read `.devlyn/done-criteria.md`. This is your primary grading rubric. Every criterion must be verified with evidence.

**Step 2 — Discover changes**: Run `git diff HEAD~1` and `git status` to see what changed. Read all changed/new files in parallel.

**Step 3 — Evaluate**: For each changed file, check:
- Correctness: logic errors, silent failures, null access, incorrect API contracts
- Architecture: pattern violations, duplication, missing integration
- Security (if auth/secrets/user-data touched): injection, hardcoded credentials, missing validation
- Frontend (if UI changed): missing error/loading/empty states, React anti-patterns, server/client boundaries
- Test coverage: untested modules, missing edge cases

**Step 4 — Grade against done criteria**: For each criterion in done-criteria.md, mark VERIFIED (with evidence) or FAILED (with file:line and what's wrong).

**Step 5 — Write findings**: Write `.devlyn/EVAL-FINDINGS.md` with this exact structure:

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

Do NOT delete `.devlyn/done-criteria.md` or `.devlyn/EVAL-FINDINGS.md` — the orchestrator needs them.

**After the agent completes**:
1. Read `.devlyn/EVAL-FINDINGS.md`
2. Extract the verdict
3. **If `--with-codex` includes `evaluate` or `both`**: Read `references/codex-integration.md` and follow the "PHASE 2-CODEX: CROSS-MODEL EVALUATE" section. This runs Codex as a second evaluator and merges findings into `EVAL-FINDINGS.md`.
4. Branch on verdict (from the merged findings if Codex was used):
   - `PASS` → skip to PHASE 3
   - `PASS WITH ISSUES` → skip to PHASE 3 (issues are shippable)
   - `NEEDS WORK` → go to PHASE 2.5 (fix loop)
   - `BLOCKED` → go to PHASE 2.5 (fix loop)
5. If `.devlyn/EVAL-FINDINGS.md` was not created, treat as PASS WITH ISSUES and log a warning

## PHASE 2.5: FIX LOOP (conditional)

Track the current round number. If `round >= max-rounds`, stop the loop and proceed to PHASE 3 with a warning that unresolved findings remain.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` to fix the evaluation findings.

Agent prompt — pass this to the Agent tool:

Read `.devlyn/EVAL-FINDINGS.md` — it contains specific issues found by an independent evaluator. Fix every CRITICAL and HIGH finding. Address MEDIUM findings if straightforward.

The original done criteria are in `.devlyn/done-criteria.md` — your fixes must still satisfy those criteria. Do not delete or weaken criteria to make them pass.

For each finding: read the referenced file:line, understand the issue, implement the fix. No workarounds — fix the actual root cause. Run tests after fixing. Update `.devlyn/done-criteria.md` to mark fixed items.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): fix round [N] complete"` to preserve the fix
2. Increment round counter
3. Go back to PHASE 2 (re-evaluate)

## PHASE 3: SIMPLIFY

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` for a quick cleanup pass.

Agent prompt — pass this to the Agent tool:

Review the recently changed files (use `git diff HEAD~1` to see what changed). Look for: code that could reuse existing utilities instead of reimplementing, quality issues (unclear naming, unnecessary complexity), and efficiency improvements (redundant operations, missing early returns). Fix any issues found. Keep changes minimal — this is a polish pass, not a rewrite.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): simplify pass complete"` if there are changes

## PHASE 4: REVIEW (skippable)

Skip if `--skip-review` was set.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` for a multi-perspective review.

Agent prompt — pass this to the Agent tool:

Review all recent changes in this codebase (use `git diff main` and `git status` to determine scope). Assemble a review team using TeamCreate with specialized reviewers: security reviewer, quality reviewer, test analyst. Add UX reviewer, performance reviewer, or API reviewer based on the changes.

Each reviewer evaluates from their perspective, sends findings with file:line evidence grouped by severity (CRITICAL, HIGH, MEDIUM, LOW). After all reviewers report, synthesize findings, deduplicate, and fix any CRITICAL issues directly. For HIGH issues, fix if straightforward.

Clean up the team after completion.

**If `--with-codex` includes `review` or `both`**: Read `references/codex-integration.md` and follow the "PHASE 4B: CODEX REVIEW" section. This runs Codex's independent code review and reconciles findings with the Claude team review.

**After the review phase completes**:
1. If CRITICAL issues remain unfixed, log a warning in the final report
2. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): review fixes complete"` if there are changes

## PHASE 5: SECURITY REVIEW (conditional)

Determine whether to run this phase:
- If `--security-review always` → run
- If `--security-review skip` → skip
- If `--security-review auto` (default) → auto-detect by scanning changed files for security-sensitive patterns:
  - Run `git diff main --name-only` and check for files matching: `*auth*`, `*login*`, `*session*`, `*token*`, `*secret*`, `*crypt*`, `*password*`, `*api*`, `*middleware*`, `*env*`, `*config*`, `*permission*`, `*role*`, `*access*`
  - Also run `git diff main` and scan for patterns: `API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PRIVATE_KEY`, `Bearer`, `jwt`, `bcrypt`, `crypto`, `env.`, `process.env`
  - If any match → run. If no matches → skip and note "Security review skipped — no security-sensitive changes detected."

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` for a dedicated security audit.

Agent prompt — pass this to the Agent tool:

You are a security auditor performing a dedicated security review. This is NOT a general code review — focus exclusively on security concerns.

Examine all recent changes (use `git diff main` to see what changed). For every changed file:

1. **Input validation**: Trace every user input from entry point to storage/output. Check for: SQL injection, XSS, command injection, path traversal, SSRF.
2. **Authentication & authorization**: Are new endpoints properly protected? Are auth checks consistent with existing patterns? Any privilege escalation paths?
3. **Secrets & credentials**: Grep for hardcoded API keys, tokens, passwords, private keys. Check that secrets come from env vars, not source code. Verify .gitignore covers sensitive files.
4. **Data exposure**: Are error messages leaking internal details? Are logs capturing sensitive data? Are API responses returning more data than needed?
5. **Dependencies**: If package.json/requirements.txt changed, run the package manager's audit command (npm audit, pip-audit, etc.).
6. **CSRF/CORS**: For new endpoints with side effects, verify CSRF protection. Check CORS configuration for overly permissive origins.

For each finding, provide: severity (CRITICAL/HIGH/MEDIUM), file:line, OWASP category, description, and suggested fix.

Fix any CRITICAL findings directly. For HIGH findings, fix if straightforward, otherwise document clearly.

**After the agent completes**:
1. If CRITICAL issues were found and fixed, this is expected — continue
2. If CRITICAL issues remain unfixed, log a warning in the final report
3. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): security review complete"` if there are changes

## PHASE 6: CLEAN (skippable)

Skip if `--skip-clean` was set.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the Agent tool:

Scan the codebase for dead code, unused dependencies, and code hygiene issues in recently changed files. Focus on: unused imports, unreachable code paths, unused variables, dependencies in package.json that are no longer imported. Keep the scope tight — only clean what's related to recent work. Remove what's confirmed dead, leave anything ambiguous.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): cleanup complete"` if there are changes

## PHASE 7: DOCS (skippable)

Skip if `--skip-docs` was set.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the Agent tool:

Synchronize documentation with recent code changes. Use `git log --oneline -20` and `git diff main` to understand what changed. Update any docs that reference changed APIs, features, or behaviors. Do not create new documentation files unless the changes introduced entirely new features with no existing docs. Preserve all forward-looking content: roadmaps, future plans, visions, open questions.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): docs updated"` if there are changes

## PHASE 8: FINAL REPORT

After all phases complete:

1. Clean up temporary files:
   - Delete the `.devlyn/` directory entirely (contains done-criteria.md, EVAL-FINDINGS.md, BROWSER-RESULTS.md, screenshots/, playwright temp files)
   - Kill any dev server process still running from browser validation

2. Run `git log --oneline -10` to show commits made during the pipeline

3. Present the report:

```
### Auto-Resolve Pipeline Complete

**Task**: [original task description]

**Pipeline Summary**:
| Phase | Status | Notes |
|-------|--------|-------|
| Build (team-resolve) | [completed] | [brief summary] |
| Browser validate | [completed / skipped / auto-skipped] | [verdict, tier used, console errors, flow results] |
| Evaluate (Claude) | [PASS/NEEDS WORK after N rounds] | [verdict + key findings] |
| Evaluate (Codex) | [completed / skipped] | [Codex-only findings count, merged verdict] |
| Fix rounds | [N rounds / skipped] | [what was fixed] |
| Simplify | [completed / skipped] | [changes made] |
| Review (Claude team) | [completed / skipped] | [findings summary] |
| Review (Codex) | [completed / skipped] | [Codex-only findings, agreed findings] |
| Security review | [completed / skipped / auto-skipped] | [findings or "no security-sensitive changes"] |
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
