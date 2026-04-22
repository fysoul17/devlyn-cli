---
name: devlyn:auto-resolve
description: Fully automated build-evaluate-polish pipeline for any task type — bug fixes, new features, refactors, chores, and more. Use this as the default starting point when the user wants hands-free implementation with zero human intervention. Runs the full cycle — build, evaluate, fix loop, simplify, review, clean, docs — as a single command. Use when the user says "auto resolve", "build this", "implement this feature", "fix this", "run the full pipeline", "refactor this", or wants to walk away and come back to finished work.
---

Fully automated resolve-evaluate-polish pipeline. One command, zero human intervention. Spawns a subagent for each phase, uses file-based handoff between phases, and loops on evaluation feedback until the work passes or max rounds are reached.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<pipeline_workflow>

<orchestrator_context>
This pipeline is long-horizon agentic work. As the orchestrator, you spawn many subagents and read their handoff files; your own context grows over the run.

- Your context window is auto-compacted as it approaches its limit, so do not stop tasks early due to token-budget concerns. Keep the run going.
- All durable state lives in `.devlyn/pipeline.state.json` (control plane: source pointers, criteria status, phase verdicts) plus per-phase artifact files (`BUILD-GATE.md`, `EVAL-FINDINGS.md`, `BROWSER-RESULTS.md`, `CHALLENGE-FINDINGS.md`) and in git commits. `pipeline.state.json` is the single authoritative record of what phase reached what verdict on which criterion. Its schema is defined in `references/pipeline-state.md`.
- Best results come from `xhigh` effort. If you are running on lower effort and notice shallow reasoning during phase decisions, escalate.
</orchestrator_context>

<autonomy_contract>
This pipeline runs hands-free. The user launches it to walk away and come back to finished work, so the quality of this run is measured by how far it gets without human intervention. Apply these behaviors throughout every phase:

1. **Make decisions autonomously and log them in the final report.** When you would otherwise ask the user something ("Should I commit this?", "Ready to proceed?", "Which approach?"), pick the safe default, proceed, and record the decision in PHASE 8's report so the user can review it at the end.
2. **Run only the phases defined below, in the order given.** Doc updates, roadmap edits, changelog entries, and planning-doc changes belong in PHASE 7 (Docs). Resist inserting them earlier as freelance pre-work.
3. **Delegate all file changes to spawned subagents.** As the orchestrator, your actions are: parse input, spawn phase agents, read handoff files (`.devlyn/*.md`), run `git` commands, branch on verdicts, and emit the final report.
4. **Continue through the pipeline by default.** Stop only for: (a) a subagent reporting an unrecoverable failure, (b) PHASE 1 producing zero code changes, (c) `max-rounds` reached — in which case continue to PHASE 3 with a warning rather than halting. Every other situation means move on to the next phase.
5. **Treat questions as a signal to act instead.** If you notice yourself drafting a question to the user mid-pipeline, convert it into a decision + log entry and spawn the next phase.
</autonomy_contract>

<engine_routing_convention>
Every phase in this pipeline routes its work to the optimal model per `references/engine-routing.md`. The convention is the same everywhere:

- The phase prompt body below is **engine-agnostic** — same instructions whether Codex or Claude executes it.
- For phases routed to **Codex** (per the routing table), call `mcp__codex-cli__codex` per the patterns in `engine-routing.md` (How to Spawn a Codex BUILD/FIX Agent / How to Spawn a Codex Role / How to Spawn a Dual Role).
- For phases routed to **Claude**, spawn an Agent subagent with `mode: "bypassPermissions"` and pass the prompt body verbatim.
- `--engine claude` forces all phases to Claude. `--engine codex` forces implementation/analysis to Codex (Claude still handles orchestration and Chrome MCP). `--engine auto` (default) uses the routing table per phase.

Phase-level "Engine routing" notes below are short reminders only — `engine-routing.md` is the single source of truth.
</engine_routing_convention>

## PHASE 0: PARSE INPUT

1. Extract the task/issue description from `<pipeline_config>`.
2. Determine optional flags from the input (defaults in parentheses):
   - `--max-rounds N` (4) — max evaluate-fix loops before stopping with a report
   - `--skip-review` (false) — skip team-review phase
   - `--security-review` (auto) — run dedicated security audit. Auto-detects: runs when changes touch auth, secrets, user data, API endpoints, env/config, or crypto. Force with `--security-review always` or skip with `--security-review skip`
   - `--skip-clean` (false) — skip clean phase
   - `--skip-browser` (false) — skip browser validation phase (auto-skipped for non-web changes)
   - `--skip-docs` (false) — skip update-docs phase
   - `--skip-build-gate` (false) — skip the deterministic build gate (Phase 1.4). Not recommended — the build gate is the primary defense against "tests pass locally, breaks in CI/Docker/production" class of bugs.
   - `--build-gate MODE` (auto) — controls build gate behavior. `auto`: detect project type and run appropriate build/typecheck/lint commands; if Dockerfile(s) are present, Docker builds are included automatically. `strict`: auto + treat warnings as errors. `no-docker`: auto but skip Docker builds even if Dockerfiles exist (for faster iteration). `skip`: same as --skip-build-gate.
   - `--engine MODE` (auto) — controls which model handles each pipeline phase and team role. Modes:
     - `auto` (default): each phase and team role routes to the optimal model based on benchmark data. Requires Codex MCP server. Codex handles BUILD/FIX (SWE-bench Pro lead) and several team roles; Claude handles EVALUATE, CHALLENGE, BROWSER, and orchestration — creating a GAN-like dynamic where the builder and critic are always different models.
     - `codex`: Codex handles implementation/analysis phases, Claude handles orchestration, evaluation, and Chrome MCP.
     - `claude`: all phases use Claude subagents. No Codex calls.

   Flags can be passed naturally: `/devlyn:auto-resolve fix the auth bug --max-rounds 3 --skip-docs`
   Engine examples: `--engine auto`, `--engine codex`, `--engine claude`
   If no flags are present, use defaults. The default engine is `auto` — if the user does not pass `--engine`, treat it as `--engine auto`.

   **Consolidated flag**: `--with-codex` (and its variants `evaluate`/`review`/`both`) was rolled into the smarter `--engine auto` default. If the user passes it, inform them once and proceed with `--engine auto`: "Note: `--with-codex` was consolidated into `--engine auto` (default), which provides broader Codex coverage — Codex now handles BUILD, FIX, and several team roles automatically. No flag needed. Continuing with `--engine auto`."

3. **Engine pre-flight** (runs unless `--engine claude` was explicitly passed):
   - The default engine is `auto`. If the user did not pass `--engine`, the engine is `auto` — not `claude`.
   - Read `references/engine-routing.md` for the full routing table.
   - Call `mcp__codex-cli__ping` to verify the Codex MCP server is available. If ping fails, warn the user and offer: [1] Continue with `--engine claude` (fallback), [2] Abort.

4. **Initialize `.devlyn/pipeline.state.json` skeleton** (schema: `references/pipeline-state.md`):
   - `version: "1.0"`
   - `run_id`: `ar-<YYYYMMDD>-<HHMMSS>-<6-random-hex>` (generate via `date -u +%Y%m%d-%H%M%S` + `openssl rand -hex 3`)
   - `started_at`: current UTC ISO-8601
   - `engine`: `auto` / `codex` / `claude` (from flag)
   - `base_ref.branch`: `git rev-parse --abbrev-ref HEAD`
   - `base_ref.sha`: `git rev-parse HEAD`
   - `rounds.max_rounds`: from `--max-rounds` flag (default 4)
   - `rounds.global: 0`
   - Empty `phases`, `criteria`, `route` (PHASE 0.5 and downstream phases populate these)

5. Announce the pipeline plan:
```
Auto-resolve pipeline starting
Task: [extracted task description]
Engine: [auto / codex / claude]
Phases: Build → Build Gate → [Browser] → Evaluate → [Fix loop if needed] → Simplify → [Review] → Challenge → [Security] → [Clean] → [Docs]
Max evaluation rounds: [N]
```

## PHASE 0.5: SPEC PREFLIGHT & SOURCE RESOLUTION

This phase captures the contract. The ideate skill produces specs designed as auto-resolve's contract — `Requirements` are the done-criteria, `Out of Scope` bounds over-building, `Dependencies` gates sequencing. Phase 0.5 records that contract in `.devlyn/pipeline.state.json:source` so every downstream phase reads the same canonical source. **No copy of the spec is made** — the spec file itself is the source of truth; state.json stores pointers, integrity hashes, and per-criterion status.

State.json was created in PHASE 0. This phase populates `source`, `criteria[]`, and `route.stage_a`.

**Step 1 — Detect the source.** Scan `<pipeline_config>` task description for a path matching `docs/roadmap/phase-\d+/[^\s"'`)]+\.md`.

**If a spec path is found (spec-driven run):**

**Step 2a — Read the spec file.** If the file does not exist, stop with a `BLOCKED` verdict in the final report. Do not proceed to BUILD with a missing spec — the task description lies and silent recovery is worse than halting.

**Step 2b — Verify internal dependencies.** For each entry under `## Dependencies → Internal` (e.g. `1.1 User Auth`), locate `docs/roadmap/phase-*/[id]-*.md` and check frontmatter `status`. Any dep without `status: done` → stop with `BLOCKED` listing the unmet deps. Implementing out of sequence wastes the pipeline.

**Step 2c — Populate state.json source + criteria:**
- `source.type = "spec"`
- `source.spec_path = "<matched path>"`
- `source.spec_sha256 = sha256(<file contents>)` via `sha256sum <path>` (Linux) or `shasum -a 256 <path>` (macOS)
- `source.criteria_anchors = ["spec://requirements", "spec://out-of-scope", "spec://verification", "spec://constraints", "spec://architecture-notes", "spec://dependencies"]`
- `criteria[]`: one entry per `- [ ]` item in the spec's `## Requirements` section, in document order. Each entry: `{ "id": "C<N>", "ref": "spec://requirements/<N-1>", "status": "pending", "evidence": [], "failed_by_finding_ids": [] }` (N is 1-indexed; ref index is 0-indexed per anchor syntax).

**Step 2d — Announce.** One line: `Spec preflight: <spec path> — complexity <value>, <N> internal deps verified done, <M> criteria extracted, proceeding.` Surfaces in the final report.

**If no spec path is found (ad-hoc run):**

- `source.type = "generated"`
- `source.criteria_path = ".devlyn/criteria.generated.md"` (Phase 1 Phase B creates this file)
- `source.criteria_anchors = ["criteria.generated://requirements", "criteria.generated://out-of-scope", "criteria.generated://verification"]`
- `criteria = []` (Phase 1 Phase B populates these)
- Announce: `No spec detected — BUILD will synthesize criteria into .devlyn/criteria.generated.md.`

Every downstream phase reads `pipeline.state.json` first and follows `source.spec_path` or `source.criteria_path` to the canonical criteria text. No intermediate copy exists.

## PHASE 1: BUILD

**Engine**: BUILD row of the routing table — Codex on `auto`/`codex`, Claude on `claude`. Per `<engine_routing_convention>` above. Subagents do not have access to skills, so the prompt below includes everything they need inline.

Agent prompt — pass this to the spawned executor:

Investigate and implement the following task. Work through these phases in order:

**Phase A — Understand the task**: Read `.devlyn/pipeline.state.json`. If `source.type == "spec"`, open the spec file at `source.spec_path` directly and read it. The spec has already decided the task shape — use its `Objective`, `Constraints`, `Architecture Notes`, `Dependencies`, and frontmatter `complexity` as the exploration boundary. Do not re-classify the task type open-endedly; the spec already bounds the problem. Read only the files the spec implicates (Architecture Notes + Dependencies + any existing files touched by referenced patterns), then move on.

If `source.type == "generated"`, read the raw task description from `<pipeline_config>` and classify the task type:
- **Bug fix**: trace from symptom to root cause. Read error logs and affected code paths.
- **Feature**: explore the codebase to find existing patterns, integration points, and relevant modules.
- **Refactor/Chore**: understand current implementation, identify what needs to change and why.
- **UI/UX**: review existing components, design system, and user flows.
Read relevant files in parallel. Build a clear picture of what exists and what needs to change.

**Phase B — Resolve criteria source**: Read `.devlyn/pipeline.state.json:source`.

- **If `source.type == "spec"`**: the spec file is canonical. Phase 0.5 has already populated `criteria[]` in state.json from the spec's `## Requirements` section. **Do not create any criteria file** — read the Requirements, Out of Scope, Constraints, Architecture Notes, and Verification sections directly from `source.spec_path` whenever you need them. Copying them anywhere else would silently drift from the contract the ideate CHALLENGE rubric validated.

- **If `source.type == "generated"`**: no spec exists. Create `.devlyn/criteria.generated.md` once with three sections:
  ```
  ## Requirements
  - [ ] <specific, testable criterion>
  ...
  ## Out of Scope
  - <explicit exclusion>
  ...
  ## Verification
  - <observable verification step>
  ```
  Each Requirement must be verifiable (a test can assert it, or a human can observe it in under 30 seconds), specific (not "handles errors correctly"), and scoped to this task. Then update state.json `criteria[]` with one entry per Requirement: `{ "id": "C<N>", "ref": "criteria.generated://requirements/<N-1>", "status": "pending", "evidence": [], "failed_by_finding_ids": [] }`.

After this phase, either `source.spec_path` (spec-driven) or `.devlyn/criteria.generated.md` (ad-hoc) is the single canonical criteria source. No other criteria file is produced.

**Phase C — Assemble a team (complexity-gated)**: Determine complexity.

- If `source.type == "spec"`: read the spec file's frontmatter `complexity` field.
- If `source.type == "generated"`: classify from task scope — `low` (single file, no API changes), `medium` (multi-file, no cross-boundary), or `high` (cross-boundary, security-sensitive, or new subsystem).

If `complexity == "low"` AND the task does not touch risk areas (grep the spec or task description for: `auth`, `login`, `session`, `token`, `secret`, `password`, `crypto`, `api`, `env`, `permission`, `access`, `database`, `migration`, `payment`), skip TeamCreate entirely and implement directly — the multi-perspective team exists to catch ambiguity that low-complexity work has already resolved.

Otherwise (complexity medium or high, or risk areas present), use TeamCreate to create a team. Select teammates based on task type:
- Bug fix: root-cause-analyst + test-engineer (+ security-auditor, performance-engineer as needed)
- Feature: implementation-planner + test-engineer (+ ux-designer, architecture-reviewer, api-designer as needed)
- Refactor: architecture-reviewer + test-engineer
- UI/UX: product-designer + ux-designer + ui-designer (+ accessibility-auditor as needed)
Each teammate investigates from their perspective and sends findings back. Per-role engine routing follows the team-resolve table in `references/engine-routing.md`; Dual roles run both models in parallel.

**Phase D — Synthesize and implement**: After all teammates report, compile findings into a unified plan. Implement the solution — no workarounds, no hardcoded values, no silent error swallowing. For bugs: write a failing test first, then fix. For features: implement following existing patterns, then write tests. For refactors: ensure tests pass before and after.

**Phase E — Mark criteria implemented**: In `.devlyn/pipeline.state.json`, for each criterion you satisfied, update its entry to `status: "implemented"` and append an `evidence` record `{"file": "...", "line": N, "note": "brief description"}` pointing to the implementation. Run the full test suite.

**Phase F — Cleanup**: Shut down all teammates and delete the team.

The task is: [paste the task description here]

**After the agent completes**:
1. Verify `.devlyn/pipeline.state.json` exists and `criteria[]` has at least one entry with `status != "pending"` — if missing or all still pending, the agent did not follow instructions; re-spawn BUILD with an explicit reminder to update state.json
2. Run `git diff --stat` to confirm code was actually changed
3. If no changes were made, report failure and stop
4. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): phase 1 — build complete"` to create a rollback point

## PHASE 1.4: BUILD GATE

Skip if `--skip-build-gate` or `--build-gate skip` was set.

This phase runs the project's real build, typecheck, and lint commands — the same ones CI, Docker, and production environments will run. It catches the entire class of bugs that LLM-based evaluation and test suites cannot: type errors in un-tested files, cross-package type drift in monorepos, lint violations, missing production dependencies, and Dockerfile copy mismatches.

This is deterministic — if the compiler says no, the pipeline stops. No LLM judgment involved.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the Agent tool:

You are the build gate agent. Read `references/build-gate.md` from the auto-resolve skill directory for the full project-type detection matrix and execution rules.

Your job: detect every project type in this repo, run their build/typecheck/lint commands, and report results. You do NOT reason about code quality — you run commands and faithfully report what they output.

1. Read the detection matrix in `references/build-gate.md`
2. Scan the repo to detect all matching project types (a monorepo may match several)
3. Detect the package manager (npm/pnpm/yarn/bun) per the rules in the reference file
4. Run all gate commands. Sequential within a project type, parallel across unrelated types.
5. If `--build-gate strict` is set, apply strict-mode flags per the reference file
6. Run Dockerfile builds if Dockerfiles are detected, UNLESS `--build-gate no-docker` is set (see reference file)
7. Write results to `.devlyn/BUILD-GATE.md` following the output format in the reference file

For failures: include the FULL error output (not truncated) and extract root file:line references with concrete fix guidance so the fix agent knows exactly where to look.

**After the agent completes**:
1. Read `.devlyn/BUILD-GATE.md`
2. Extract verdict
3. Branch:
   - `PASS` → continue to PHASE 1.5
   - `FAIL` → go to PHASE 1.4-fix (build gate fix loop)

## PHASE 1.4-fix: BUILD GATE FIX LOOP

Triggered only when PHASE 1.4 returns FAIL.

Track a round counter. The build-gate fix loop and the main evaluate fix loop share **one global round counter** capped at `max-rounds` — increments from this loop and from PHASE 2.5 both count against the same total. If `round >= max-rounds`, stop with a clear failure report and do not continue to evaluate/browser/etc. Code that doesn't build cannot be meaningfully evaluated or tested.

**Engine**: FIX LOOP row of the routing table.

Agent prompt — pass this to the spawned executor:

Read `.devlyn/BUILD-GATE.md` — it contains deterministic build/typecheck/lint failures from real compiler output. These are not opinions; the compiler rejected this code. Fix every listed failure at the root cause level.

For each failure:
1. Read the referenced file:line and enough surrounding context to understand the error
2. For type errors: check BOTH sides of the type contract — the consumer AND the type definition. The fix may belong to either side. Do NOT suppress errors with `any`, `@ts-ignore`, `as unknown as`, `// eslint-disable`, or equivalent escape hatches.
3. For lint errors: fix the underlying issue, do not disable the rule.
4. For missing module/dependency errors: investigate the cause — it may be a missing dep in package.json, a typo in the import path, or a tsconfig paths misconfiguration.
5. After fixing, do NOT re-run the build yourself. The orchestrator re-runs PHASE 1.4.

**After the agent completes**:
1. **Checkpoint**: `git add -A && git commit -m "chore(pipeline): build gate fix round [N]"`
2. Increment the global round counter (shared with PHASE 2.5)
3. Go back to PHASE 1.4 (re-run the gate)

## PHASE 1.5: BROWSER VALIDATE (conditional)

Skip if `--skip-browser` was set.

1. **Check relevance**: Run `git diff --name-only` and check for web-relevant files (`*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.html`, `page.*`, `layout.*`, `route.*`). If none found, skip and note "Browser validation skipped — no web changes detected."

2. **Run validation**: Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the Agent tool:

You are a browser validation agent. Read the skill instructions at `.claude/skills/devlyn:browser-validate/SKILL.md` and follow the full workflow to validate this web application. The dev server should be started, tested, and left running (pass `--keep-server` internally) — the pipeline will clean it up later. Write your findings to `.devlyn/BROWSER-RESULTS.md`.

**After the agent completes**:
1. Read `.devlyn/BROWSER-RESULTS.md`
2. Extract the verdict
3. **Validate the verdict is real**: If the verdict says "code-level pass" or indicates no actual browser interaction occurred (no screenshots taken, no pages navigated, no DOM inspected), the validation did NOT happen. Treat this as if no browser validation ran — re-run PHASE 1.5 with `--tier 2` to force Playwright, or `--tier 3` for HTTP smoke. A "PARTIALLY VERIFIED" based on reading source code is not browser validation.
4. Branch on verdict:
   - `PASS` → continue to PHASE 2
   - `PASS WITH ISSUES` → continue to PHASE 2 (evaluator reads browser results as extra context)
   - `PARTIALLY VERIFIED` → continue to PHASE 2, but flag to the evaluator that browser coverage was incomplete — unverified features should be weighted more heavily. This verdict is only valid when features were actually tested in a browser and some couldn't be verified due to environment limitations (missing API keys, external services). It is NOT valid as a substitute for "browser tools didn't work."
   - `NEEDS WORK` → features don't work in the browser. Go to PHASE 2.5 fix loop. Fix agent reads `.devlyn/BROWSER-RESULTS.md` for which criterion failed, at what step, with what error. After fixing, re-run PHASE 1.5 to verify the fix before proceeding to Evaluate.
   - `BLOCKED` → app doesn't render. Go to PHASE 2.5 fix loop. After fixing, re-run PHASE 1.5.

## PHASE 2: EVALUATE

**Engine**: EVALUATE row of the routing table — Claude on every engine. When `--engine auto`, Codex built the code, so Claude evaluating Codex's work is the GAN dynamic by default; no separate Codex evaluation pass is needed.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`. Include all evaluation instructions inline (subagents do not have access to skills).

Agent prompt — pass this to the spawned executor:

You are an independent evaluator. Your job is to grade work produced by another agent against a specific rubric, not to praise it.

<investigate_before_answering>
Never claim a file:line or assert a behavior you have not opened and read. The canonical criteria source (see Step 1) is the rubric — read it first. Then read every changed/new file in full before marking anything VERIFIED or FAILED. Findings without a real file:line behind them are speculation; exclude them.
</investigate_before_answering>

<coverage_over_filtering>
Your goal is coverage at this stage, not severity filtering. Report every issue you find — uncertain ones, low-severity ones, all of them. The fix loop and the orchestrator's verdict logic do the filtering downstream. Each finding includes its severity and your confidence so the downstream layers can rank them; your job is to surface them, not pre-decide which ones matter.

This matters because under-reporting is the asymmetric cost: a missed bug ships broken code, a flagged non-issue costs a few minutes of review.
</coverage_over_filtering>

**Step 1 — Read the criteria source**: Open `.devlyn/pipeline.state.json`. Follow `source.spec_path` (spec-driven) or `source.criteria_path` (generated). Read the Requirements, Out of Scope, and Verification sections from that file directly — this is your primary grading rubric. The `criteria[]` array in state.json lists the IDs (`C1..CN`) and their current status set by BUILD. Every criterion must be verified with evidence.

**Step 2 — Discover changes**: Run `git diff HEAD~1` and `git status` to see what changed. Read all changed/new files in parallel.

**Step 3 — Evaluate**: For each changed file, check:
- Correctness: logic errors, silent failures, null access, incorrect API contracts
- Architecture: pattern violations, duplication, missing integration
- Security (if auth/secrets/user-data touched): injection, hardcoded credentials, missing validation
- Frontend (if UI changed): missing error/loading/empty states, React anti-patterns, server/client boundaries
- Test coverage: untested modules, missing edge cases

**Step 4 — Grade against criteria**: For each criterion in `pipeline.state.json:criteria[]` (mapped to its line in the canonical source file), mark VERIFIED (update `status: "verified"` + `evidence` array) or FAILED (update `status: "failed"` + `failed_by_finding_ids` referencing the relevant finding IDs in your findings output). Work directly on state.json — do not produce a separate criteria tracking file.

**Step 5 — Write findings**: Write `.devlyn/EVAL-FINDINGS.md` with this exact structure:

```
# Evaluation Findings
## Verdict: [PASS / PASS WITH ISSUES / NEEDS WORK / BLOCKED]
## Done Criteria Results
- [x] criterion — VERIFIED: evidence
- [ ] criterion — FAILED: what's wrong, file:line
## Findings Requiring Action
### CRITICAL
- `file:line` — description — Confidence: high/med/low — Fix: suggested approach
### HIGH
- `file:line` — description — Confidence: high/med/low — Fix: suggested approach
### MEDIUM / LOW
- `file:line` — description — Confidence: high/med/low — Fix: suggested approach
## Cross-Cutting Patterns
- pattern description
```

Verdict rules:
- `BLOCKED` — any CRITICAL issues
- `NEEDS WORK` — HIGH or MEDIUM issues
- `PASS WITH ISSUES` — only LOW cosmetic notes
- `PASS` — clean

Findings labeled "pre-existing" or "out of scope" still count if they relate to the criteria. The goal is working software, not blame attribution.

Calibration examples:
- A catch block that logs but doesn't surface the error to the user → HIGH (not MEDIUM). Logging is not error handling.
- A `let` that could be `const` → LOW. Linters catch this.
- "The error handling is generally quite good" is not a finding. Count the instances and name the files. "3 of 7 async ops have error states. 4 are missing: file:line, file:line…"

Do not delete `.devlyn/pipeline.state.json` or `.devlyn/EVAL-FINDINGS.md` — the orchestrator needs them.

**After the agent completes**:
1. Read `.devlyn/EVAL-FINDINGS.md`
2. Extract the verdict
3. Branch on verdict:
   - `PASS` → skip to PHASE 3
   - `PASS WITH ISSUES` → go to PHASE 2.5 (fix loop) — LOW-only issues are still issues; fix them
   - `NEEDS WORK` → go to PHASE 2.5 (fix loop)
   - `BLOCKED` → go to PHASE 2.5 (fix loop)
4. If `.devlyn/EVAL-FINDINGS.md` was not created, treat as NEEDS WORK and log a warning — absence of evidence is not evidence of absence

## PHASE 2.5: FIX LOOP (conditional)

Track the current round number. If `round >= max-rounds`, stop the loop and proceed to PHASE 3 with a warning that unresolved findings remain.

**Engine**: FIX LOOP row of the routing table. Use a fresh Codex call each round (no `sessionId` reuse — sandbox/fullAuto only apply on the first call of a session).

Agent prompt — pass this to the spawned executor:

Read every findings file present in `.devlyn/`:
- `.devlyn/EVAL-FINDINGS.md` — issues from the independent evaluator (PHASE 2)
- `.devlyn/BROWSER-RESULTS.md` — issues from browser validation (PHASE 1.5), if present and the verdict is `NEEDS WORK` or `BLOCKED`

Fix every finding regardless of severity (CRITICAL, HIGH, MEDIUM, and LOW). The pipeline loops until the relevant verdict returns PASS — there is no "shippable with issues" shortcut.

The original criteria are tracked in `.devlyn/pipeline.state.json:criteria[]`, with the full text at `source.spec_path` or `source.criteria_path` (follow the pointer). Your fixes must still satisfy those criteria. Do not delete or weaken criteria to make them pass.

For each finding: read the referenced file:line (or browser step / console error), understand the issue, implement the fix. No workarounds — fix the actual root cause. Run tests after fixing. When a previously-failed criterion is now satisfied, update its entry in state.json: clear `failed_by_finding_ids`, set `status: "implemented"`, and add an `evidence` record.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): fix round [N] complete"` to preserve the fix
2. Increment the global round counter (shared with PHASE 1.4-fix)
3. Re-run the phase that triggered the fix:
   - If invoked from PHASE 2 (eval failure) → go back to PHASE 2 to re-evaluate
   - If invoked from PHASE 1.5 (browser failure) → go back to PHASE 1.5 to re-validate the browser, then proceed to PHASE 2 only if browser passes

## PHASE 3: SIMPLIFY

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` for a quick cleanup pass.

Agent prompt — pass this to the Agent tool:

Review the recently changed files (use `git diff HEAD~1` to see what changed). Look for: code that could reuse existing utilities instead of reimplementing, quality issues (unclear naming, unnecessary complexity), and efficiency improvements (redundant operations, missing early returns). Fix any issues found. Keep changes minimal — this is a polish pass, not a rewrite.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): simplify pass complete"` if there are changes

## PHASE 4: REVIEW (skippable)

Skip if `--skip-review` was set.

**Engine**: REVIEW (team) — per-role routing per the team-review table in `references/engine-routing.md`. Dual roles run both models in parallel and merge findings.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the spawned executor:

Review all recent changes in this codebase (use `git diff main` and `git status` to determine scope). Assemble a review team using TeamCreate with specialized reviewers: security reviewer, quality reviewer, test analyst. Add UX reviewer, performance reviewer, or API reviewer based on the changes. Per-role engine routing follows the team-review table in `references/engine-routing.md`; Dual roles run both models in parallel and merge findings.

Each reviewer reports findings with file:line evidence grouped by severity (CRITICAL, HIGH, MEDIUM, LOW) and a confidence level. After all reviewers report, synthesize findings, deduplicate, and fix any CRITICAL issues directly. For HIGH issues, fix if straightforward.

Clean up the team after completion.

**After the review phase completes**:
1. If CRITICAL issues remain unfixed, log a warning in the final report
2. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): review fixes complete"` if there are changes

## PHASE 4.5: CHALLENGE

Every prior phase used checklists, criteria, or structured categories. This phase is deliberately different — it's a fresh pair of eyes with no checklist, no prior context, and a skeptical mandate. The subagent hasn't seen the criteria, the eval findings, or the review results. It reads the raw diff cold and asks: "would I mass-ship this?"

This is what catches the things structured reviews miss — subtle logic that technically works but isn't the right approach, assumptions nobody questioned, patterns that are fine but not best-practice, and integration seams that look correct in isolation but feel wrong when you read the whole changeset.

**Engine**: CHALLENGE row — Claude on every engine. The diff was likely produced by Codex on `--engine auto`; Claude reading it cold preserves the cross-model dynamic.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the spawned executor:

You are a senior engineer doing a final skeptical review before this code ships to production. You have not seen any prior reviews, test results, or design docs — read the code cold.

<investigate_before_answering>
Anchor every finding in code you have actually opened. Run `git diff main` for the change surface, then read each changed file in full (not just the hunks — surrounding context matters). Findings without a real file:line and a quote from the code are speculation; exclude them.
</investigate_before_answering>

Your job is not to check boxes. Your job is to find the things that would make a staff engineer say "hold on, let's talk about this before we ship." Think about:

- Would this approach survive a 10x traffic spike? A midnight oncall page? A junior dev maintaining it 6 months from now?
- Are there assumptions baked in that nobody stated out loud? Hardcoded limits, implicit ordering, missing edge cases in business logic?
- Is the error handling actually helpful, or does it just prevent crashes while leaving the user confused?
- Are there simpler, more idiomatic ways to do what this code does? Not "clever" alternatives — genuinely better approaches?
- Would you confidently approve this PR, or would you leave comments?

Be direct and concrete. Do not open with praise. Every finding must include `file:line` and a concrete fix — not "consider improving" but "change X to Y because Z."

Write `.devlyn/CHALLENGE-FINDINGS.md`:

```
# Challenge Findings
## Verdict: [PASS / NEEDS WORK]
## Findings
### [severity: CRITICAL / HIGH / MEDIUM]
- `file:line` — what's wrong — Fix: concrete change
```

<examples>
<example index="1">
GOOD finding (anchored, specific, fixable):
### CRITICAL
- `src/api/orders/cancel.ts:42` — `await db.transaction(...)` is missing — the read of `order.status` and the write of `order.status = "cancelled"` are not atomic, so two concurrent cancellations both succeed and the inventory hook fires twice. Fix: wrap the read+write in `db.transaction()` and re-check `order.status === "pending"` inside the transaction before the update.
</example>
<example index="2">
BAD finding (vague, unanchored, not actionable):
### HIGH
- The error handling could be improved. Consider being more defensive throughout.

Why this is bad: no file:line, no specific failure, no concrete fix. Either delete the finding or replace it with a real one anchored to a specific call site.
</example>
<example index="3">
GOOD finding (idiom / approach issue):
### MEDIUM
- `src/components/UserList.tsx:18-34` — fetching `/api/users` inside `useEffect` and managing loading/error state by hand re-implements what the project already does with the `useFetch` hook in `src/hooks/useFetch.ts`. Fix: replace the manual `useState`+`useEffect` with `useFetch('/api/users')` so this list inherits retry, cache, and abort handling.
</example>
</examples>

Verdict: `PASS` only if you would confidently ship this code with your name on it. If you found anything CRITICAL or HIGH, verdict is `NEEDS WORK`.

**After the agent completes**:
1. Read `.devlyn/CHALLENGE-FINDINGS.md`
2. Extract the verdict
3. Branch:
   - `PASS` → continue to PHASE 5
   - `NEEDS WORK` → spawn a fix subagent with `mode: "bypassPermissions"`:

     Read `.devlyn/CHALLENGE-FINDINGS.md` — it contains findings from a fresh skeptical review. Fix every CRITICAL and HIGH finding at the root cause. For MEDIUM findings, fix if straightforward. After fixing, run the test suite to verify nothing broke.

   After the fix agent completes:
   1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): challenge fixes complete"`
   2. Continue to PHASE 5 (do NOT re-run the challenge — one pass is sufficient to avoid infinite loops)

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

Agent prompt — pass this to the Agent tool (include the original task description from `<pipeline_config>` so the agent can detect spec paths):

You are the Docs phase of the auto-resolve pipeline. You have two jobs, in this order.

**Job 1 — Roadmap Sync** (run first, only if this task implemented a roadmap item)

The ideate skill produces specs at `docs/roadmap/phase-N/{id}-{slug}.md` and tracks them in `docs/ROADMAP.md`. When auto-resolve finishes a task for one of those specs, the index lies until someone flips it — and nobody does, so it rots. Your job is to flip it.

1. **Detect whether this task was a spec implementation.** Look at the original task description you were passed. Match against this regex: `docs/roadmap/phase-\d+/[^\s"'\`)]+\.md`. If there is no match, or if `docs/ROADMAP.md` does not exist in the repo, Job 1 is a no-op — skip straight to Job 2.
2. **Sanity-check against the diff.** Run `git diff main --stat` (or `git diff HEAD~N --stat` if on main). If the diff is empty or contains only doc changes, the build phase produced nothing — do NOT flip any status. Leave Job 1 untouched and continue to Job 2.
3. **Read the spec file** at the matched path. If its frontmatter already has `status: done`, Job 1 is already done — skip to Job 2. Otherwise:
   - Set `status: done` in the frontmatter.
   - Add a `completed: YYYY-MM-DD` field (use today's date from `date +%Y-%m-%d`).
   - Do not change any other fields, and do not touch the body of the spec.
4. **Update `docs/ROADMAP.md`.** Find the row whose `#` column matches the spec's `id` (e.g., row starting `| 2.3 |`). Change its Status column to `Done`. Do not touch any other row, and do not reformat the table.
5. **Check whether the phase is now fully Done.** Read every row of the phase's table (the one containing the just-flipped row). If every row's Status is `Done`, archive the phase:
   - Cut the phase's `## Phase N: …` heading and table out of the active section of ROADMAP.md.
   - If no `## Completed` section exists at the bottom of the file, create one just above end-of-file (below Decisions if Decisions exists).
   - Add a `<details>` block for the phase inside Completed, using the format defined in the devlyn:ideate skill's Context Archiving section. Pull each item's completion date from its spec file's `completed:` frontmatter; if a spec has none, use today's date.
   - Item spec files stay on disk — do not delete them. Only the index row moves.
6. **Report.** In your summary, say explicitly what you did: "Flipped spec 2.3 to done, updated ROADMAP.md row." And if applicable: "Phase 2 was fully Done — archived to Completed block."

**Safety invariants** — violating any of these means stop Job 1 and report it:
- Never flip a spec to `done` without a non-empty `git diff` touching non-doc files.
- Never flip multiple specs in one run — one task, one spec.
- Never edit a row whose `#` doesn't exactly match the spec's `id`.
- Never delete spec files.

**Job 2 — General doc sync**

Synchronize the rest of the documentation with recent code changes. Use `git log --oneline -20` and `git diff main` to understand what changed. Update any docs that reference changed APIs, features, or behaviors. Do not create new documentation files unless the changes introduced entirely new features with no existing docs. Preserve all forward-looking content: future plans, visions, open questions. (Job 1 already handled the roadmap index — don't second-guess it here.)

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): docs updated"` if there are changes

## PHASE 8: FINAL REPORT

After all phases complete:

1. Clean up temporary files:
   - Delete the `.devlyn/` directory entirely (contains pipeline.state.json, criteria.generated.md if ad-hoc, BUILD-GATE.md, EVAL-FINDINGS.md, BROWSER-RESULTS.md, CHALLENGE-FINDINGS.md, screenshots/, playwright temp files)
   - Kill any dev server process still running from browser validation

2. Run `git log --oneline -10` to show commits made during the pipeline

3. Present the report:

```
### Auto-Resolve Pipeline Complete

**Task**: [original task description]
**Engine**: [auto / codex / claude — if auto, note which phases used which model]

**Pipeline Summary**:
| Phase | Status | Notes |
|-------|--------|-------|
| Build (team-resolve) | [completed] | [brief summary; engine that ran it] |
| Build gate | [completed / skipped / FAIL after N rounds] | [project types detected, commands run, pass/fail per command] |
| Browser validate | [completed / skipped / auto-skipped] | [verdict, tier used, console errors, flow results] |
| Evaluate | [PASS/NEEDS WORK after N rounds] | [verdict + key findings] |
| Fix rounds | [N rounds / skipped] | [what was fixed] |
| Simplify | [completed / skipped] | [changes made] |
| Review (team) | [completed / skipped] | [findings summary; per-role engines if --engine auto] |
| Challenge | [PASS / NEEDS WORK] | [findings count, fixes applied] |
| Security review | [completed / skipped / auto-skipped] | [findings or "no security-sensitive changes"] |
| Clean | [completed / skipped] | [items cleaned] |
| Docs (update-docs) | [completed / skipped] | [docs updated] |

**Evaluation Rounds**: [N] of [max-rounds] used (shared budget across PHASE 1.4-fix and PHASE 2.5)
**Final Verdict**: [last evaluation verdict, or "BUILD GATE FAILED — code does not compile" if PHASE 1.4 exhausted the round budget before PHASE 2 ran]

**Commits created**:
[git log output]

**What to do next**:
- Review the changes: `git diff main`
- If satisfied, squash pipeline commits: `git rebase -i main` (combine the chore commits into meaningful ones)
- If not satisfied, run specific fixes: `/devlyn:team-resolve [specific issue]`
- For a final human review: `/devlyn:team-review`
```

</pipeline_workflow>
