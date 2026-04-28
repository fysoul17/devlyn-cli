---
name: devlyn:auto-resolve
description: Fully automated build-evaluate-ship pipeline for any task type — bug fixes, new features, refactors, chores. Use this as the default starting point when the user wants hands-free implementation with zero human intervention. Runs a minimal goal-driven loop — build, evaluate, fix, critic, docs — as a single command. Use when the user says "auto resolve", "build this", "implement this feature", "fix this", "run the full pipeline", "refactor this", or wants to walk away and come back to finished work.
---

Orchestrator for the hands-free implementation pipeline. One subagent per phase, file-based handoff, unified fix loop on evaluation feedback until the work passes or `max_rounds` is reached. The orchestrator itself does not write code — it parses input, spawns phases, reads handoff artifacts, runs git commands, branches on verdicts, and emits the final report.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<orchestrator_context>
Long-horizon agentic work. Context auto-compacts — do not stop early on token-budget concerns. All durable state lives in `.devlyn/pipeline.state.json` (control plane: pointers, criteria, verdicts) plus `<phase>.findings.jsonl` + `<phase>.log.md` for phases that emit findings. `state.json` is the **single authoritative verdict source** — branch on `phases.<name>.verdict` directly, never parse artifact files. At PHASE 5, the run's `.devlyn/*` artifacts are **archived** to `.devlyn/runs/<run_id>/` (last 10 kept, best-effort). Schemas: `references/pipeline-state.md`, `references/findings-schema.md`. Best results with `xhigh` reasoning.
</orchestrator_context>

<autonomy_contract>
This pipeline runs hands-free. Measured by how far it gets without human intervention.

1. **Never prompt the user mid-pipeline.** When you'd otherwise ask, pick the safe default, proceed, and log it in the final report.
2. **Codex availability**: on `--engine auto`/`codex`, follow `config/skills/_shared/engine-preflight.md` — check that the `codex` CLI is on PATH. On failure, silently fall back to `--engine claude` and log `engine downgraded: codex-unavailable` in the final report. Do NOT present a menu. Do NOT abort.
3. **Run only the phases defined below, in order.** Doc updates belong in PHASE 4 (DOCS). Don't insert them earlier.
4. **Delegate all file changes to spawned subagents.** Orchestrator actions: parse input, spawn phase agents, read handoff files, run `git`, branch on verdicts, emit report, archive.
5. **Continue by default.** Stop only for: (a) unrecoverable subagent failure, (b) PHASE 1 producing zero code changes, (c) build-gate / browser fix-loop exhausting `max_rounds` (halt → FINAL REPORT). EVAL/CRITIC exhaustion proceeds with warning — never halts.
</autonomy_contract>

<harness_principles>
Sub-agent contract for every phase: read `_shared/runtime-principles.md` (Subtractive-first / Goal-locked / No-workaround / Evidence). Phases routed to Codex receive the contract excerpt inlined in their prompt body (Codex has no filesystem under read-only). Phase-specific operating constraints (state-write protocol, post-EVAL invariant, engine routing) are below; the runtime contract is non-negotiable across all of them.
</harness_principles>

<engine_routing_convention>
Every phase routes to the optimal model per `references/engine-routing.md`:

- Phase prompt bodies (in `references/phases/`) are engine-agnostic.
- Phases routed to **Codex**: shell out to `bash .claude/skills/_shared/codex-monitored.sh` (which wraps `codex exec`) per the canonical flag set in `config/skills/_shared/codex-config.md` and the spawn patterns in `engine-routing.md`. The wrapper closes stdin and emits a heartbeat so long reasoning calls don't starve the outer API stream. No MCP.
- Phases routed to **Claude**: spawn an `Agent` subagent with `mode: "bypassPermissions"`, passing the phase body verbatim.
- Phases routed to **Native** (CRITIC security sub-pass): invoke the native Claude Code `security-review` skill via the Skill tool; normalize its output into `.devlyn/critic.findings.jsonl` per `phase-3-critic.md`.
- `--engine claude` forces all phases to Claude. `--engine codex` forces implementation to Codex, orchestration/Chrome MCP stays Claude. `--engine auto` (default) uses the routing table.
</engine_routing_convention>

<post_eval_invariant>
Once `state.eval_passed_sha` is non-null (PHASE 2 returned PASS or PASS_WITH_ISSUES), the post-EVAL phases (CRITIC, DOCS) run **findings-only / doc-only** — they never write code. DOCS is the only phase allowed to commit after EVAL, and only for doc files.

**Orchestrator enforcement (per-phase, NOT cumulative)**: before each post-EVAL phase, capture `state.phases.<phase>.pre_sha = git rev-parse HEAD`. After the subagent completes, run `git diff --name-only <pre_sha> -- ':!.devlyn/**'`:
- CRITIC (findings-only) → any diff → `git reset --hard <pre_sha>`, emit `rule_id: "invariant.post-eval-code-mutation"` + `severity: HIGH` into `.devlyn/invariant.findings.jsonl`, route to FIX LOOP with `triggered_by: "critic"`.
- DOCS → check against allowlist; non-allowlisted paths trigger the revert-and-find flow.

Per-phase (not cumulative) baseline is correct because fix-loop commits between one post-EVAL phase and the next are legitimate.

Doc-file allowlist (DOCS): `*.md`, `.mdx`, files under `docs/`, `README*`, `CHANGELOG*`, `CLAUDE.md`, frontmatter in spec files under `docs/roadmap/phase-*/`. Any other path triggers revert-and-find.
</post_eval_invariant>

<perf_opt_in>
Optional: pass `--perf` to record per-phase `{wall_ms, tokens, engine, round, triggered_by}` into `state.perf.per_phase` and totals at PHASE 5. Off by default. Harness efficiency claims can be measured when needed; mandatory meta-measurement was retired in v3.4.
</perf_opt_in>

<state_write_protocol>
**Every phase, every round** — orchestrator owns this. Per `references/pipeline-state.md` Write Protocol.

- **Before each phase spawn**: write `state.phases.<name>.{started_at: <ISO-8601 UTC now>, round: state.rounds.global, triggered_by: <"build_gate"|"evaluate"|"critic"|"browser_validate"|null>}`. The phase agent inherits an entry already in the JSON.
- **After each agent returns**: validate `state.phases.<name>.{verdict, completed_at, duration_ms, artifacts}` are populated. If any are missing or null, write them yourself before branching: `verdict` from the agent's reported result; `completed_at = <ISO-8601 UTC now>`; `duration_ms = (completed_at - started_at) in ms`; `artifacts = {findings_file: ".devlyn/<name>.findings.jsonl" if exists, log_file: ".devlyn/<name>.log.md" if exists}`. **Validate before any branching decision** — branching on a null verdict is undefined behavior.
- **Phases this applies to**: `build`, `build_gate`, `browser_validate`, `evaluate`, `critic`, `docs`, `final_report`. (PHASE 0 PARSE creates state.json itself; no separate `phases.parse` entry.)
- **Why this exists**: prompt-body output contracts alone proved insufficient empirically — `build_gate.md` already explicitly listed the four end-fields and the orchestrator still skipped the write on a clean F1 run (iter-0014 evidence). Orchestrator-side validation closes the gap. Side benefit: `phases.final_report.verdict` populated correctly is what guards archive pruning from deleting in-flight runs.
</state_write_protocol>

## PHASE 0: PARSE + PREFLIGHT + ROUTE

1. **Parse flags** from `<pipeline_config>`:
   - `--max-rounds N` (4)
   - `--route MODE` (auto) — per `references/pipeline-routing.md`
   - `--engine MODE` (auto) — per `references/engine-routing.md`
   - `--team` — force team-assembled BUILD even on non-strict routes (default: solo).
   - `--bypass <phase>[,<phase>...]` — skip specific phases. Valid: `build-gate`, `browser`, `critic`, `docs`. Deprecated aliases (`--skip-*`, `--security-review skip`, `--bypass simplify|review|clean|security|challenge`) map to `--bypass critic` where applicable; log `deprecated flag — use --bypass <phase>` once.
   - `--build-gate MODE` (auto) — `auto` / `strict` / `no-docker`.
   - `--perf` — opt in to per-phase timing/token accounting.

2. **Engine pre-flight**: follow `config/skills/_shared/engine-preflight.md`. The downgrade banner surfaces in the final report's Engine line.

3. **Initialize `pipeline.state.json`** per `references/pipeline-state.md`:
   - `version: "1.2"`, `run_id: "ar-$(date -u +%Y%m%dT%H%M%SZ)-<12-hex>"`, `started_at`, `engine`, `base_ref.{branch, sha}`, `rounds.max_rounds`, `eval_passed_sha: null`, `route.bypasses: [...]`, empty `phases`, `criteria`, `route.selected`.

4. **Spec preflight** (if `<pipeline_config>` contains `docs/roadmap/phase-\d+/[^\s"'`)]+\.md`):
   - Read the spec. Missing → `BLOCKED`.
   - Verify internal deps (each entry under `## Dependencies → Internal` resolves to a `status: done` spec). Unmet → `BLOCKED`.
   - Populate `state.source`: `type: "spec"`, `spec_path`, `spec_sha256 = sha256(spec)`, `criteria_anchors: ["spec://requirements", "spec://out-of-scope", "spec://verification", "spec://constraints", "spec://architecture-notes", "spec://dependencies"]`.
   - Populate `state.criteria[]`: one per `- [ ]` in `## Requirements`, `status: pending`.

   No spec path found → `source.type: "generated"`, `source.criteria_path: ".devlyn/criteria.generated.md"` (PHASE 1 creates it), `criteria_anchors: ["criteria.generated://requirements", "criteria.generated://out-of-scope", "criteria.generated://verification"]`, `criteria: []`.

   **iter-0020**: ALSO populate `state.source.fixture_class` from the `BENCH_FIXTURE_CATEGORY` env var AND `state.source.fixture_id` from `BENCH_FIXTURE`, in both cases ONLY when `BENCH_WORKDIR` is also set (benchmark-scoped). When the bench envs are unset, write both fields as `null`. Stable schema; `select_phase_engine.py` keys off `fixture_class`, `coverage_report.py` keys off `fixture_id`.

5. **Compute Stage A route** per `references/pipeline-routing.md#stage-a`. Write to `state.route.{selected, user_override, stage_a}`.

6. **Announce** (single line):
```
Auto-resolve starting — run <run_id> — task: <desc>
Engine: <engine>, Route: <selected> (<stage_a_reasons>), Bypasses: <bypasses|none>, Max rounds: <N>
```

## PHASE 1: BUILD

**Engine** (iter-0020 — code-enforced override, not prompt-only): before the spawn, run `python3 .claude/skills/devlyn:auto-resolve/scripts/select_phase_engine.py --phase build --engine <pipeline_config.engine>`. The script reads `state.source.fixture_class`, applies the `references/engine-routing.md` BUILD row, applies per-fixture-class overrides (currently `e2e → claude`), writes `state.route.engine_overrides.build` if an override fires, and prints the resolved engine name. Use that engine for the spawn (NOT the static table). On any other phase, the static `references/engine-routing.md` table still applies — only BUILD has an iter-0020 override. Prompt body: **`references/phases/phase-1-build.md`** (verbatim) + task description. Spawn per `<engine_routing_convention>` with the engine returned by the selector.

**Team assembly rule** (simplified from v3.2): BUILD spawns as **team** ONLY when `--team` flag passed OR `state.route.selected == "strict"`. Otherwise solo. Keyword-match auto-trigger removed — Claude/Codex base SWE capability is the default.

**State write** (per `<state_write_protocol>`): write `phases.build.started_at` before spawn; after agent returns, validate `phases.build.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching.

**After the agent completes**:
1. Verify `criteria[]` has ≥1 entry with `status != "pending"`. If not, re-spawn with reminder.
2. `git diff --stat` — if no changes, halt with failure.
3. Checkpoint: `git add -A && git commit -m "chore(pipeline): phase 1 — build complete"`.

## PHASE 1.4: BUILD GATE

Skip if `build-gate` in `state.route.bypasses`. Deterministic — same commands CI/Docker/production run.

Spawn Claude `Agent` (`mode: "bypassPermissions"`): "Read `references/build-gate.md` (detection matrix, commands, package manager, monorepo, strict, Docker, **spec literal check**) and `references/findings-schema.md`. Run all matched gates. Apply strict flags if `--build-gate strict` OR `state.route.selected == "strict"`. Run Docker unless `--build-gate no-docker`. **Always run `python3 .claude/skills/devlyn:auto-resolve/scripts/spec-verify-check.py` (iter-0019.6 + iter-0019.8 + iter-0019.9 mechanical output-contract gate). The script self-stages `.devlyn/spec-verify.json` from `pipeline.state.json:source.{spec_path | criteria_path}` by extracting the canonical `## Verification` ` ```json ` block (real-user mode); benchmark mode (`BENCH_WORKDIR` set) trusts a pre-staged contract from `run-fixture.sh` and skips source-extract. Whenever the script writes findings to `.devlyn/spec-verify-findings.jsonl` (CRITICAL `correctness.spec-literal-mismatch` per failed command, or one CRITICAL `correctness.spec-verify-malformed` when the carrier is missing/malformed for a generated source or fails shape validation), concatenate that file onto `.devlyn/build_gate.findings.jsonl` so the fix-loop picks them up. Exit 0 with no findings file is a silent no-op (handwritten spec without the json block — pre-iter-0019.8 contract preserved). Exit 1 means BUILD_GATE verdict should be FAIL.** Emit `.devlyn/build_gate.findings.jsonl` + `.devlyn/build_gate.log.md`; update `state.phases.build_gate`."

**State write** (per `<state_write_protocol>`): write `phases.build_gate.started_at` before spawn; after agent returns, validate `phases.build_gate.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching.

**After the agent completes**:
1. Read `state.phases.build_gate.verdict`.
2. **Stage B LITE** (only if `verdict == "PASS"` AND `state.route.user_override == false`): apply the single escalation rule from `references/pipeline-routing.md#stage-b-lite`. If it fires, write `state.route.stage_b.{at, escalated_from, reasons}`.
3. Branch: `PASS` → PHASE 1.5; `FAIL` → PHASE 2.5 with `triggered_by: "build_gate"`.

## PHASE 1.5: BROWSER VALIDATE (conditional)

Skip if `browser` in `state.route.bypasses`. Skip if `git diff --name-only <state.base_ref.sha>` has no `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.css`, `*.html`, `page.*`, `layout.*`, `route.*` matches.

Spawn Claude `Agent` (`mode: "bypassPermissions"`): "Read `.claude/skills/devlyn:browser-validate/SKILL.md` (tiered Chrome MCP → Playwright → curl) and `references/findings-schema.md`. Start dev server, test the implemented feature end-to-end against `pipeline.state.json:criteria[]`, leave server running (`--keep-server`). Emit `.devlyn/browser_validate.findings.jsonl` + `.devlyn/browser_validate.log.md`; update `state.phases.browser_validate`."

**State write** (per `<state_write_protocol>`): write `phases.browser_validate.started_at` before spawn; after agent returns, validate `phases.browser_validate.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching.

**After the agent completes**:
1. **Sanity check**: if verdict is `PASS`/`PASS_WITH_ISSUES` but log shows zero screenshots AND zero navigations, treat as unverified — re-run at `--tier 2`/`3`. Code-level verdict is not browser validation.
2. Branch: `PASS`/`PASS_WITH_ISSUES`/`PARTIALLY_VERIFIED` → PHASE 2; `NEEDS_WORK`/`BLOCKED` → PHASE 2.5 with `triggered_by: "browser_validate"`.

## PHASE 2: EVALUATE

**Engine**: EVAL row — always Claude. Prompt body: **`references/phases/phase-2-evaluate.md`**.

**State write** (per `<state_write_protocol>`): write `phases.evaluate.started_at` before spawn; after agent returns, validate `phases.evaluate.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching. (`evaluate` is the most-likely populated phase already; still validate.)

**After the agent completes**:
1. Read `state.phases.evaluate.verdict`.
2. **First-time PASS or PASS_WITH_ISSUES** with `state.eval_passed_sha == null` → set `state.eval_passed_sha = git rev-parse HEAD` (activates `<post_eval_invariant>`).
3. Branch:
   - `PASS` → PHASE 3 (CRITIC) per route; `fast` → PHASE 5 (FINAL REPORT).
   - `PASS_WITH_ISSUES` → **terminal for this phase** (LOW-only findings do not re-trigger fix loop). Proceed to next phase.
   - `NEEDS_WORK` / `BLOCKED` → PHASE 2.5 with `triggered_by: "evaluate"`.

## PHASE 2.5: UNIFIED FIX LOOP

Single fix loop for every trigger (`build_gate` / `browser_validate` / `evaluate` / `critic`). `state.rounds.global` shared counter.

**Exhaustion check first**: if `state.rounds.global >= state.rounds.max_rounds`:
- `build_gate` / `browser_validate` → **halt** → PHASE 5 with exhaustion banner.
- `evaluate` / `critic` → **proceed_with_warning** → skip to next phase; final report shows banner.

**Fix-batch packet assembly**: read the trigger's `.findings.jsonl` (plus browser_validate if `triggered_by == "evaluate"` or `"browser_validate"` and browser has open findings — see pipeline-routing.md), filter `status == "open"`, write `.devlyn/fix-batch.round-<N>.json`:
```json
{
  "round": <N>, "max_rounds": <N>, "base_ref_sha": "...", "criteria_source": "...",
  "triggered_by": "<trigger>", "findings": [ /* id, rule_id, severity, file, line, message, fix_hint, criterion_ref */ ],
  "failed_criteria": ["<C ids>"], "acceptance": {"build_gate_cmd": "...", "test_cmd": "..."}
}
```

**Engine**: FIX LOOP row (Codex on `auto`/`codex`, Claude on `claude`). Fresh Codex call each round (no `sessionId` reuse).

Spawn per `<engine_routing_convention>`. Prompt:

> Read `.devlyn/fix-batch.round-<N>.json` and `pipeline.state.json`.
>
> **First, re-ground on the contract.** Open `source.spec_path` (or `source.criteria_path`) and read the sections/anchors referenced by each finding's `criterion_ref`. **Spec/criteria are higher authority than findings** — do not narrow or reinterpret required behavior to satisfy a finding. If a finding hint conflicts with explicit spec text (e.g., a glob/pattern like `**/SKILL.md`, a cardinality, a flag's documented behavior), preserve the spec semantics and fix only the implementation defect. Non-contradictory, backward-compatible enhancements that preserve required default behavior are allowed (e.g., respecting `NO_COLOR` while still defaulting to colored when unset). If a finding **truly contradicts** the spec, halt that finding's fix, log the conflict in `.devlyn/fix-batch.round-<N>.log.md`, and leave the finding `open` — the conflict surfaces in the final report rather than silently narrowing the contract.
>
> **Then fix every listed finding at the root cause.** If multiple findings touch the same symbol, produce **one consolidated change**. Prefer editing/replacing existing code over adding new machinery; **do not leave parallel near-duplicate helpers/functions**. When return-shape pressure appears (one finding needs a richer return value than another), broaden the existing helper's return object — don't create a second variant.
>
> Read each referenced `file:line`, implement the fix, run tests. **Runtime principles bind every fix** (read `_shared/runtime-principles.md`; if you are routed to Codex, this contract: Subtractive-first — prefer deletion / consolidated change over new machinery; Goal-locked — fix only the listed findings, do not silently expand scope to adjacent code; No-workaround — no `any`, `@ts-ignore`, silent catches, hardcoded values, helper scripts that bypass root cause; Evidence — every fix anchored at file:line). Raw failure detail: `.devlyn/build_gate.log.md` / `.devlyn/browser_validate.log.md`. When a previously-failed criterion is now satisfied, clear `failed_by_finding_ids`, set `status: "implemented"`, append an `evidence` record.

**After the agent completes**:
1. Checkpoint: `git add -A && git commit -m "chore(pipeline): fix round <N> (<triggered_by>)"`.
2. Increment `state.rounds.global`.
3. Route back: `build_gate` → PHASE 1.4; `browser_validate` → PHASE 1.5; **`evaluate` / `critic` → PHASE 2 (re-EVAL)**. All post-EVAL findings flow back through EVAL.
4. **After re-EVAL returns PASS/PASS_WITH_ISSUES with `triggered_by == "critic"`**: re-run PHASE 3 CRITIC once before proceeding to DOCS. This verifies the fix didn't introduce new design/security issues the first CRITIC would have caught. Subsequent fix-loop rounds triggered from this re-CRITIC follow the same rule (bounded by `state.rounds.max_rounds`).

## PHASE 3: CRITIC (findings-only, route-gated)

Skip if `state.route.selected == "fast"` OR `critic` in `state.route.bypasses`.

One post-EVAL critic pass with two sub-concerns:
- **Design sub-pass** — "would a staff engineer block this PR?" (cold read, any finding → `NEEDS_WORK`). Always Claude.
- **Security sub-pass** — delegated to the native Claude Code `security-review` skill on every engine. Findings-only (post-EVAL invariant compatible); covers OWASP surface + dependency audit (native reads lockfiles). No Dual-model cost. Orchestrator normalizes the native output into `.devlyn/critic.findings.jsonl` per `phase-3-critic.md` Sub-pass 2. If the native skill is unavailable or fails, security sub-verdict is `BLOCKED` with `security.review-failed` — no fallback to a custom pass.

Hygiene concerns (unused imports, dead code) live in EVAL's `hygiene.*` findings at LOW severity, not a separate sub-pass here.

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` → `state.phases.critic.pre_sha`.

**State write** (per `<state_write_protocol>`): write `phases.critic.started_at` before spawn (alongside `pre_sha` capture); after agent returns, validate `phases.critic.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching. CRITIC's verdict is the WORSE of `sub_verdicts.{design, security}`, both of which the agent writes.

**Spawn**: per `<engine_routing_convention>`. Prompt body: **`references/phases/phase-3-critic.md`**.

**After the agent completes**:
1. Enforce `<post_eval_invariant>`: `git diff --name-only <phase_pre_sha> -- ':!.devlyn/**'` — non-empty → revert + emit invariant finding + route to fix loop.
2. Read `state.phases.critic.verdict` (WORSE of design/security sub-verdicts):
   - `PASS` → PHASE 4.
   - `PASS_WITH_ISSUES` (security LOW only; design must be zero) → terminal; PHASE 4.
   - `NEEDS_WORK` / `BLOCKED` → PHASE 2.5 with `triggered_by: "critic"`.

## PHASE 4: DOCS (doc-file mutations only)

Skip if `docs` in `state.route.bypasses` OR `state.route.selected == "fast"`.

Spawn Claude `Agent` (`mode: "bypassPermissions"`). Include original task description. Prompt: "Two jobs:

**Job 1 — Roadmap sync**: if task matched `docs/roadmap/phase-\d+/[^\s\"']+\.md` and `git diff <state.base_ref.sha> --stat` touches non-doc files:
1. Read the spec. If `status: done` already, skip to Job 2.
2. Set `status: done` + `completed: <today>` in frontmatter. Do not touch body.
3. Update `docs/ROADMAP.md`: find row matching spec id; change Status to `Done`.
4. If phase now fully Done: archive to `## Completed <details>` block at bottom (format per `devlyn:ideate#context-archiving`). Item spec files stay on disk.

**Job 2 — Named-doc sync (scoped)**: update only doc files whose filename appears verbatim in the spec's Requirements or Constraints text (e.g. the spec literally says "Update `CLAUDE.md` section X"). If the filename isn't written in the spec, don't touch it. General doc maintenance — README.md feature lists, CHANGELOG.md entries, package.json version bumps, API surface writeups — is `/devlyn:update-docs`'s responsibility (a standalone, manually-invoked skill). Never widen DOCS phase beyond the verbatim-named set.

**Safety**: never flip a spec `done` without a non-empty non-doc diff; never flip multiple specs in one run; never touch files outside the doc-file allowlist; Job 2 never writes a file the spec didn't name verbatim.

**Runtime principles bind doc edits too** (read `_shared/runtime-principles.md`; Codex routings get this contract: Goal-locked — never widen DOCS beyond Job 1 + Job 2 verbatim-named scope, even if you notice unrelated stale docs; Subtractive-first — prefer trimming stale sentences over adding new ones; Evidence — every doc edit must be tied to a non-empty non-doc diff or a verbatim-named spec mention)."

**Before spawn**: capture `phase_pre_sha = git rev-parse HEAD` → `state.phases.docs.pre_sha`.

**State write** (per `<state_write_protocol>`): write `phases.docs.started_at` before spawn (alongside `pre_sha` capture); after agent returns, validate `phases.docs.{verdict, completed_at, duration_ms, artifacts}` populated and write any missing fields before branching.

**After the agent completes**:
1. Enforce allowlist: `git diff --name-only <phase_pre_sha> -- ':!.devlyn/**'` — any non-allowlisted path → revert + emit `invariant.post-eval-code-mutation` + route to PHASE 2.5 with `triggered_by: "docs"`.
2. If allowlist honored and diff non-empty: `git add -A && git commit -m "chore(pipeline): docs updated"`.

## PHASE 5: FINAL REPORT + ARCHIVE

**State write** (per `<state_write_protocol>`): write `phases.final_report.started_at` at the very top of this phase. Steps 1-2 below populate `verdict` (from terminal_verdict.py) and the rendered report; **before step 3 (Archive)**, write `phases.final_report.{verdict, completed_at, duration_ms}`. The archive script's prune logic at `pipeline-state.md:179` skips runs whose `phases.final_report.verdict == null`, treating them as "in flight" indefinitely; populating it correctly is what unblocks pruning.

1. **Terminal verdict**: run `python3 .claude/skills/devlyn:auto-resolve/scripts/terminal_verdict.py` (implements the precedence in `references/pipeline-routing.md#terminal-state-algorithm`; prints verdict, exits 0/1/2/3 for PASS/PASS_WITH_ISSUES/NEEDS_WORK/BLOCKED).

2. **Render report** per the exact shape in `references/final-report-template.md` — required section order, banner rules, engine-line contract, and summary table layout all live there. Fill placeholders from `pipeline.state.json`.

3. **Coverage report** (iter-0020): run `python3 .claude/skills/devlyn:auto-resolve/scripts/coverage_report.py`. Emits `.devlyn/coverage.json` per the schema in that script's docstring — proof artifact for hard-acceptance #4. Per-fixture invariant: every applicable iter-0020+ changed route must have fired. Failures (`applicable_missed` non-empty) indicate a router bug. Suite-level aggregation across all fixtures' coverage.json files proves "every changed route was exercised by at least one fixture."

4. **Archive**: run `python3 .claude/skills/devlyn:auto-resolve/scripts/archive_run.py` (implements `references/pipeline-state.md#archive-contract`; moves per-run artifacts into `.devlyn/runs/<run_id>/`, best-effort prunes to last 10 completed runs). The script reads `phases.final_report.verdict` for prune-safety, so the state write above must complete first.

5. Kill dev server from PHASE 1.5 if still running.
