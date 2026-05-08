---
name: devlyn:resolve
description: Hands-free pipeline for any coding task — bug fix, feature, refactor, debug, modify, PR review. Free-form goal or formal spec input. Plan → Implement → Build-gate → Cleanup → Verify (fresh subagent, findings-only). Mechanical-first verification; pair-mode is gated in Verify. Use when the user says "resolve this", "fix this", "implement this", "refactor this", "debug this", "review this PR", or wants hands-off completion.
---

Orchestrator for the 2-skill harness pipeline. One subagent per phase; file-based handoff via `.devlyn/pipeline.state.json`. VERIFY spawns a fresh-context subagent so independence is structural — not advisory.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<orchestrator_context>
Long-horizon agentic work; context auto-compacts. State lives in `.devlyn/pipeline.state.json` — the single authoritative verdict source. Schemas in `references/state-schema.md`. Best at `xhigh` effort.
</orchestrator_context>

<autonomy_contract>
Hands-free. Measured by how far we get without human intervention.

1. Do not prompt the user mid-pipeline. When tempted to ask, pick the safe default, proceed, and log it in the final report.
2. Codex availability: on `--engine auto`/`codex`, follow `_shared/engine-preflight.md`. On failure, silently fall back to Claude and log `engine downgraded: codex-unavailable` in the final report.
3. Phases run in declared order. No extra phases.
4. Orchestrator does not write code. It parses input, spawns phases, reads state, branches on verdicts, emits the report.
5. Continue by default. Halt only on (a) unrecoverable subagent failure, (b) IMPLEMENT producing zero code changes, (c) BUILD_GATE or VERIFY fix-loop exhausting `max_rounds`.
</autonomy_contract>

<harness_principles>
Every phase reads `_shared/runtime-principles.md` (Subtractive-first / Goal-locked / No-workaround / Evidence). Codex routings receive the contract excerpt inlined in their prompt body.
</harness_principles>

<engine_routing>
Each phase routes to an engine and prepends the per-engine adapter header from `_shared/adapters/<model>.md` to the canonical phase body. Adapter is the per-model delta (Anthropic Opus 4.7 guide for Claude, OpenAI GPT-5.5 guide for Codex). Canonical body is engine-agnostic.

- Claude phases: spawn `Agent` (`mode: "bypassPermissions"`); prompt = adapter-header + canonical-body + task-context.
- Codex phases: shell out via `bash _shared/codex-monitored.sh` with the same compounded prompt. The wrapper closes stdin and emits a heartbeat. No MCP.
- Default engine: Claude. `--engine codex` routes IMPLEMENT to Codex; orchestration stays Claude. Pair-mode (only in VERIFY/JUDGE) selects a different engine for the fresh subagent than IMPLEMENT used.
- Multi-LLM evolution: when a new model adapter ships in `_shared/adapters/`, that engine becomes selectable via `--engine <model>` without further skill changes (NORTH-STAR.md "Multi-LLM evolution direction").
</engine_routing>

<modes>
Three input shapes:

1. **Free-form**: `/devlyn:resolve "fix the login bug"`. PHASE 0 runs the complexity classifier and either proceeds with an internal mini-spec (trivial), drafts focused questions for in-prompt resolution (medium), or escalates to `/devlyn:ideate` (large/ambiguous). No mid-pipeline prompts in any branch.
2. **Spec**: `/devlyn:resolve --spec docs/roadmap/phase-N/X.md`. Spec is read-only. Verification commands pre-staged from spec's `## Verification` block.
3. **Verify-only**: `/devlyn:resolve --verify-only <diff-or-PR-ref> --spec <path>`. Skips PHASE 1-4. Runs PHASE 5 (VERIFY) on the supplied diff against the spec.
</modes>

<post_implement_invariant>
Once `state.implement_passed_sha` is non-null (PHASE 2 returned and produced a diff), the post-IMPLEMENT phases (CLEANUP, VERIFY) operate under structural constraints:

- CLEANUP may only mutate files in the cleanup allowlist (tooling artifacts, dead code added by this diff, doc references this diff invalidated). Other paths trigger revert.
- VERIFY runs in a fresh subagent context with no code-mutation tools. Findings only — never edits files. The fresh-context spawn is the structural guarantee; the prompt body reinforces it but the spawn is what makes independence real.
</post_implement_invariant>

## PHASE 0: PARSE + CLASSIFY + ROUTE

1. Parse flags from `<pipeline_config>`:
   - `--max-rounds N` (default 4) — fix-loop budget shared across BUILD_GATE and VERIFY.
   - `--engine MODE` (default `claude`) — picks the adapter for IMPLEMENT, CLEANUP, and the primary VERIFY judge. It does not disable VERIFY pair-mode; when a VERIFY pair trigger fires, the second judge uses the OTHER engine.
   - `--spec <path>` — switches to spec mode.
   - `--verify-only <ref>` — switches to verify-only mode. Requires `--spec`.
   - `--pair-verify` — force pair-mode JUDGE in PHASE 5 even when not auto-triggered.
   - `--risk-probes` — insert PHASE 1.5 cross-engine probe derivation. The OTHER engine converts visible `## Verification` bullets into bounded executable probes before IMPLEMENT; BUILD_GATE and VERIFY replay them mechanically.
   - `--bypass <phase>[,...]` — skip specific phases. Valid: `build-gate`, `cleanup`. PLAN, IMPLEMENT, VERIFY are non-bypassable.
   - `--perf` — opt in to per-phase timing.

2. Engine pre-flight: follow `_shared/engine-preflight.md`. The downgrade banner surfaces in the final report.

3. Initialize `.devlyn/pipeline.state.json` per `references/state-schema.md`. Set `state.run_id`, `started_at`, `engine`, `base_ref.{branch, sha}`, `rounds.{max_rounds, global: 0}`, `bypasses`, empty `phases`, empty `criteria`.

4. **Mode-specific init**:
   - **Free-form**: read `references/free-form-mode.md`. Run the complexity classifier deterministically (rules over keyword density / file count / spec-shape signals). Set `state.complexity ∈ {trivial, medium, large}`. Trivial: write internal mini-spec to `.devlyn/criteria.generated.md` and proceed. Medium: synthesize a minimal spec from the goal + add 1-2 context anchors from the codebase, write to `.devlyn/criteria.generated.md`, proceed. Large: log `recommend: /devlyn:ideate first` in the final report and either halt (default) or proceed with assumed defaults if `--continue-on-large` flag set.
   - **Spec**: validate spec exists + `## Verification` block parses (run `python3 .claude/skills/_shared/spec-verify-check.py --check <spec-path>` to validate carrier shape). Compute `state.source.spec_sha256`. Stage `.devlyn/spec-verify.json` from the spec's verification block.
   - **Verify-only**: skip to PHASE 5 with `state.source.spec_path` set, the supplied diff captured at `.devlyn/external-diff.patch`.

5. Announce one line: `resolve starting — run <run_id> — engine <engine> — mode <mode> — complexity <complexity-or-na>`.

## PHASE 1: PLAN

Skip in verify-only mode. The heaviest phase by design — spec/criteria define non-negotiable invariants; plan formalizes how the implementation hits them.

Engine: Claude (PLAN-pair is **unmeasured at HEAD** — iter-0033d is the first L1-vs-L2 measurement; iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT PLAN-pair). Prompt body: `references/phases/plan.md`.

Subagent output (writes `.devlyn/plan.md`): file list to touch, risk list (out-of-scope expansions, ambiguous spec sections), acceptance restatement (what `## Verification` actually requires verbatim).

State write: `phases.plan.{started_at, verdict, completed_at, duration_ms}`.

After return:
1. If `.devlyn/plan.md` lists zero files → halt with verdict `BLOCKED:plan-empty`.
2. If risk list flags an out-of-scope expansion the user did not authorize → re-spawn once with the reminder; second fail → halt.

## PHASE 1.5: RISK_PROBES

Skip unless `--risk-probes` is set. This phase is findings-as-executable-checks,
not a second plan and not debate.

Engine: OTHER engine from PHASE 2's selected IMPLEMENT engine. Prompt body:
`references/phases/probe-derive.md`.

Inputs: source spec/criteria, `.devlyn/plan.md`, and repo read/search. Forbidden:
`spec.expected.json`, `.devlyn/spec-verify.json`, `BENCH_FIXTURE_DIR`, hidden
fixture/verifier paths, previous findings, and harness docs unless excerpted.

Output: `.devlyn/risk-probes.jsonl`, 1 to 3 JSONL entries. Each entry must be
one verification command shape plus `id`, `derived_from`, `tags`, and
`tag_evidence`, where `derived_from` is an exact substring of the visible
`## Verification` section. `tag_evidence` must prove high-risk tags with the
evidence markers enforced by `spec-verify-check.py`; a tag-only probe is
malformed.
For high-complexity specs with multiple behavior bullets, at least one probe
must be compound: it must exercise two or more visible verification bullets in a
single command. Empty output is invalid when `--risk-probes` is set.

State write: `phases.probe_derive.{started_at, verdict, completed_at, duration_ms, artifacts}`.

Invocation contract when OTHER engine is Codex:

- Invoke Codex only through the monitored wrapper path in `CODEX_MONITORED_PATH`,
  or `.claude/skills/_shared/codex-monitored.sh` when the env var is absent:
  `bash "$CODEX_MONITORED_PATH" -C "$PWD" --full-auto -c model_reasoning_effort=xhigh "<probe prompt>"`.
- Do not run `codex`, `codex exec`, `/Users/.../codex`, or a plugin-provided
  Codex binary directly. A raw Codex child can outlive the phase and makes the
  benchmark run invalid even if `.devlyn/risk-probes.jsonl` is written.
- Capture wrapper stdout/stderr to `.devlyn/probe-derive.stdout` and
  `.devlyn/probe-derive.stderr`; branch on the wrapper exit code before
  validating `.devlyn/risk-probes.jsonl`.

After return:
1. Run `python3 .claude/skills/_shared/spec-verify-check.py --validate-risk-probes`
   for the artifact boundary before IMPLEMENT; malformed probes halt with
   `BLOCKED:probe-derive-malformed`.
2. IMPLEMENT receives `.devlyn/plan.md` plus `.devlyn/risk-probes.jsonl` as
   concrete acceptance obligations. It must not receive the producer engine's
   commentary or any mention of pair/critic/debate.

## PHASE 2: IMPLEMENT

Skip in verify-only mode. Constrained design judgment within PLAN's invariants. Writes code, tests, and inline doc-comments. No standalone DOCS phase — what the spec licenses is updated here, what it does not is out of scope.

Engine: per `--engine`. Prompt body: `references/phases/implement.md`.

State write: `phases.implement.{started_at, verdict, completed_at, duration_ms}`.

After return:
1. `git diff --stat` — empty diff → halt with `BLOCKED:implement-empty`.
2. Set `state.implement_passed_sha = git rev-parse HEAD` (activates `<post_implement_invariant>`).
3. Checkpoint: `git add -A && git commit -m "chore(pipeline): implement"`.

## PHASE 3: BUILD_GATE

Skip in verify-only mode OR when `build-gate` in `state.bypasses`. Deterministic — same commands CI / Docker / production run.

Spawn Claude `Agent` (`mode: "bypassPermissions"`) with prompt body `references/phases/build-gate.md`. The agent:
1. Detects language/framework via project files (`package.json`, `pyproject.toml`, etc.).
2. Runs language-specific gates (tsc / lint / test).
3. Always runs `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes` (verification_commands literal-match plus `.devlyn/risk-probes.jsonl` when present).
4. If `spec.expected.json.browser_flows` declared OR diff touches web-surface files: invokes the browser runner (Chrome MCP → Playwright → curl tier as available).
5. Emits `.devlyn/build_gate.findings.jsonl` + `.devlyn/build_gate.log.md`.

State write: `phases.build_gate.{started_at, verdict, completed_at, duration_ms, artifacts}`.

Branch:
- `PASS` → PHASE 4.
- `FAIL` → fix loop. Spawn IMPLEMENT-engine agent with the build_gate findings as input. Increment `state.rounds.global`. On second FAIL with `state.rounds.global >= state.rounds.max_rounds` → halt with verdict `BLOCKED:build-gate-exhausted`.

## PHASE 4: CLEANUP

Skip if `cleanup` in `state.bypasses`. Task-scoped pass.

Engine: per `--engine`. Prompt body: `references/phases/cleanup.md`. Allowlist enforced post-spawn:
- Tooling artifacts the spec did not list as deliverables (`test-results/`, `playwright-report/`, `.last-run.json`, coverage HTML).
- Dead code added by this diff (not pre-existing dead code).
- Doc references whose target this diff renamed or removed.

Before spawn: capture `state.phases.cleanup.pre_sha = git rev-parse HEAD`.

State write: `phases.cleanup.{started_at, verdict, completed_at, duration_ms}`.

After return:
1. Run `git diff --name-only <pre_sha>` — any path outside the cleanup allowlist → revert to `pre_sha` and emit `invariant.cleanup-out-of-scope` finding into `.devlyn/cleanup.findings.jsonl`.
2. If allowlist honored and diff non-empty: `git add -A && git commit -m "chore(pipeline): cleanup"`.

## PHASE 5: VERIFY (fresh subagent, findings-only)

Independent quality layer. **Spawned with empty conversation context** — no carry-over from PHASE 1-4. Inputs limited to `spec.md` (or `.devlyn/criteria.generated.md`), `spec.expected.json`, the cumulative diff, and the spec hash. The fresh-context spawn is the structural guarantee of independence; the prompt body reinforces it.

Two sub-phases:

1. **MECHANICAL** (deterministic): re-run `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes` against the post-CLEANUP code (independent of BUILD_GATE's earlier run). Re-scan `spec.expected.json.forbidden_patterns` against the diff. Re-check `required_files` and `forbidden_files`. Emit `.devlyn/verify-mechanical.findings.jsonl`.

2. **JUDGE** (fresh-context Agent): grade the diff against the spec on rubric axes (spec compliance, scope, quality, consistency). Split each Requirement into binding clauses and trace code-order counterexamples; a passing verifier proves only the case it exercises, not neighboring `once` / `regardless` / `duplicate` / auth-order / rollback invariants. Respect scope qualifiers such as `inside a warehouse`, `per resource`, `for this line`, and `after validation`; do not widen a scoped clause into a global invariant, and compose multiple ordering rules in the stated order. For stateful flows, explicitly trace failed-operation rollback and the next entity's state before hunting broader edge cases. For high-complexity specs, construct at least one interaction counterexample that combines ordering/priority with failure handling and state mutation, then execute at least one such scenario through the repo's existing CLI/API/test runner without leaving tracked files behind; one-axis examples and pure mental tracing are insufficient. Default engine = same as IMPLEMENT (solo). Pair-mode (cross-model JUDGE) is eligible only when MECHANICAL has no HIGH/CRITICAL findings; deterministic blockers already decide the verdict and route to the fix loop. Pair-mode fires when eligible and:
   - `--pair-verify` flag set, OR
   - spec frontmatter has `complexity: high`, OR `state.complexity` is `"high"` or `"large"`, OR
   - MECHANICAL emits findings flagged `severity: warning` (not disqualifier — those route to fix loop directly), OR
   - `state.verify.coverage_failed == true` (judge could not exercise a required spec axis from available evidence).

Before spawning JUDGE, compute `pair_trigger = { eligible, reasons[] }` and write it into `state.phases.verify`. If `eligible == true` and `reasons` is non-empty, you MUST spawn the second OTHER-engine judge. Skipping that second judge is a VERIFY contract violation, not a discretion call.

The `--engine` flag never suppresses this rule. Explicit `--engine claude`
means "Claude is the primary judge"; it does not mean "do not run Codex as the
second pair judge." The only valid skip reasons after a non-empty eligible
trigger are deterministic MECHANICAL HIGH/CRITICAL blockers or Codex
unavailability proven by the invocation layer.

Pair-mode JUDGE: spawn a second Agent with the OTHER engine's adapter; the second judge is a bounded adversarial complement, not a duplicate broad audit. The primary judge owns broad coverage; pair-JUDGE targets the two highest-risk explicit `## Verification` bullets that cross state mutation, all-or-nothing rollback, ordering, idempotency, auth, or error-priority clauses. It must not read `.claude/skills`, `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness docs unless the orchestrator pasted a specific excerpt into the prompt. It may use only the spec, diff, implementation files, tests, and the repo's existing CLI/API/test runner. It may execute at most two targeted probes before first output, and each probe must compare the full externally visible result (exit/stdout/stderr plus full parsed output object, including accepted/scheduled rows, rejected rows, and remaining state when present), not just a single property. For priority/stateful specs, at least one probe must include an earlier input entity that would succeed under input-order processing, a later higher-priority entity that consumes or blocks the critical resource, and a failure/blocked/rollback edge that determines a later entity's state. Scope qualifiers are binding: pair-JUDGE must not reinterpret `inside a warehouse`, `per resource`, or line-scoped rules as global rules. When both priority ordering and rollback/blocked-interval behavior appear in the spec, this dominance-loss probe is mandatory and comes before any other probe: an earlier lower-priority entity that would succeed alone or under input-order processing must lose because a later higher-priority entity is processed first; a failed/blocked middle entity must not corrupt later state; and the assertion must cover complete accepted/scheduled and rejected output ordering. It must stop and emit JSONL immediately on the first verdict-binding finding, and must emit PASS immediately if both probes plus static scope/dependency checks pass. Both judgments merge with the rule "any HIGH/CRITICAL finding either model surfaces is verdict-binding; high-confidence MEDIUM findings are also verdict-binding when they identify a concrete behavioral regression against the spec, public contract, or existing test contract." Cross-model disagreement on advisory lower-severity findings is logged but does not change the verdict. If MECHANICAL has a HIGH/CRITICAL finding, skip the second judge and record `pair_judge: null`; the fix loop needs the deterministic finding, not duplicate review.

Findings written to `.devlyn/verify.findings.jsonl`. **VERIFY agents have no code-mutation tools.** Codex pair-JUDGE is read-only: invoke `codex-monitored.sh` directly with `-c model_reasoning_effort=medium` for this bounded two-probe review, without piping to `tail`/`head`/`grep`, capture stdout/stderr by direct tool capture or file redirection, require JSONL findings on stdout, and have the orchestrator write `.devlyn/verify.pair.findings.jsonl`. If stdout is first captured as `.devlyn/codex-judge.stdout`, run `python3 .claude/skills/_shared/collect-codex-findings.py` before merge; that script is the deterministic boundary writer for `.devlyn/verify.pair.findings.jsonl`. Raw stdout remains diagnostic only: if stdout contains findings or a non-PASS summary while `.devlyn/verify.pair.findings.jsonl` is empty, `verify-merge-findings.py` blocks VERIFY for `verify.pair.emission-contract`. Do not ask Codex to `apply_patch` or edit `.devlyn`. After primary and pair findings are written, run `python3 .claude/skills/_shared/verify-merge-findings.py --write-state`. Branch only on the merged `state.phases.verify.verdict`; a HIGH/CRITICAL finding from either judge must mechanically become `NEEDS_WORK`. Never write `.devlyn/verify-merged.findings.jsonl` or `.devlyn/verify-merge.summary.json` by hand; `verify-merge-findings.py` is their only writer. State write: `phases.verify.{started_at, verdict, completed_at, duration_ms, sub_verdicts: {mechanical, judge, pair_judge?}, artifacts}`.

Branch:
- `PASS` → PHASE 6.
- `PASS_WITH_ISSUES` (LOW severity only) → PHASE 6 with banner.
- `NEEDS_WORK` / `BLOCKED` → fix loop with `triggered_by: "verify"`. Spawn IMPLEMENT-engine agent with the verify findings; increment `state.rounds.global`. Second `NEEDS_WORK` → halt with verdict `BLOCKED:verify-exhausted`.

## PHASE 6: FINAL REPORT + ARCHIVE

State write: `phases.final_report.started_at` at the top of this phase.

1. **Terminal verdict** — derive from `state.phases.{plan, implement, build_gate, cleanup, verify}.verdict` per the precedence rules in `references/state-schema.md#terminal-verdict`. Verify-only mode short-circuits to `state.phases.verify.verdict`.

2. **Render report** — sections: header (run_id, engine, mode, verdict, wall-time), per-phase summary, findings table (verify findings only — post-IMPLEMENT phases are findings-only), follow-up notes (any `--continue-on-large` assumptions, any silent fallbacks).

3. State write: `phases.final_report.{verdict, completed_at, duration_ms}` BEFORE archive runs (archive prune logic skips runs whose `final_report.verdict` is null).

4. **Archive** — invoke the deterministic script: `python3 .claude/skills/_shared/archive_run.py`. The script reads `run_id` from `.devlyn/pipeline.state.json`, moves per-run artifacts (state.json + `*.findings.jsonl` + `*.log.md` + `fix-batch.round-*.json` + `criteria.generated.md` + `risk-probes.jsonl` + `spec-verify*.json` + `spec-verify-findings.jsonl`) into `.devlyn/runs/<run_id>/`, then best-effort prunes to last 10 completed runs. Archive must run; running this step as deterministic-script-not-prose ensures the move actually happens (iter-0033a Smoke 3 caught a case where the agent claimed archive ran without moving the files).

5. Kill any dev server PHASE 3 left running.

## State management

`.devlyn/pipeline.state.json` is the single authoritative verdict source. Branch on `state.phases.<name>.verdict` directly; never parse `.devlyn/*.findings.jsonl` for routing decisions. Schema: `references/state-schema.md`.
