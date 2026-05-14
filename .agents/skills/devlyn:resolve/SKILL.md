---
name: devlyn:resolve
description: Hands-free pipeline for any coding task — bug fix, feature, refactor, debug, modify, PR review. Free-form goal or formal spec input. Plan → Implement → Build-gate → Cleanup → Verify (fresh subagent, findings-only). Mechanical-first verification; pair-mode is conditional-default in Verify. Use when the user says "resolve this", "fix this", "implement this", "refactor this", "debug this", "review this PR", or wants hands-off completion.
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
2. Engine availability: follow `_shared/engine-preflight.md`. When a selected or conditionally-required engine is unavailable, fail closed with `BLOCKED:<engine>-unavailable` and setup guidance; do not convert a pair-required or explicitly requested engine into a solo run.
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
- Default engine: Claude for PLAN / IMPLEMENT / BUILD_GATE / CLEANUP. `--engine codex` routes IMPLEMENT to Codex; orchestration stays Claude. Pair-mode is conditional-default in VERIFY/JUDGE and selects the OTHER engine for the fresh subagent when the trigger policy fires.
- Multi-LLM evolution: when a new model adapter ships in `_shared/adapters/`, that engine becomes selectable via `--engine <model>` without further skill changes (NORTH-STAR.md "Multi-LLM evolution direction").
</engine_routing>

<modes>
Three input shapes:

1. **Free-form**: `/devlyn:resolve "fix the login bug"`. PHASE 0 runs the complexity classifier and either proceeds with an internal mini-spec (trivial), drafts focused questions for in-prompt resolution (medium), or escalates to `/devlyn:ideate` (large/ambiguous). No mid-pipeline prompts in any branch.
2. **Spec**: `/devlyn:resolve --spec docs/roadmap/phase-N/X.md`. Spec is read-only. Stage verification commands from sibling `spec.expected.json`; if absent, use the legacy `## Verification` JSON block.
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
   - `--no-pair` — disable conditional VERIFY pair-JUDGE for this run. Record `pair_trigger.skipped_reason: "user_no_pair"` whenever a trigger would otherwise fire.
   - `--risk-probes` — insert PHASE 1.5 cross-engine probe derivation. The OTHER engine converts visible `## Verification` bullets into bounded executable probes before IMPLEMENT; BUILD_GATE and VERIFY replay them mechanically.
   - `--no-risk-probes` — disable automatic high-risk risk probes. Explicit `--risk-probes` wins over `--no-risk-probes`.
   - `--bypass <phase>[,...]` — skip specific phases. Valid: `build-gate`, `cleanup`. PLAN, IMPLEMENT, VERIFY are non-bypassable.
   - `--perf` — opt in to per-phase timing.

2. Engine pre-flight: follow `_shared/engine-preflight.md`. If a required engine is unavailable, halt with a BLOCKED verdict and setup instructions instead of downgrading.

   `--pair-verify` and `--no-pair` are mutually exclusive; if both are present, stop with `BLOCKED:invalid-flags`.

3. Initialize `.devlyn/pipeline.state.json` per `references/state-schema.md`. Set `state.run_id`, `started_at`, `engine`, `pair_verify: true` only when `--pair-verify` was passed and `false` otherwise, `base_ref.{branch, sha}`, `rounds.{max_rounds, global: 0}`, `bypasses`, empty `phases`, empty `criteria`, and `risk_profile: { high_risk: false, reasons: [], risk_probes_enabled: false, pair_default_enabled: true }`. `risk_profile` is strict typed state: keep it an object, keep the three flags as JSON booleans, and keep `reasons` as a string array; never serialize booleans as strings.

4. **Mode-specific init**:
   - **Free-form**: read `references/free-form-mode.md`. Run the complexity classifier deterministically (rules over keyword density / file count / spec-shape signals, plus pair-evidence intent). Set `state.complexity ∈ {trivial, medium, large}`. Trivial: write internal mini-spec to `.devlyn/criteria.generated.md` and proceed. Medium: synthesize a minimal spec from the goal + add 1-2 context anchors from the codebase, write to `.devlyn/criteria.generated.md`, proceed. Every free-form branch that writes criteria must set `state.source.type = "generated"`, `state.source.criteria_path = ".devlyn/criteria.generated.md"`, and `state.source.criteria_sha256` from the raw file bytes. Large: log `recommend: /devlyn:ideate first` in the final report and either halt (default) or proceed with assumed defaults if `--continue-on-large` flag set, except pair-evidence intent without an actionable solo-headroom hypothesis must halt with `BLOCKED:solo-headroom-hypothesis-required`, and unmeasured pair-candidate intent without solo ceiling avoidance must halt with `BLOCKED:solo-ceiling-avoidance-required`.
   - **Spec**: validate spec exists. If sibling `spec.expected.json` exists, run `--check-expected <expected-path>` to validate both the expected contract, sibling spec `complexity` frontmatter, and any present actionable solo-headroom hypothesis; if the spec has a solo-headroom hypothesis, its observable command must match `spec.expected.json.verification_commands[].cmd`. Then stage `.devlyn/spec-verify.json` from `verification_commands`. Otherwise run `--check <spec-path>` to validate the legacy inline carrier plus supported `complexity` frontmatter and any present actionable solo-headroom hypothesis; if the spec uses an inline `## Verification` JSON carrier, any solo-headroom hypothesis command must match that carrier's `verification_commands[].cmd`. Then stage from the legacy inline carrier. Compute `state.source.spec_sha256`.
   - **Verify-only**: skip to PHASE 5 with `state.source.spec_path` set, the supplied diff captured at `.devlyn/external-diff.patch`.

5. Compute `state.risk_profile` from the user goal plus spec/criteria text. Mark `high_risk: true` when the work touches any of: auth/authz, permissions, security, token/session, payment/money/billing/invoice/pricing/tax/ledger, persistence/data mutation/deletion/migration, idempotency/replay/duplicate, API/webhook/raw-body/signature, allocation/scheduling/inventory/rollback/transaction, or explicit error-priority/output-shape contracts. If high-risk and `--no-risk-probes` is absent, set `risk_probes_enabled: true`; explicit `--risk-probes` also sets it true. If `--no-pair` is present, set `pair_default_enabled: false`. Add concise string reasons for the classification, but do not use reasons as substitutes for the boolean fields.

6. Announce one line: `resolve starting — run <run_id> — engine <engine> — mode <mode> — complexity <complexity-or-na> — pair <conditional|disabled> — risk_probes <on|off>`.

## PHASE 1: PLAN

Skip in verify-only mode. The heaviest phase by design — spec/criteria define non-negotiable invariants; plan formalizes how the implementation hits them.

Engine: Claude (PLAN-pair is **unmeasured at HEAD** — iter-0033d is the first L1-vs-L2 measurement; iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT PLAN-pair). Prompt body: `references/phases/plan.md`.

Subagent output (writes `.devlyn/plan.md`): file list to touch, risk list (out-of-scope expansions, ambiguous spec sections), acceptance restatement (what `## Verification` actually requires verbatim).

State write: `phases.plan.{started_at, verdict, completed_at, duration_ms}`.

After return:
1. If `.devlyn/plan.md` lists zero files → halt with verdict `BLOCKED:plan-empty`.
2. If risk list flags an out-of-scope expansion the user did not authorize → re-spawn once with the reminder; second fail → halt.

## PHASE 1.5: RISK_PROBES

Skip unless `--risk-probes` is set OR `state.risk_profile.risk_probes_enabled`
is true. This phase is findings-as-executable-checks, not a second plan and not
debate. If this phase is required and the OTHER engine is unavailable, halt with
`BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable` plus setup guidance;
do not silently continue without probes.

Engine: OTHER engine from PHASE 2's selected IMPLEMENT engine. Prompt body:
`references/phases/probe-derive.md`.

Inputs: source spec/criteria, `.devlyn/plan.md`, and repo read/search. Forbidden:
`spec.expected.json`, `.devlyn/spec-verify.json`, `BENCH_FIXTURE_DIR`, hidden
fixture/verifier paths, previous findings, and harness docs unless excerpted.

Output: `.devlyn/risk-probes.jsonl`, 1 to 3 JSONL entries. Each entry must be
one verification command shape plus `id`, `derived_from`, `tags`, and
`tag_evidence`, where `derived_from` is an exact substring of the visible
`## Verification` bullet the command directly exercises. `tag_evidence` must be
a JSON object keyed by tag, with marker arrays as values; a top-level array or
tag-only probe is malformed. `ordering_inversion` must include
`input_order_would_choose_wrong_winner` and `asserts_processing_order_result`;
`prior_consumption` must include `same_resource_consumed_first` and
`later_entity_fails_or_reroutes`; `stdout_stderr_contract` must include
`asserts_named_stream_output`; `error_contract` must include
`asserts_error_payload_or_stderr` and `asserts_nonzero_or_exit_2`.
`http_error_contract` must include `asserts_http_error_status` and
`asserts_error_payload_body`.
`auth_signature_contract` must include `asserts_signature_over_exact_bytes` and
`asserts_tampered_or_missing_signature_rejected`; `idempotency_replay` must
include `first_delivery_then_duplicate` and
`duplicate_id_rejected_regardless_of_body`; `concurrent_state_consistency` must
include `overlapping_mutations_exercised`,
`all_successful_responses_reflected`, and `distinct_identifiers_asserted`;
`atomic_batch_state` must include `mixed_valid_invalid_batch`,
`asserts_store_unchanged_after_failure`, and
`asserts_success_order_and_distinct_ids`.
When visible text names exact keys, fields, row shapes, JSON objects, response
bodies, stdout/stderr objects, or exact error bodies, `shape_contract` must
include `uses_visible_input_key_names`, `asserts_visible_output_key_names`, and
`asserts_no_unexpected_output_keys`; exact JSON error objects/bodies must also
include `asserts_exact_error_object`. Cart/pricing success probes should use
`shape_contract` unless they satisfy the `ordering_inversion` markers. The probe
command must not reference external network URLs; use only worktree-local or
localhost resources.
For high-complexity specs with multiple behavior bullets, at least one probe
must be compound: it must exercise two or more visible verification bullets in a
single command. Empty output is invalid when `--risk-probes` is set.
When the visible spec includes a solo-headroom hypothesis, the first probe must
exercise that hypothesis with the visible command/input shape and full
observable assertion; its `cmd` must contain the hypothesis's backticked
observable command, and its `derived_from` must reference the hypothesis bullet,
so deterministic validation can prove the probe targets the stated expected
`solo_claude` miss. Otherwise the probe set is too weak for pair-evidence work.
The same actionable solo-headroom hypothesis is a VERIFY pair-trigger reason,
so a candidate spec that explicitly predicts a `solo_claude` miss cannot finish
on solo VERIFY alone unless `--no-pair` was explicitly set or an earlier
verdict-binding blocker already decides the run.

State write: `phases.probe_derive.{started_at, verdict, completed_at, duration_ms, artifacts}`.

Invocation contract when OTHER engine is Codex:

- Invoke Codex only through the monitored wrapper path in `CODEX_MONITORED_PATH`,
  or `.claude/skills/_shared/codex-monitored.sh` when the env var is absent:
  `CODEX_MONITORED_ISOLATED=1 bash "$CODEX_MONITORED_PATH" -C "$PWD" --full-auto -c model_reasoning_effort=high "<probe prompt>"`.
  Isolation keeps user config, AGENTS.md, pyx-memory, hooks, and project rules
  from adding hidden context, tool calls, or transcript side effects.
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
3. Always runs `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes` (verification_commands literal-match plus `.devlyn/risk-probes.jsonl` when present). If `state.risk_profile.risk_probes_enabled == true`, the script requires `.devlyn/risk-probes.jsonl`; a missing file is a CRITICAL mechanical blocker, not a silent solo run.
4. If diff touches web-surface files: run the browser tier with the repo's available toolchain (for example Playwright or curl).
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

1. **MECHANICAL** (deterministic): re-run `SPEC_VERIFY_PHASE=verify_mechanical SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes` against the post-CLEANUP code (independent of BUILD_GATE's earlier run). If `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker. This emits `.devlyn/verify-mechanical.findings.jsonl` for `verify-merge-findings.py`.

2. **JUDGE** (fresh-context Agent): grade the diff against the spec on rubric axes (spec compliance, scope, quality, consistency). Split each Requirement into binding clauses and trace code-order counterexamples; a passing verifier proves only the case it exercises, not neighboring `once` / `regardless` / `duplicate` / auth-order / rollback invariants. Respect scope qualifiers such as `inside a warehouse`, `per resource`, `for this line`, and `after validation`; do not widen a scoped clause into a global invariant, and compose multiple ordering rules in the stated order. For stateful flows, explicitly trace failed-operation rollback and the next entity's state before hunting broader edge cases. For high-complexity specs, construct at least one interaction counterexample that combines ordering/priority with failure handling and state mutation, then execute at least one such scenario through the repo's existing CLI/API/test runner without leaving tracked files behind; one-axis examples and pure mental tracing are insufficient. Default engine = same as IMPLEMENT (solo). Pair-mode (cross-model JUDGE) is eligible only after MECHANICAL and the primary JUDGE have no verdict-binding findings; deterministic blockers and primary JUDGE blockers already decide the verdict and route to the fix loop. Pair-mode fires when eligible and:
   - `--pair-verify` flag set, OR
   - `state.mode == "verify-only"`, OR
   - `state.risk_profile.high_risk == true`, OR
   - `.devlyn/risk-probes.jsonl` exists or `state.risk_profile.risk_probes_enabled == true`, OR
   - spec frontmatter has `complexity: high` (legacy/external spec `complexity: large` is accepted for compatibility; new specs use `high`), OR current free-form `state.complexity` is `"large"` (legacy `"high"` state is accepted only for archived runs), OR
   - MECHANICAL or the primary JUDGE emits findings flagged `severity: warning` (not verdict-binding — those route to fix loop directly), OR
   - `state.verify.coverage_failed == true` (judge could not exercise a required spec axis from available evidence).

After MECHANICAL and the primary JUDGE finish, compute `pair_trigger = { eligible, reasons[], skipped_reason }`, write it into `state.phases.verify`, and then spawn the second OTHER-engine judge when eligible. If `eligible == true`, `reasons` must be non-empty, include every applicable canonical reason, and every reason must be one of these canonical values: `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, or `judge.warning`; `skipped_reason` must be null; and you MUST spawn the second OTHER-engine judge. If `eligible == false`, `reasons` must be empty and `skipped_reason` must be a string or null. Contradictory, incomplete, or unknown trigger state is a VERIFY contract violation, not advisory metadata; `verify-merge-findings.py` blocks malformed trigger state. Pair reasons derive `risk.high` and `risk_probes.enabled` from `state.risk_profile`; malformed `risk_profile` is also a VERIFY contract violation because it can hide a required pair decision.

The `--engine` flag never suppresses this rule. Explicit `--engine claude`
means "Claude is the primary judge"; it does not mean "do not run Codex as the
second pair judge." The only valid skip reasons after a non-empty eligible
trigger are deterministic MECHANICAL HIGH/CRITICAL blockers or an explicit
`--no-pair`. Engine unavailability is a `BLOCKED:<engine>-unavailable` verdict,
not a skip reason.

Pair-mode JUDGE: spawn a second Agent with the OTHER engine's adapter; the second judge is a bounded adversarial complement, not a duplicate broad audit. The primary judge owns broad coverage; pair-JUDGE targets the two highest-risk explicit `## Verification` bullets that cross state mutation, all-or-nothing rollback, ordering, idempotency, auth, or error-priority clauses. If the spec includes a solo-headroom hypothesis, one of those targeted probes must exercise that hypothesis with the visible command/input shape and full externally visible result, using the hypothesis's backticked observable command as its command anchor before adding bounded input variations. It must not read `.claude/skills`, `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness docs unless the orchestrator pasted a specific excerpt into the prompt. It may use only the spec, diff, implementation files, tests, and the repo's existing CLI/API/test runner. It may execute at most two targeted probes before first output, and each probe must compare the full externally visible result (exit/stdout/stderr plus full parsed output object, including accepted/scheduled rows, rejected rows, and remaining state when present), not just a single property. When the spec names exact keys, row shapes, JSON object shape, or an exact error body, pair-JUDGE must compare parsed key sets/deep equality so aliased keys, missing keys, and extra keys are verdict-binding failures, and it must construct inputs with the spec's visible key names. For priority/stateful specs, at least one probe must include an earlier input entity that would succeed under input-order processing, a later higher-priority entity that consumes or blocks the critical resource, and a failure/blocked/rollback edge that determines a later entity's state. For cart/pricing specs where visible verification combines duplicate items, line promotions, tax, coupon, and shipping, the success-path probe must include interleaved duplicates plus taxable and non-taxable items and assert full output rows. Scope qualifiers are binding: pair-JUDGE must not reinterpret `inside a warehouse`, `per resource`, or line-scoped rules as global rules. When both priority ordering and rollback/blocked-interval behavior appear in the spec, this dominance-loss probe is mandatory and comes before any other probe: an earlier lower-priority entity that would succeed alone or under input-order processing must lose because a later higher-priority entity is processed first; a failed/blocked middle entity must not corrupt later state; and the assertion must cover complete accepted/scheduled and rejected output ordering. It must stop and emit JSONL immediately on the first verdict-binding finding, and must emit PASS immediately if both probes plus static scope/dependency checks pass. Both judgments merge with the rule "any HIGH/CRITICAL finding either model surfaces is verdict-binding; high-confidence MEDIUM findings are also verdict-binding when they identify a concrete behavioral regression against the spec, public contract, or existing test contract." Cross-model disagreement on advisory lower-severity findings is logged but does not change the verdict. If MECHANICAL or the primary JUDGE has a verdict-binding finding, skip the second judge and record `pair_judge: null`; the fix loop needs the blocker, not duplicate review.

If pair-mode is triggered and the OTHER engine is unavailable, do not downgrade
or skip the required judge. Set VERIFY to `BLOCKED:<engine>-unavailable`, preserve the
failed availability check evidence, and print setup guidance:

- Codex: install/configure the Codex CLI, run `codex auth` or the current login
  flow, verify `codex --version`, then rerun. Use `--no-pair` only when the user
  intentionally accepts solo VERIFY for this run.
- Claude: install/configure Claude Code, run `claude --version` when available,
  confirm the host can spawn Claude agents, then rerun.

Findings written to `.devlyn/verify.findings.jsonl`. **VERIFY agents have no code-mutation tools.** Codex pair-JUDGE is read-only: invoke `codex-monitored.sh` with `CODEX_MONITORED_ISOLATED=1` and `-c model_reasoning_effort=medium`, no `tail`/`head`/`grep` pipes, direct stdout/stderr capture, JSONL findings on stdout, and orchestrator-written `.devlyn/verify.pair.findings.jsonl`. Isolation blocks user config, AGENTS.md, pyx-memory, hooks, and project rules from hidden context/tool/transcript side effects. If stdout is captured as `.devlyn/codex-judge.stdout`, run `python3 .claude/skills/_shared/collect-codex-findings.py` before merge; raw stdout is diagnostic only. If stdout contains findings or a non-PASS summary while `.devlyn/verify.pair.findings.jsonl` is empty, `verify-merge-findings.py` blocks VERIFY for `verify.pair.emission-contract`. Do not ask Codex to `apply_patch` or edit `.devlyn`. After primary and pair findings are written, run `python3 .claude/skills/_shared/verify-merge-findings.py --write-state`. Branch only on the merged `state.phases.verify.verdict`; a HIGH/CRITICAL finding from either judge must mechanically become `NEEDS_WORK`. Never write `.devlyn/verify-merged.findings.jsonl` or `.devlyn/verify-merge.summary.json` by hand; `verify-merge-findings.py` is their only writer. State write: `phases.verify.{started_at, verdict, completed_at, duration_ms, sub_verdicts: {mechanical, judge, pair_judge?}, artifacts}`.

Branch:
- `PASS` → PHASE 6.
- `PASS_WITH_ISSUES` (LOW severity only) → PHASE 6 with banner.
- `NEEDS_WORK` / `BLOCKED` → fix loop with `triggered_by: "verify"`. Spawn IMPLEMENT-engine agent with the verify findings; increment `state.rounds.global`. Second `NEEDS_WORK` → halt with verdict `BLOCKED:verify-exhausted`.

## PHASE 6: FINAL REPORT + ARCHIVE

State write: `phases.final_report.started_at` at the top of this phase.

1. **Terminal verdict** — derive from `state.phases.{plan, implement, build_gate, cleanup, verify}.verdict` per the precedence rules in `references/state-schema.md#terminal-verdict`. Verify-only mode short-circuits to `state.phases.verify.verdict`.

2. **Render report** — sections: header (run_id, engine, mode, verdict, wall-time), per-phase summary, pair/risk-probe status, findings table (verify findings only — post-IMPLEMENT phases are findings-only), follow-up notes (any `--continue-on-large` assumptions, any `--no-pair` / `--no-risk-probes` opt-out, any engine setup guidance after BLOCKED, `/devlyn:ideate` guidance after `BLOCKED:solo-headroom-hypothesis-required` that asks for the visible behavior `solo_claude` is expected to miss, and `/devlyn:ideate` guidance after `BLOCKED:solo-ceiling-avoidance-required` that asks for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`).

3. State write: `phases.final_report.{verdict, completed_at, duration_ms}` BEFORE archive runs (archive prune logic skips runs whose `final_report.verdict` is null).

4. **Archive** — invoke the deterministic script: `python3 .claude/skills/_shared/archive_run.py`. The script reads `run_id` from `.devlyn/pipeline.state.json`, moves per-run artifacts (state.json + `*.findings.jsonl` + `*.log.md` + `fix-batch.round-*.json` + `criteria.generated.md` + `risk-probes.jsonl` + `spec-verify*.json` + `spec-verify-findings.jsonl`) into `.devlyn/runs/<run_id>/`, then best-effort prunes to last 10 completed runs. Archive must run; running this step as deterministic-script-not-prose ensures the move actually happens (iter-0033a Smoke 3 caught a case where the agent claimed archive ran without moving the files).

5. Kill any dev server PHASE 3 left running.

## State management

`.devlyn/pipeline.state.json` is the single authoritative verdict source. Branch on `state.phases.<name>.verdict` directly; never parse `.devlyn/*.findings.jsonl` for routing decisions. Schema: `references/state-schema.md`.
