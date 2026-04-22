---
name: devlyn:auto-resolve
description: Fully automated build-evaluate-polish pipeline for any task type — bug fixes, new features, refactors, chores. Use this as the default starting point when the user wants hands-free implementation with zero human intervention. Runs the full cycle — build, evaluate, fix loop, simplify, review, clean, docs — as a single command. Use when the user says "auto resolve", "build this", "implement this feature", "fix this", "run the full pipeline", "refactor this", or wants to walk away and come back to finished work.
---

Orchestrator for the hands-free implementation pipeline. Spawns one subagent per phase, uses file-based handoff, and loops on evaluation feedback until the work passes or `max_rounds` is reached. The orchestrator itself does not write code — it parses input, spawns phases, reads handoff artifacts, runs git commands, branches on verdicts, and emits the final report.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<orchestrator_context>
Long-horizon agentic work. Your context auto-compacts as it approaches the limit — do not stop early due to token-budget concerns. All durable state lives in `.devlyn/pipeline.state.json` (control plane: pointers, criteria, verdicts, `perf` timing/token accounting) plus `<phase>.findings.jsonl` + `<phase>.log.md` for phases that emit findings. `state.json` is the **single authoritative verdict source** — branch on `phases.<name>.verdict` directly, never parse artifact files. At PHASE 8, the run's `.devlyn/*` artifacts are **archived** to `.devlyn/runs/<run_id>/` (last 10 kept). Schemas: `references/pipeline-state.md`, `references/findings-schema.md`. Best results come from `xhigh` reasoning effort.
</orchestrator_context>

<perf_instrumentation>
Every phase is timed and token-accounted. Because production use is the benchmark, this instrumentation is not optional:

1. At each phase spawn, capture `phase_started_at = <unix ms>`.
2. Subagent completion notification returns `total_tokens` (Agent subagents) or the Codex response includes usage (Codex calls). Capture that value as `phase_tokens`.
3. After verdict/artifacts are written to `state.phases.<name>`, append one entry to `state.perf.per_phase`: `{phase, engine, wall_ms: now - phase_started_at, tokens: phase_tokens, round, triggered_by}`.
4. Build gate (bash) reports `tokens: 0`. Dual-mode phases record one entry per model (two entries total) so Codex vs Claude cost is separately recoverable.
5. At PHASE 8, set `state.perf.wall_ms = now - state.started_at_unix` and `state.perf.tokens_total = sum(per_phase[].tokens)`. Archive preserves the perf block.

Schema: `references/pipeline-state.md#perf`. Do NOT skip or approximate — missing perf data makes the harness's own efficiency claims unverifiable.
</perf_instrumentation>

<autonomy_contract>
This pipeline runs hands-free. Measured by how far it gets without human intervention.

1. **Never prompt the user mid-pipeline.** When you'd otherwise ask ("should I commit?", "which approach?"), pick the safe default, proceed, and log it in the final report.
2. **Codex availability**: on `--engine auto`/`codex`, call `mcp__codex-cli__ping` at the start. **If ping fails, silently fall back to `--engine claude`** and log `engine downgraded: codex-ping failed` in the final report. Do NOT present a [1]/[2] menu. Do NOT abort.
3. **Run only the phases defined below, in order.** Doc updates, roadmap edits, and changelog belong in PHASE 7 (DOCS). Don't insert them earlier.
4. **Delegate all file changes to spawned subagents.** Orchestrator actions: parse input, spawn phase agents, read handoff files, run `git`, branch on verdicts, emit report, archive.
5. **Continue by default.** Stop only for: (a) unrecoverable subagent failure, (b) PHASE 1 producing zero code changes, (c) build-gate / browser fix-loop exhausting `max_rounds` (halt → FINAL REPORT). Eval/Challenge/Review/Security exhaustion proceeds with warning — never halts.
</autonomy_contract>

<harness_principles>
Before acting: verify state, source integrity, diff base, artifact contracts. Prefer deletion or reuse over new machinery. Change only files the task requires. Each phase optimizes for its declared success criteria, not a checklist. Fix root causes only — no `any`, `@ts-ignore`, silent catches, hardcoded values. Label hypotheses explicitly; back claims with file:line evidence.
</harness_principles>

<engine_routing_convention>
Every phase routes to the optimal model per `references/engine-routing.md`:

- Phase prompt bodies (in `references/phases/`) are engine-agnostic.
- Phases routed to **Codex**: call `mcp__codex-cli__codex` per the spawn patterns in `engine-routing.md`.
- Phases routed to **Claude**: spawn an `Agent` subagent with `mode: "bypassPermissions"`, passing the phase body verbatim.
- Phases routed to **Dual** (e.g., security_review on `--engine auto`): spawn both in parallel; orchestrator merges findings.
- `--engine claude` forces all phases to Claude. `--engine codex` forces implementation to Codex, orchestration/Chrome MCP stays Claude. `--engine auto` (default) uses the routing table.

On Codex-ping failure, silent fallback to `--engine claude` per `<autonomy_contract>`.
</engine_routing_convention>

<post_eval_invariant>
Once `state.eval_passed_sha` is non-null (PHASE 2 returned PASS or PASS_WITH_ISSUES at least once), the following phases run **findings-only** — they emit `.findings.jsonl` + `.log.md` but do NOT write code or commit: SIMPLIFY, REVIEW, CHALLENGE, SECURITY REVIEW, CLEAN. If any of these emit NEEDS_WORK/BLOCKED verdicts, the orchestrator routes the findings to PHASE 2.5 (UNIFIED FIX LOOP). After the fix, EVALUATE re-runs — all semantic changes verify through EVAL.

DOCS (PHASE 7) is the only post-EVAL phase allowed to commit, and only for doc files (`*.md` and YAML frontmatter).

**Orchestrator enforcement (per-phase, NOT cumulative)**: `eval_passed_sha` is an activation marker, not the diff baseline. Before each post-EVAL phase starts, orchestrator captures `phase_pre_sha = git rev-parse HEAD` and stores it at `state.phases.<phase>.pre_sha`. After the phase's subagent completes, orchestrator runs `git diff --name-only <phase_pre_sha>` — the diff of **only what this phase touched**, not everything since EVAL first passed. If non-doc files appear:
- Phase is SIMPLIFY/REVIEW/CHALLENGE/SECURITY/CLEAN (findings-only) → `git reset --hard <phase_pre_sha>`, emit finding `rule_id: "invariant.post-eval-code-mutation"` + `severity: HIGH` into a synthetic `.devlyn/invariant.findings.jsonl`, route to PHASE 2.5 with `triggered_by: "<phase>"`.
- Phase is DOCS → same check, but against the doc-file allowlist; non-allowlisted paths trigger the revert-and-find flow.

This per-phase baseline is the correct reference because fix-loop commits between one post-EVAL phase and the next are legitimate (they were already re-EVALed) — they only become part of the baseline for whichever post-EVAL phase runs next. Using `eval_passed_sha` as the cumulative baseline (as the earlier draft of this invariant did) would falsely attribute fix-loop commits to the current phase.

Doc-file allowlist (for DOCS): `*.md`, `.mdx`, files under `docs/`, `README*`, `CHANGELOG*`, `CLAUDE.md`, spec files under `docs/roadmap/phase-*/`, frontmatter in those files. Any other path triggers the revert-and-find flow.
</post_eval_invariant>

## PHASE 0: PARSE + PREFLIGHT + ROUTE

1. **Parse flags** from `<pipeline_config>`:
   - `--max-rounds N` (4)
   - `--route MODE` (auto) — per `references/pipeline-routing.md`
   - `--engine MODE` (auto) — per `references/engine-routing.md`
   - `--bypass <phase>[,<phase>...]` — skip specific phases. Valid: `build-gate`, `browser`, `simplify`, `review`, `challenge`, `security`, `clean`, `docs`. Deprecated aliases `--skip-*` and `--security-review skip` still work; log `deprecated flag — use --bypass` once on use.
   - `--build-gate MODE` (auto) — `auto` / `strict` / `no-docker`.

2. **Engine pre-flight** (unless `--engine claude`): call `mcp__codex-cli__ping`. On failure, silent fallback to `--engine claude`, log `engine downgraded`. Never prompt the user.

3. **Initialize `pipeline.state.json`** per `references/pipeline-state.md`:
   - `version: "1.1"`
   - `run_id: "ar-$(date -u +%Y%m%dT%H%M%SZ)-<12-hex>"` (UUIDv7 short or `openssl rand -hex 6`)
   - `started_at`, `engine`, `base_ref.{branch, sha}`, `rounds.max_rounds`
   - `eval_passed_sha: null`
   - `route.bypasses: [<parsed from --bypass>]`
   - Empty `phases`, `criteria`, `route.selected`.

4. **Spec preflight** (if `<pipeline_config>` contains a path matching `docs/roadmap/phase-\d+/[^\s"'`)]+\.md`):
   - Read the spec. If missing → `BLOCKED`.
   - Verify internal dependencies: each entry under `## Dependencies → Internal` → find `docs/roadmap/phase-*/[id]-*.md`, check `status: done`. Any unmet dep → `BLOCKED`.
   - Populate `state.source`: `type: "spec"`, `spec_path`, `spec_sha256 = sha256(spec)`, `criteria_anchors: ["spec://requirements", "spec://out-of-scope", "spec://verification", "spec://constraints", "spec://architecture-notes", "spec://dependencies"]`.
   - Populate `state.criteria[]`: one per `- [ ]` in `## Requirements`, `status: pending`.

   If no spec path found:
   - `source.type: "generated"`, `source.criteria_path: ".devlyn/criteria.generated.md"` (PHASE 1 creates it), `criteria_anchors: ["criteria.generated://requirements", "criteria.generated://out-of-scope", "criteria.generated://verification"]`, `criteria: []`.

5. **Compute Stage A route** per `references/pipeline-routing.md#stage-a`. Write to `state.route.{selected, user_override, stage_a}`.

6. **Announce** (single line):
```
Auto-resolve starting — run <run_id> — task: <desc>
Engine: <engine>, Route: <selected> (<stage_a_reasons>), Bypasses: <bypasses|none>, Max rounds: <N>
```

## PHASE 1: BUILD

**Engine**: BUILD row of routing table. Spawn per `<engine_routing_convention>`. Agent prompt body: **`references/phases/phase-1-build.md`** — read it, paste it verbatim into the agent prompt, and append the task description at the bottom.

**After the agent completes**:
1. Verify `criteria[]` has ≥1 entry with `status != "pending"`. If not, re-spawn with an explicit reminder.
2. `git diff --stat` — if no changes, stop with failure.
3. Checkpoint: `git add -A && git commit -m "chore(pipeline): phase 1 — build complete"`.

## PHASE 1.4: BUILD GATE

Skip if `build-gate` in `state.route.bypasses` or `--build-gate skip` passed. Deterministic — same commands CI/Docker/production run.

Spawn a Claude `Agent` with `mode: "bypassPermissions"`. Prompt: "Read `references/build-gate.md` (detection matrix, commands, package manager, monorepo, strict, Docker) and `references/findings-schema.md` (output format). Run all matched gates. Apply strict flags if `--build-gate strict` OR `state.route.selected == "strict"`. Run Docker unless `--build-gate no-docker`. Emit `.devlyn/build_gate.findings.jsonl` + `.devlyn/build_gate.log.md`; update `state.phases.build_gate`."

**After the agent completes**:
1. **Inject fingerprints** into `build_gate.findings.jsonl` per `references/findings-schema.md`.
2. Read `state.phases.build_gate.verdict`.
3. **Stage B routing** (only if `verdict == "PASS"` and `state.route.user_override == false`): apply the escalation rules from `references/pipeline-routing.md#stage-b`. Gather signals: diff files, diff lines, risk keywords in diff content, API surface, tests absent, cross-boundary. Apply the escalation rules from pipeline-routing.md. Write `state.route.stage_b.{at, escalated_from, reasons}` on escalation.
4. Branch: `PASS` → PHASE 1.5; `FAIL` → PHASE 2.5 with `triggered_by: "build_gate"`.

## PHASE 1.5: BROWSER VALIDATE (conditional)

Skip if `browser` in `state.route.bypasses`. Check relevance: `git diff --name-only <state.base_ref.sha>` for `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.html`, `page.*`, `layout.*`, `route.*`. None → skip with note.

Spawn a Claude `Agent` with `mode: "bypassPermissions"`. Prompt: "Read `.claude/skills/devlyn:browser-validate/SKILL.md` for the tiered browser workflow (Chrome MCP → Playwright → curl) and `references/findings-schema.md` for output format. Start the dev server, test the implemented feature end-to-end against `pipeline.state.json:criteria[]`, leave the server running (`--keep-server`). Emit `.devlyn/browser_validate.findings.jsonl` + `.devlyn/browser_validate.log.md`; update `state.phases.browser_validate`. Verdict: `PASS` / `PASS_WITH_ISSUES` / `PARTIALLY_VERIFIED` / `NEEDS_WORK` / `BLOCKED`."

**After the agent completes**:
1. **Inject fingerprints**.
2. **Sanity check**: if verdict claims `PASS`/`PASS_WITH_ISSUES` but log shows zero screenshots AND zero page navigations, treat as unverified — re-run at `--tier 2` (Playwright) or `--tier 3` (HTTP smoke). A code-level verdict is not browser validation.
3. Branch: `PASS`/`PASS_WITH_ISSUES`/`PARTIALLY_VERIFIED` → PHASE 2 (flag partial coverage in state.json note if partial); `NEEDS_WORK`/`BLOCKED` → PHASE 2.5 with `triggered_by: "browser_validate"`.

## PHASE 2: EVALUATE

**Engine**: EVALUATE row — always Claude (GAN dynamic when BUILD was Codex). Spawn per `<engine_routing_convention>`. Agent prompt body: **`references/phases/phase-2-evaluate.md`**.

**After the agent completes**:
1. **Inject fingerprints** into `evaluate.findings.jsonl`.
2. Read `state.phases.evaluate.verdict`.
3. **If first-time PASS or PASS_WITH_ISSUES** and `state.eval_passed_sha == null`: set `state.eval_passed_sha = git rev-parse HEAD`. This activates `<post_eval_invariant>`.
4. Branch:
   - `PASS` → next phase per route (SIMPLIFY for standard/strict; FINAL REPORT for fast).
   - `PASS_WITH_ISSUES` → **terminal for this phase** (LOW-only findings do not trigger fix loop; they are logged and proceed). Move to next phase per route. `state.eval_passed_sha` set as above.
   - `NEEDS_WORK` / `BLOCKED` → PHASE 2.5 with `triggered_by: "evaluate"`.

## PHASE 2.5: UNIFIED FIX LOOP

Single fix loop for every trigger (build_gate / browser_validate / evaluate / challenge / simplify / review / security_review / clean). `state.rounds.global` is the shared counter; every entry increments it.

**Exhaustion check first**: if `state.rounds.global >= state.rounds.max_rounds`, apply per-trigger exhaustion from `references/pipeline-routing.md#--max-rounds-exhaustion`:
- `build_gate` / `browser_validate` → **halt** — skip to PHASE 8 with exhaustion banner.
- everything else → **proceed_with_warning** — skip to next phase per route; final report shows `EVAL EXHAUSTED` / etc. banner.

**Fix-batch packet assembly** (orchestrator, before spawn): read the trigger's `.findings.jsonl` (plus browser_validate if `triggered_by == "browser_validate"` or `"evaluate"` and browser also had open findings — see pipeline-routing.md), filter `status == "open"`, write `.devlyn/fix-batch.round-<N>.json`:
```json
{
  "round": <N>, "max_rounds": <state.rounds.max_rounds>,
  "base_ref_sha": "<state.base_ref.sha>",
  "criteria_source": "<state.source.spec_path or criteria_path>",
  "triggered_by": "<trigger phase>",
  "findings": [ /* minimal: id, rule_id, severity, file, line, message, fix_hint, criterion_ref, partial_fingerprints */ ],
  "failed_criteria": ["<C ids>"],
  "acceptance": {"build_gate_cmd": "<from build-gate log>", "test_cmd": "<pnpm test/cargo test/etc>"}
}
```

**Engine**: FIX LOOP row (Codex on `auto`/`codex`, Claude on `claude`). Use a fresh Codex call each round (no `sessionId` reuse).

Spawn per `<engine_routing_convention>`. Agent prompt (inline — short enough): "Read `.devlyn/fix-batch.round-<N>.json` — contains the open, blocking findings from <triggered_by>. Fix every listed entry at the root cause. Criteria live at `pipeline.state.json:criteria[]` (text at `source.spec_path` / `source.criteria_path`) — fixes must still satisfy them; do not weaken criteria. For each finding: read the referenced `file:line`, understand the issue, implement the fix. No workarounds — no `any`, `@ts-ignore`, silent catches. Run tests after fixing. Raw failure detail: `.devlyn/build_gate.log.md` / `.devlyn/browser_validate.log.md`. When a previously-failed criterion is now satisfied, update its entry: clear `failed_by_finding_ids`, set `status: "implemented"`, add `evidence`."

**After the agent completes**:
1. Checkpoint: `git add -A && git commit -m "chore(pipeline): fix round <N> (<triggered_by>)"`.
2. Increment `state.rounds.global`.
3. Route back:
   - `triggered_by: "build_gate"` → PHASE 1.4 (re-run gate).
   - `triggered_by: "browser_validate"` → PHASE 1.5 (re-validate).
   - `triggered_by: "evaluate" | "challenge" | "simplify" | "review" | "security_review" | "clean"` → **PHASE 2 (re-EVALUATE)**. This enforces `<post_eval_invariant>`: all post-EVAL findings come back through EVAL.

## PHASE 3: SIMPLIFY (findings-only, route-gated)

Skip if `state.route.selected == "fast"` OR `simplify` in `state.route.bypasses`.

Spawn a Claude `Agent` with `mode: "bypassPermissions"`. Prompt: "Review recently changed files (`git diff <state.base_ref.sha>`). Look for: code that could reuse existing utilities, unclear naming, unnecessary complexity, redundant operations. **Do NOT write code.** Emit `.devlyn/simplify.findings.jsonl` with `rule_id` like `quality.duplication`, `quality.over-abstraction`, `quality.unclear-naming`; one line per finding; severities LOW–HIGH. Plus `.devlyn/simplify.log.md` summary. Update `state.phases.simplify`. Verdict: `PASS` (zero findings), `PASS_WITH_ISSUES` (LOW only), `NEEDS_WORK` (MEDIUM+HIGH), `BLOCKED` (any CRITICAL)."

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` and store at `state.phases.simplify.pre_sha`.

**After the agent completes**:
1. Inject fingerprints.
2. Enforce `<post_eval_invariant>`: `git diff --name-only <phase_pre_sha>` — non-empty means the subagent ignored the findings-only contract. `git reset --hard <phase_pre_sha>`, emit `invariant.post-eval-code-mutation` finding, route to PHASE 2.5.
3. Branch: `PASS`/`PASS_WITH_ISSUES` → PHASE 4 (or FINAL REPORT per route); `NEEDS_WORK`/`BLOCKED` → PHASE 2.5 with `triggered_by: "simplify"`.

## PHASE 4: REVIEW (findings-only, strict-only)

Skip if `state.route.selected != "strict"` OR `review` in `state.route.bypasses`.

**Engine**: REVIEW (team) per `references/engine-routing.md#team-review-roles`. Dual roles run both models in parallel; orchestrator merges.

Spawn a Claude `Agent` with `mode: "bypassPermissions"`. Prompt: "Assemble a review team via `TeamCreate` with: security-reviewer, quality-reviewer, test-analyst. Add ux-reviewer/performance-reviewer/api-reviewer based on changes. Per-role engine routing: see `references/engine-routing.md`. Each reviewer reports findings with `file:line` + severity + confidence. **Do NOT write code.** Synthesize into `.devlyn/review.findings.jsonl` + `.devlyn/review.log.md`. Clean up team. Update `state.phases.review`."

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` and store at `state.phases.review.pre_sha`.

**After the agent completes**:
1. Inject fingerprints.
2. Enforce `<post_eval_invariant>`: `git diff --name-only <phase_pre_sha>` — non-empty → revert + emit invariant finding + route to fix loop.
3. Branch per verdict (same taxonomy as SIMPLIFY). NEEDS_WORK/BLOCKED → PHASE 2.5 with `triggered_by: "review"`.

## PHASE 4.5: CHALLENGE (findings-only, route-gated)

Skip if `state.route.selected == "fast"` OR `challenge` in `state.route.bypasses`.

**Engine**: CHALLENGE row — always Claude. Spawn per `<engine_routing_convention>`. Agent prompt body: **`references/phases/phase-4.5-challenge.md`**.

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` and store at `state.phases.challenge.pre_sha`.

**After the agent completes**:
1. Inject fingerprints.
2. Enforce `<post_eval_invariant>`: `git diff --name-only <phase_pre_sha>` — non-empty → revert + emit invariant finding + route to fix loop.
3. Branch: `PASS` → PHASE 5; `NEEDS_WORK` → PHASE 2.5 with `triggered_by: "challenge"`.

## PHASE 5: SECURITY REVIEW (findings-only, conditional)

Skip if `security` in `state.route.bypasses`. Otherwise:
- `state.route.selected == "strict"` → run (mandatory).
- `state.route.selected == "fast"` → skip (Stage A/B would have escalated if risk detected).
- `state.route.selected == "standard"` → auto-detect: `git diff --name-only` for security-sensitive files OR `git diff` for `API_KEY|SECRET|TOKEN|PASSWORD|PRIVATE_KEY|Bearer|jwt|bcrypt|crypto|env\.|process\.env`. Any match → run.

**Engine**: SECURITY row — Dual on `auto`. Spawn per `<engine_routing_convention>`. Agent prompt body: **`references/phases/phase-5-security.md`**.

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` and store at `state.phases.security_review.pre_sha`.

**After the agent completes**:
1. Inject fingerprints.
2. Enforce `<post_eval_invariant>`: `git diff --name-only <phase_pre_sha>` — non-empty → revert + emit invariant finding + route to fix loop.
3. Branch per verdict. `NEEDS_WORK`/`BLOCKED` → PHASE 2.5 with `triggered_by: "security_review"`.

## PHASE 6: CLEAN (findings-only, strict-only)

Skip if `state.route.selected != "strict"` OR `clean` in `state.route.bypasses`.

Spawn a Claude `Agent` with `mode: "bypassPermissions"`. Prompt: "Scan recently changed files (`git diff <state.base_ref.sha>`) for dead code, unused imports, unreachable paths, unused variables, dependencies in package.json no longer imported. **Do NOT write code.** Emit `.devlyn/clean.findings.jsonl` with `rule_id` like `hygiene.dead-code`, `hygiene.unused-import`, `hygiene.unused-dep` (usually LOW, sometimes MEDIUM) + `.devlyn/clean.log.md`. Update `state.phases.clean`."

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` and store at `state.phases.clean.pre_sha`.

**After the agent completes**:
1. Inject fingerprints.
2. Enforce `<post_eval_invariant>`: `git diff --name-only <phase_pre_sha>` — non-empty → revert + emit invariant finding + route to fix loop.
3. Branch per verdict. `NEEDS_WORK`/`BLOCKED` → PHASE 2.5 with `triggered_by: "clean"`.

## PHASE 7: DOCS (doc-file mutations only)

Skip if `docs` in `state.route.bypasses` OR `state.route.selected == "fast"`.

Spawn a Claude `Agent` with `mode: "bypassPermissions"`. Include the original task description. Prompt: "You have two jobs:

**Job 1 — Roadmap sync**: If the task matched `docs/roadmap/phase-\d+/[^\s\"']+\.md`, and `git diff <state.base_ref.sha> --stat` touches non-doc files:
1. Read the spec. If `status: done` already, skip to Job 2.
2. Set `status: done` in frontmatter + `completed: <today>`. Do not touch body.
3. Update `docs/ROADMAP.md`: find the row whose `#` column matches the spec id; change Status to `Done`.
4. If the phase is now fully Done: archive the phase block into a `## Completed <details>` block at the bottom of ROADMAP.md (format per `devlyn:ideate#context-archiving`). Item spec files stay on disk.

**Job 2 — General doc sync**: Update docs referencing changed APIs/features/behaviors. Use `git log --oneline -20` + `git diff <state.base_ref.sha>`. Preserve forward-looking content (future plans, visions, open questions).

**Safety**: never flip a spec `done` without a non-empty non-doc diff; never flip multiple specs in one run; never touch files outside the doc-file allowlist (`*.md`, `.mdx`, `docs/`, `README*`, `CHANGELOG*`, `CLAUDE.md`, frontmatter in specs)."

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` and store at `state.phases.docs.pre_sha`.

**After the agent completes**:
1. Enforce the doc-file allowlist: `git diff --name-only <phase_pre_sha>` — any path outside the doc-file allowlist (listed in `<post_eval_invariant>`) → `git reset --hard <phase_pre_sha>`, emit `invariant.post-eval-code-mutation` finding, route to PHASE 2.5 with `triggered_by: "docs"`.
2. If allowlist honored and there are changes: `git add -A && git commit -m "chore(pipeline): docs updated"`.

## PHASE 8: FINAL REPORT + ARCHIVE

1. **Terminal verdict** per `references/pipeline-routing.md#terminal-state-algorithm`. Scan all `<phase>.findings.jsonl` for `status == "open"` findings and apply the precedence table.

2. **Render report**:
```
### Auto-Resolve Complete — run <run_id>

Task: <original task>
Engine: <engine> (downgraded: <reason or no>)
Route: <selected> (user_override: <t/f>)
  Stage A: <reasons>
  Stage B: <no escalation | escalated from X — reasons>

Terminal verdict: <PASS / PASS_WITH_ISSUES / NEEDS_WORK / BLOCKED>
<banner if applicable: "⚠ BUILD GATE EXHAUSTED" / "⚠ EVAL EXHAUSTED — open findings: <list file:line>" />

Pipeline summary:
| Phase | Verdict | Notes |
|-------|---------|-------|
| BUILD | <v> | <engine, team on/off> |
| BUILD GATE | <v> | <project types, commands> |
| BROWSER | <v / skipped — no web> | <tier, flow> |
| EVAL (round <N>) | <v> | <finding count by severity> |
| FIX ROUNDS | <N of max> | <triggered_by history> |
| SIMPLIFY | <v / skipped-route / skipped-bypass> | <finding count> |
| REVIEW | <v / skipped> | <finding count> |
| CHALLENGE | <v / skipped> | <finding count> |
| SECURITY | <v / skipped> | <finding count> |
| CLEAN | <v / skipped> | <finding count> |
| DOCS | <completed / skipped> | <specs flipped, roadmap archived> |

Guardrails bypassed: <state.route.bypasses or "none">

Commits: <git log --oneline from state.base_ref.sha>

Audit trail: .devlyn/runs/<run_id>/

Next steps:
- Review: git diff <base_ref.sha>
- Squash: git rebase -i <base_ref.sha>
- Re-run fixes: /devlyn:auto-resolve "<narrower task>"
```

3. **Archive** per `references/pipeline-state.md#archive-contract`: move `.devlyn/pipeline.state.json`, every `<phase>.findings.jsonl` and `<phase>.log.md`, `fix-batch.round-*.json`, and `criteria.generated.md` (if exists) into `.devlyn/runs/<run_id>/`. Acquire `flock .devlyn/runs/.prune.lock`, prune to last 10 directories by lexicographic `run_id` sort (excluding any with `phases.final_report.verdict == null`), release lock.

4. Kill dev server from PHASE 1.5 if still running.
