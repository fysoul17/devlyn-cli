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
- All durable state lives in `.devlyn/pipeline.state.json` (control plane: source pointers, criteria status, phase verdicts) plus per-phase artifacts — `<phase>.findings.jsonl` (SARIF-aligned structured findings) and `<phase>.log.md` (human prose + raw detail) for phases that emit findings (build_gate, browser_validate, evaluate, challenge, security_review) — and in git commits. `pipeline.state.json` is the **single authoritative verdict source** — orchestrator branching reads `phases.<name>.verdict` directly, never parses artifact files. Schemas: `references/pipeline-state.md`, `references/findings-schema.md`.
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

<harness_principles>
Before acting: verify state, source, diff base, and artifact contracts. Prefer deletion or reuse over new machinery. Change only files the task requires. Each phase optimizes for its declared success criteria, not for completing a checklist. Fix root causes only — no `any`, `@ts-ignore`, silent catches, or hardcoded values. Label hypotheses explicitly; back claims with file:line evidence. Align structured outputs with production standards (SARIF `partialFingerprints`, semver, ISO-8601).
</harness_principles>

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

<goal>
Implement code changes that satisfy every pending criterion in `pipeline.state.json:criteria[]` without violating anything declared Out of Scope or Constraints. Make the source's intent run in the code.
</goal>

<input>
- Canonical criteria: `pipeline.state.json:source`. Follow `source.spec_path` (spec file — read directly, do not copy) or `source.criteria_path` (`.devlyn/criteria.generated.md` — this file may not yet exist; see OUTPUT CONTRACT).
- Codebase at `pipeline.state.json:base_ref.sha`.
- Task statement appended below.
</input>

<output_contract>
- **Code changes** implementing every `pending` criterion. Use `git diff` to confirm.
- **state.json criteria updates**: for each criterion you satisfied, set `status: "implemented"` and append an `evidence` record `{"file": "...", "line": N, "note": "brief"}`.
- **If `source.type == "generated"` and `.devlyn/criteria.generated.md` does not exist**: create it once with `## Requirements` (each `- [ ]` testable in under 30 seconds, specific, scoped), `## Out of Scope`, `## Verification`. Then populate state.json `criteria[]` with `{"id": "C<N>", "ref": "criteria.generated://requirements/<N-1>", "status": "pending", "evidence": [], "failed_by_finding_ids": []}`. Also classify task complexity into `low` (single file, no API changes), `medium` (multi-file, no cross-boundary), or `high` (cross-boundary, security-sensitive, or new subsystem) and write it as `phases.build.complexity` in state.json for team-gating below.
- **No pending criterion remains**: every entry in `criteria[]` must transition to `status: "implemented"` with an `evidence` record before you exit. There is no exception. If a criterion genuinely cannot be satisfied in this run (missing external dependency, blocking design ambiguity that requires human input), stop the build entirely: set `phases.build.verdict: "BLOCKED"` and report the obstacle in your return text so the orchestrator halts the pipeline. Never exit with a criterion still `pending`. BUILD must not mark any criterion `failed` — `failed` is Evaluate-only per the state-machine in `references/pipeline-state.md`. The only BUILD-legal transitions are `pending → implemented` (per-criterion success) or halt via `phases.build.verdict: "BLOCKED"` (entire phase halts).
- **Tests** added or updated for changed behavior. Run the full test suite before you stop.
- **Team** (only if source-declared `complexity != "low"` — for spec, read `source.spec_path` frontmatter; for generated, use the classification you wrote to `phases.build.complexity` above — OR any risk keyword matches the source body: `auth, login, session, token, secret, password, crypto, api, env, permission, access, database, migration, payment`): use `TeamCreate` per the task-type table below; collect findings; shut down the team before exiting. Otherwise implement directly.
</output_contract>

<quality_bar>
- Criteria and Out-of-Scope from the source are the contract — never weaken, reword, or delete them.
- Read only the files the source implicates (Architecture Notes + Dependencies + touched patterns), not the whole codebase.
- Bugs: write a failing test first, then fix. Features: follow existing patterns, then write tests. Refactors: tests pass before and after.
- Fix root causes only — no `any`, `@ts-ignore`, silent `catch`, or hardcoded values.
</quality_bar>

<principle>
The source is the contract. Your output is evidence that the contract now runs in code.
</principle>

<team_role_selection>
When team assembly triggers, select teammates by task type (per-role engine routing follows `references/engine-routing.md`):
- Bug fix: root-cause-analyst + test-engineer (+ security-auditor / performance-engineer as needed)
- Feature: implementation-planner + test-engineer (+ ux-designer / architecture-reviewer / api-designer as needed)
- Refactor: architecture-reviewer + test-engineer
- UI/UX: product-designer + ux-designer + ui-designer (+ accessibility-auditor as needed)
</team_role_selection>

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

You are the build gate agent. Read `references/build-gate.md` for the project-type detection matrix and execution rules, and `references/findings-schema.md` for the findings output format.

Your job: detect every project type in this repo, run their build/typecheck/lint commands, and emit structured results. You do NOT reason about code quality — you run commands and faithfully report what they output.

1. Read the detection matrix in `references/build-gate.md`
2. Scan the repo to detect all matching project types (a monorepo may match several)
3. Detect the package manager (npm/pnpm/yarn/bun) per the rules in the reference file
4. Run all gate commands. Sequential within a project type, parallel across unrelated types.
5. If `--build-gate strict` is set, apply strict-mode flags per the reference file
6. Run Dockerfile builds if Dockerfiles are detected, UNLESS `--build-gate no-docker` is set (see reference file)

**Output contract** (see `references/findings-schema.md` and `references/pipeline-state.md`):

- `.devlyn/build_gate.findings.jsonl` — one JSON line per compiler/typecheck/lint failure. `rule_id` examples: `build.type-error`, `build.lint-violation`, `build.dep-missing`, `build.docker-copy-mismatch`. Each finding MUST include `file` + `line` + concise `message` (not the full stack trace) + concrete `fix_hint`. Leave `partial_fingerprints` as `{}` or omit the field — the orchestrator computes and injects it after this phase completes (see `references/findings-schema.md`).
- `.devlyn/build_gate.log.md` — human summary. Detected project types, commands run with exit codes and timing, and the full raw stderr/stdout from failing commands (this is where long compiler output lives, NOT in the JSONL `message`).
- Update `pipeline.state.json.phases.build_gate` with: `verdict` (`PASS` if all exit 0, else `FAIL`), `engine: "bash"`, `started_at`, `completed_at`, `duration_ms`, `round` (current round number), `artifacts.findings_file` and `artifacts.log_file` paths.

**After the agent completes**:
1. **Inject fingerprints.** Run the reference snippet from `references/findings-schema.md` over `.devlyn/build_gate.findings.jsonl` — compute `partial_fingerprints` for each line and write back. This is deterministic orchestrator bookkeeping; do not delegate to the subagent.
2. Read `pipeline.state.json.phases.build_gate.verdict`
3. Branch:
   - `PASS` → continue to PHASE 1.5
   - `FAIL` → go to PHASE 1.4-fix (build gate fix loop)

## PHASE 1.4-fix: BUILD GATE FIX LOOP

Triggered only when PHASE 1.4 returns FAIL.

Track a round counter. The build-gate fix loop and the main evaluate fix loop share **one global round counter** capped at `max-rounds` — increments from this loop and from PHASE 2.5 both count against the same total. If `round >= max-rounds`, stop with a clear failure report and do not continue to evaluate/browser/etc. Code that doesn't build cannot be meaningfully evaluated or tested.

**Engine**: FIX LOOP row of the routing table.

Before spawning the fix agent, the orchestrator assembles `.devlyn/fix-batch.round-<N>.json` by reading `.devlyn/build_gate.findings.jsonl`, filtering to `status == "open"` entries, and packaging only the minimum needed (`id`, `rule_id`, `severity`, `file`, `line`, `message`, `fix_hint`, `partial_fingerprints`) plus the acceptance command (`.devlyn/build_gate.log.md` → "Commands" table). The fix agent receives the packet path — it does NOT re-parse prior findings files or the full compiler log.

Agent prompt — pass this to the spawned executor:

Read `.devlyn/fix-batch.round-<N>.json` — it contains the open, blocking build-gate failures extracted from real compiler output. These are not opinions; the compiler rejected this code. Fix every listed entry at the root cause.

For each entry:
1. Read the referenced `file:line` and enough surrounding context to understand the error. If you need the raw compiler output, `.devlyn/build_gate.log.md` has the full stderr/stdout.
2. For type errors: check BOTH sides of the type contract — the consumer AND the type definition. Do NOT suppress with `any`, `@ts-ignore`, `as unknown as`, `// eslint-disable`, or equivalent escape hatches.
3. For lint errors: fix the underlying issue, do not disable the rule.
4. For missing module/dependency errors: investigate root cause — missing dep in package.json, typo in import path, or tsconfig paths misconfiguration.
5. After fixing, do NOT re-run the build yourself. The orchestrator re-runs PHASE 1.4.

**After the agent completes**:
1. **Checkpoint**: `git add -A && git commit -m "chore(pipeline): build gate fix round [N]"`
2. Increment the global round counter (shared with PHASE 2.5)
3. Go back to PHASE 1.4 (re-run the gate)

## PHASE 1.5: BROWSER VALIDATE (conditional)

Skip if `--skip-browser` was set.

1. **Check relevance**: Run `git diff --name-only <pipeline.state.json.base_ref.sha>` (use the frozen run-start SHA, not ambient HEAD — after fix-round checkpoint commits, ambient diffs silently return empty and would auto-skip this phase incorrectly). Check the output for web-relevant files (`*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.html`, `page.*`, `layout.*`, `route.*`). If none found, skip and note "Browser validation skipped — no web changes detected."

2. **Run validation**: Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the Agent tool:

You are a browser validation agent. Read `.claude/skills/devlyn:browser-validate/SKILL.md` for the full workflow and `references/findings-schema.md` for the findings output format. Start the dev server, test the implemented feature end-to-end, and leave the server running (pass `--keep-server` internally) — the pipeline will clean it up later.

**Output contract**:
- `.devlyn/browser_validate.findings.jsonl` — one JSON line per browser-observable failure (`rule_id` examples: `browser.render-failure`, `browser.feature-broken`, `browser.console-error`, `browser.network-error`, `browser.accessibility-violation`). Each with `file` + `line` where a source-code file was implicated (or the page route + component path); `message` short; `fix_hint` concrete with file:line. Leave `partial_fingerprints` as `{}` — the orchestrator computes it after the phase completes.
- `.devlyn/browser_validate.log.md` — human summary: which tier was used (chrome MCP / Playwright / curl), dev server URL, screenshots taken, pages navigated, console errors collected, flow steps executed per feature from `pipeline.state.json:criteria[]`.
- Update `pipeline.state.json.phases.browser_validate` with `verdict`, `engine: "claude"`, timing, `round`, and `artifacts.{findings_file, log_file}`.

Verdict taxonomy (written to state.json):
- `PASS` — every criterion verified in a real browser, no blocking errors
- `PASS_WITH_ISSUES` — criteria verified; LOW-severity findings only
- `PARTIALLY_VERIFIED` — actual browser interaction happened, but some criteria unverifiable due to environment limits (missing API keys, external services). NOT valid as a substitute for "browser tools didn't work."
- `NEEDS_WORK` — one or more criteria failed in the browser (populates findings with `blocking: true`)
- `BLOCKED` — app does not render at all

**After the agent completes**:
1. **Inject fingerprints** into `.devlyn/browser_validate.findings.jsonl` (if present and non-empty) per `references/findings-schema.md`.
2. Read `pipeline.state.json.phases.browser_validate.verdict`
3. **Sanity check**: if the verdict is `PASS`/`PASS_WITH_ISSUES` but `browser_validate.log.md` shows no screenshots taken and no pages navigated, treat as if no browser validation ran — re-run PHASE 1.5 with `--tier 2` to force Playwright, or `--tier 3` for HTTP smoke. A code-level verdict is not browser validation.
4. Branch on verdict:
   - `PASS` / `PASS_WITH_ISSUES` → continue to PHASE 2
   - `PARTIALLY_VERIFIED` → continue to PHASE 2, flag to evaluator via a note in state.json that browser coverage was incomplete
   - `NEEDS_WORK` / `BLOCKED` → go to PHASE 2.5 fix loop; after fixing, re-run PHASE 1.5 before PHASE 2

## PHASE 2: EVALUATE

**Engine**: EVALUATE row of the routing table — Claude on every engine. When `--engine auto`, Codex built the code, so Claude evaluating Codex's work is the GAN dynamic by default; no separate Codex evaluation pass is needed.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`. Include all evaluation instructions inline (subagents do not have access to skills).

Agent prompt — pass this to the spawned executor:

<goal>
Independently verify whether every criterion in `pipeline.state.json:criteria[]` is satisfied by the current code. Surface every defect with file:line evidence. You are a skeptic, not a cheerleader — praise is not your job.
</goal>

<input>
- Canonical rubric: `pipeline.state.json:source`. Follow `source.spec_path` or `source.criteria_path` and read Requirements + Out of Scope + Verification directly.
- Change surface: `git diff <pipeline.state.json:base_ref.sha>` + `git status`. Read every changed/new file in full — not just the hunks.
- Prior browser findings at `.devlyn/browser_validate.findings.jsonl` (if that phase ran).
</input>

<output_contract>
- **`.devlyn/evaluate.findings.jsonl`** — one JSON per line (schema: `references/findings-schema.md`). Fields per finding:
  `id` (`EVAL-<4digit>`), `rule_id` (stable kebab-case, e.g. `correctness.silent-error`, `ux.missing-error-state`, `architecture.duplication`, `security.missing-validation`, `types.any-cast-escape`, `style.let-vs-const`, `scope.out-of-scope-violation`), `level` (`error`/`warning`/`note` — map from severity: CRITICAL/HIGH → error, MEDIUM → warning, LOW → note), `severity` (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`), `confidence` (0.0–1.0), `message` (one line naming the issue, not symptoms), `file`, `line` (1-based primary location), `phase: "evaluate"`, `criterion_ref` (the exact `ref` string from a `criteria[]` entry — e.g. `"spec://requirements/2"` — when the finding fails a specific criterion; or a section-level anchor from `state.source.criteria_anchors` such as `"spec://constraints"` or `"spec://out-of-scope"` when the finding is cross-cutting; or `null` when scope-broader than any anchor), `fix_hint` (concrete action quoting file:line), `blocking` (CRITICAL/HIGH/MEDIUM default true, LOW false), `status: "open"`, `partial_fingerprints: {}` (orchestrator injects post-phase).
- **`.devlyn/evaluate.log.md`** — 3–5 line human summary: verdict + criteria pass/fail counts + top 3 risks + cross-cutting patterns if any. Prose here; structured data in the JSONL.
- **state.json criteria updates** — every `criteria[]` entry must leave Evaluate in a terminal state. Incoming status from BUILD is normally `implemented`; transition each to `status: "verified"` (append `evidence` record confirming satisfaction) OR `status: "failed"` (set `failed_by_finding_ids` to the IDs you emitted). If a criterion is still `pending` (BUILD did not satisfy it), mark it `failed` with a finding whose `rule_id` is `correctness.criterion-unimplemented` and whose `fix_hint` names what was missed. No `criteria[]` entry may remain `pending` or `implemented` after Evaluate.
- **state.json phases.evaluate** — `verdict` per taxonomy, `engine: "claude"`, `model`, timing, `round`, `artifacts.{findings_file, log_file}`.

Verdict taxonomy: `BLOCKED` (any CRITICAL) / `NEEDS_WORK` (HIGH or MEDIUM present) / `PASS_WITH_ISSUES` (LOW only) / `PASS` (clean).
</output_contract>

<quality_bar>
- Every finding must point at a file:line you have opened and read. Findings without real anchors are speculation — exclude them.
- Every failed criterion maps to ≥1 finding `id`.
- **Coverage over comfort**: report uncertain and LOW findings too; downstream filters rank them. Missing a real defect ships broken code — the asymmetry is decisive.
- Audit each changed file for: correctness (logic errors, silent failures, null access, wrong API contracts), architecture (pattern violations, duplication, missing integration), security (if auth/secrets/user-data touched: injection, hardcoded credentials, missing validation), frontend (if UI changed: missing error/loading/empty states, React anti-patterns, server/client boundaries), test coverage (untested modules, missing edge cases).
- Calibration: a catch block that logs but doesn't surface the error to the user → HIGH, not MEDIUM (logging ≠ error handling). A `let` that could be `const` → LOW (linters catch it). "Error handling is generally quite good" is not a finding — count the instances, name the files.
- "Pre-existing" findings still count if they relate to the criteria. Working software, not blame attribution.
- **Out-of-Scope violations are findings**: if BUILD added behavior the source's `## Out of Scope` explicitly excludes, emit a finding with `rule_id: "scope.out-of-scope-violation"`, `severity: HIGH`, `criterion_ref: "spec://out-of-scope"` (or `"criteria.generated://out-of-scope"`), and `fix_hint` naming what to remove. OOS violations fail the pipeline the same as missing requirements.
</quality_bar>

<principle>
Missing a real defect is worse than reporting an extra one. Asymmetric cost demands bias toward reporting.
</principle>

Do not delete `pipeline.state.json` or the JSONL/log files — the orchestrator needs them.

**After the agent completes**:
1. **Inject fingerprints** into `.devlyn/evaluate.findings.jsonl` per the reference snippet in `references/findings-schema.md`.
2. Read `pipeline.state.json.phases.evaluate.verdict`
3. Branch on verdict:
   - `PASS` → skip to PHASE 3
   - `PASS_WITH_ISSUES` → go to PHASE 2.5 (fix loop) — LOW-only issues are still issues; fix them
   - `NEEDS_WORK` → go to PHASE 2.5 (fix loop)
   - `BLOCKED` → go to PHASE 2.5 (fix loop)
4. If `phases.evaluate.verdict` is `null` or the findings/log files were not written, treat as `NEEDS_WORK` and log a warning — absence of evidence is not evidence of absence.

## PHASE 2.5: FIX LOOP (conditional)

Track the current round number. If `round >= max-rounds`, stop the loop and proceed to PHASE 3 with a warning that unresolved findings remain.

**Engine**: FIX LOOP row of the routing table. Use a fresh Codex call each round (no `sessionId` reuse — sandbox/fullAuto only apply on the first call of a session).

**Before spawning the fix agent, the orchestrator assembles a fix-batch packet.** Read `.devlyn/evaluate.findings.jsonl` (and `.devlyn/browser_validate.findings.jsonl` if the PHASE 1.5 verdict was `NEEDS_WORK` or `BLOCKED`), filter to entries with `status == "open"`, and write `.devlyn/fix-batch.round-<N>.json`:

```json
{
  "round": <N>,
  "max_rounds": <from state.rounds.max_rounds>,
  "base_ref_sha": "<state.base_ref.sha>",
  "criteria_source": "<state.source.spec_path or state.source.criteria_path>",
  "findings": [
    { "id": "EVAL-0007", "rule_id": "...", "severity": "HIGH", "file": "...", "line": 84, "message": "...", "fix_hint": "...", "criterion_ref": "spec://requirements/2", "partial_fingerprints": {...} },
    ...
  ],
  "failed_criteria": ["C2", "C3"],
  "acceptance": {
    "build_gate_cmd": "<from build-gate log>",
    "test_cmd": "<language-appropriate: 'pnpm test' / 'cargo test' / etc.>"
  }
}
```

The fix agent receives this packet and does NOT re-parse the full findings files — the packet is the minimum sufficient context. Agents that need raw detail (full stderr, full browser flow log) can read `.devlyn/build_gate.log.md` or `.devlyn/browser_validate.log.md` on demand.

Agent prompt — pass this to the spawned executor (include the packet path):

Read `.devlyn/fix-batch.round-<N>.json` — it contains the open, blocking findings from independent evaluation and/or browser validation. Fix every listed entry at the root cause. The pipeline loops until the relevant verdict returns `PASS` — there is no "shippable with issues" shortcut.

The original criteria are tracked in `pipeline.state.json:criteria[]`, with full text at `source.spec_path` or `source.criteria_path` (follow the pointer). Your fixes must still satisfy those criteria. Do not delete or weaken criteria to make them pass.

For each finding in the packet: read the referenced `file:line`, understand the issue, implement the fix. No workarounds — fix the actual root cause, no `any`/`@ts-ignore`/silent catches. Run tests after fixing. If you need the full raw output for a build failure or browser flow, open `.devlyn/build_gate.log.md` or `.devlyn/browser_validate.log.md` directly.

When a previously-failed criterion is now satisfied, update its entry in state.json: clear `failed_by_finding_ids`, set `status: "implemented"`, and add an `evidence` record.

**After the agent completes**:
1. **Checkpoint**: `git add -A && git commit -m "chore(pipeline): fix round [N] complete"` to preserve the fix
2. Increment the global round counter (shared with PHASE 1.4-fix)
3. Re-run the phase that triggered the fix:
   - If invoked from PHASE 2 (eval failure) → go back to PHASE 2 to re-evaluate
   - If invoked from PHASE 1.5 (browser failure) → go back to PHASE 1.5 to re-validate, then PHASE 2 only if browser passes

## PHASE 3: SIMPLIFY

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` for a quick cleanup pass.

Agent prompt — pass this to the Agent tool:

Review the recently changed files (use `git diff <pipeline.state.json.base_ref.sha>` — the frozen run-start SHA — to see what changed since the pipeline started). Look for: code that could reuse existing utilities instead of reimplementing, quality issues (unclear naming, unnecessary complexity), and efficiency improvements (redundant operations, missing early returns). Fix any issues found. Keep changes minimal — this is a polish pass, not a rewrite.

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): simplify pass complete"` if there are changes

## PHASE 4: REVIEW (skippable)

Skip if `--skip-review` was set.

**Engine**: REVIEW (team) — per-role routing per the team-review table in `references/engine-routing.md`. Dual roles run both models in parallel and merge findings.

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"`.

Agent prompt — pass this to the spawned executor:

Review all recent changes in this codebase (use `git diff <pipeline.state.json.base_ref.sha>` and `git status` to determine scope — all phases share the same frozen base SHA for consistent diffs). Assemble a review team using TeamCreate with specialized reviewers: security reviewer, quality reviewer, test analyst. Add UX reviewer, performance reviewer, or API reviewer based on the changes. Per-role engine routing follows the team-review table in `references/engine-routing.md`; Dual roles run both models in parallel and merge findings.

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

<goal>
Read the diff cold — no checklist, no prior-phase context. Find what a staff engineer would block before this PR ships. Any hesitation is a finding.
</goal>

<input>
- Change surface: `git diff <pipeline.state.json:base_ref.sha>`. Read every changed file in full, not just the hunks.
</input>

<output_contract>
- **`.devlyn/challenge.findings.jsonl`** — one JSON per line (schema: `references/findings-schema.md`). Fields: `id: "CHLG-<4digit>"`, `rule_id` (examples: `design.non-atomic-transaction`, `design.duplicate-pattern`, `design.hidden-assumption`, `design.unidiomatic-pattern`), `severity` (CRITICAL/HIGH/MEDIUM — no LOW; Challenge is ship/no-ship), `file`, `line`, `message`, `fix_hint` (concrete change quoting file:line), `phase: "challenge"`, `status: "open"`, `partial_fingerprints: {}` (orchestrator injects post-phase).
- **`.devlyn/challenge.log.md`** — verdict + top 3 concerns framed as "why a staff engineer would stop this PR".
- **state.json phases.challenge** — `verdict` (`PASS` or `NEEDS_WORK` — no middle ground), `engine: "claude"`, `model`, timing, `round: 1`, `artifacts.{findings_file, log_file}`.

Verdict: `PASS` only if you would confidently ship this code with your name on it AND you emitted zero open findings. Any open finding of any severity (including MEDIUM) → `NEEDS_WORK`. Challenge has no "issues OK to ship" middle ground; either you'd ship with your name on it, or you'd leave comments — and leaving comments means `NEEDS_WORK`.
</output_contract>

<quality_bar>
- Every finding anchored to `file:line` in code you have opened, with a concrete fix. Vague ≠ finding.
- `fix_hint` is a specific change ("change X to Y because Z"), never "consider improving".
- Interrogate: would this survive 10x traffic? A midnight oncall page? A junior dev maintaining it in 6 months? Are baked-in assumptions stated out loud (hardcoded limits, implicit ordering, missed business-logic edges)? Is error handling actually helpful or does it prevent crashes while leaving users confused? Are there simpler idiomatic approaches — not "clever" but genuinely better?
- Do not open with praise.
</quality_bar>

<principle>
Cold eyes catch what structured reviews miss. "Would I ship this with my name on it?" is the only question.
</principle>

<example index="1">
GOOD (anchored JSONL): `{"id":"CHLG-0001","rule_id":"design.non-atomic-transaction","severity":"CRITICAL","message":"order.status read and write are not atomic in cancel handler — concurrent cancellations both succeed and fire inventory hook twice","file":"src/api/orders/cancel.ts","line":42,"fix_hint":"Wrap read+write in db.transaction() at src/api/orders/cancel.ts:40-50; re-check order.status === 'pending' inside transaction before update",...}`
</example>
<example index="2">
BAD (vague, unanchored): "The error handling could be improved. Consider being more defensive." — no file:line, no specific failure, no concrete fix. Exclude.
</example>

**After the agent completes**:
1. **Inject fingerprints** into `.devlyn/challenge.findings.jsonl` per `references/findings-schema.md`.
2. Read `pipeline.state.json.phases.challenge.verdict`
3. Branch:
   - `PASS` → continue to PHASE 5
   - `NEEDS_WORK` → **assemble `.devlyn/fix-batch.challenge.json`** from `.devlyn/challenge.findings.jsonl` (same packet shape as PHASE 2.5's `fix-batch.round-<N>.json`: filter `status == "open"` + `severity in {CRITICAL, HIGH}` + optionally MEDIUM if straightforward; include minimal keys + acceptance commands). Then spawn a fix subagent with `mode: "bypassPermissions"` that reads the packet path only — not the full findings file — and fixes every listed entry at the root cause. After fixing, run the test suite.

   After the fix agent completes:
   1. **Checkpoint**: `git add -A && git commit -m "chore(pipeline): challenge fixes complete"`
   2. Continue to PHASE 5 (do NOT re-run challenge — one pass is sufficient to avoid infinite loops)

## PHASE 5: SECURITY REVIEW (conditional)

Determine whether to run this phase:
- If `--security-review always` → run
- If `--security-review skip` → skip
- If `--security-review auto` (default) → auto-detect by scanning changed files for security-sensitive patterns:
  - Run `git diff <pipeline.state.json.base_ref.sha> --name-only` and check for files matching: `*auth*`, `*login*`, `*session*`, `*token*`, `*secret*`, `*crypt*`, `*password*`, `*api*`, `*middleware*`, `*env*`, `*config*`, `*permission*`, `*role*`, `*access*`
  - Also run `git diff <pipeline.state.json.base_ref.sha>` and scan for patterns: `API_KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PRIVATE_KEY`, `Bearer`, `jwt`, `bcrypt`, `crypto`, `env.`, `process.env`
  - If any match → run. If no matches → skip and note "Security review skipped — no security-sensitive changes detected."

Spawn a subagent using the Agent tool with `mode: "bypassPermissions"` for a dedicated security audit.

Agent prompt — pass this to the Agent tool:

You are a security auditor performing a dedicated security review. This is NOT a general code review — focus exclusively on security concerns.

Examine all recent changes (use `git diff <pipeline.state.json.base_ref.sha>` to see what changed since the pipeline started). For every changed file:

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
2. **Sanity-check against the diff.** Run `git diff <pipeline.state.json.base_ref.sha> --stat`. If the diff is empty or contains only doc changes, the build phase produced nothing — do NOT flip any status. Leave Job 1 untouched and continue to Job 2.
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

Synchronize the rest of the documentation with recent code changes. Use `git log --oneline -20` and `git diff <pipeline.state.json.base_ref.sha>` to understand what changed since the pipeline started. Update any docs that reference changed APIs, features, or behaviors. Do not create new documentation files unless the changes introduced entirely new features with no existing docs. Preserve all forward-looking content: future plans, visions, open questions. (Job 1 already handled the roadmap index — don't second-guess it here.)

**After the agent completes**:
1. **Checkpoint**: Run `git add -A && git commit -m "chore(pipeline): docs updated"` if there are changes

## PHASE 8: FINAL REPORT

After all phases complete:

1. Clean up temporary files:
   - Delete the `.devlyn/` directory entirely (contains pipeline.state.json, criteria.generated.md if ad-hoc, `<phase>.findings.jsonl` + `<phase>.log.md` for each phase that emitted findings, fix-batch.round-N.json per fix round, screenshots/, playwright temp files)
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
