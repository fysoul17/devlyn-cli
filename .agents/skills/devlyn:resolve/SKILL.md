---
name: devlyn:resolve
description: Hands-free pipeline for any coding task — bug fix, feature, refactor, debug, modify, PR review. Free-form goal or formal spec input. Plan → Implement → Build-gate → Cleanup → Verify (fresh subagent, findings-only). Mechanical-first verification; Verify dual-judge is default-when-available. Use when the user says "resolve this", "fix this", "implement this", "refactor this", "debug this", "review this PR", or wants hands-off completion.
---

Orchestrator for the 2-skill harness pipeline. One fresh worker per phase; file-based handoff via `.devlyn/pipeline.state.json`. VERIFY spawns a fresh-context worker so independence is structural — not advisory.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<orchestrator_context>
Long-horizon agentic work; context auto-compacts. State lives in `.devlyn/pipeline.state.json` — the single authoritative verdict source. Schemas in `references/state-schema.md`. Best at `xhigh` effort.
</orchestrator_context>

<autonomy_contract>
Hands-free. Measured by how far we get without human intervention.

1. Do not prompt the user mid-pipeline. When tempted to ask, pick the safe default, proceed, and log it in the final report.
2. Engine availability: follow `_shared/engine-preflight.md` for the explicit-route-vs-automatic-escalation distinction and BLOCKED-vs-skip behavior. Explicit routes (`--engine`, `--risk-probes`, `--pair-verify`) never downgrade to solo; unavailable auto-escalations proceed solo and report the skip.
3. Order: PLAN → RISK_PROBES? → IMPLEMENT → SURFACE_CLOSE? → BUILD_GATE → CLEANUP → VERIFY → FINAL_REPORT. No others.
4. Orchestrator does not write code. It parses input, spawns phases, reads state, branches on verdicts, emits the report.
5. Halt only on unrecoverable worker failure, empty IMPLEMENT, exhausted BUILD_GATE/VERIFY `max_rounds`, or SURFACE_CLOSE timeout / input-or-prompt mismatch / attestation failure / execution-audit violation / out-of-surface delta / rollback failure; adjudication-malformed SURFACE_CLOSE continues after successful rollback plus transcript write-audit; otherwise continue.
</autonomy_contract>

<harness_principles>
Every phase applies Subtractive-first / Goal-locked / No-workaround / Evidence, loaded by file or inline; Codex routes receive it inline.
</harness_principles>

<runtime_paths>
Resolve shared scripts from this skill's installed directory, never from the project cwd. At PHASE 0, before any phase command:

```bash
DEVLYN_SKILL_DIR="${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}"
if [ "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__" ] || [ ! -d "$DEVLYN_SKILL_DIR/../_shared" ]; then
  echo "BLOCKED:shared-dir-unresolved: $DEVLYN_SKILL_DIR/../_shared" >&2
  exit 1
fi
DEVLYN_SHARED_DIR="$(cd "$DEVLYN_SKILL_DIR/../_shared" && pwd)"
CODEX_MONITORED_PATH="$DEVLYN_SHARED_DIR/codex-monitored.sh"
if [ ! -f "$CODEX_MONITORED_PATH" ]; then
  echo "BLOCKED:shared-dir-unresolved: $CODEX_MONITORED_PATH" >&2
  exit 1
fi
```

`DEVLYN_SHARED_DIR` is the only valid `_shared` anchor. Claude Code supplies `CLAUDE_SKILL_DIR` by native render substitution; Codex/oh-my-pi installs receive an absolute copy-time stamp in the default branch. If the resolved skill directory is still the placeholder, `../_shared` is absent, or a required script is missing, halt with report-level `BLOCKED:shared-dir-unresolved` and include the failed path. Pass the absolute `DEVLYN_SHARED_DIR` and `CODEX_MONITORED_PATH` into every fresh phase worker.
</runtime_paths>

<engine_routing>
Each phase routes to an engine and prepends the per-engine adapter header from `_shared/adapters/<engine>.md` (e.g. `claude.md`, `codex.md`) to the canonical phase body. Adapter is the per-model delta (Anthropic's prompt-engineering guide for Claude, OpenAI's prompt guidance for Codex). Canonical body is engine-agnostic.

- Phase spawning is mandatory for every orchestrator. Same-context PLAN / IMPLEMENT / BUILD_GATE / CLEANUP / VERIFY is a contract violation. If the current CLI cannot spawn a fresh worker, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable` with the failed spawn command; do not continue with ad-hoc same-context execution.
- Claude Code phases: spawn `Agent` (`mode: "bypassPermissions"`); prompt = adapter-header + canonical-body + task-context.
- Codex CLI phases: shell out via `bash "$CODEX_MONITORED_PATH"` with the same compounded prompt. Each `codex exec` child is a new session/fresh context. The wrapper closes stdin and emits a heartbeat. No MCP. The wrapper call is foreground-blocking — never a background shell (`run_in_background`, `&`, `nohup`), never end your message while it runs: headless print-mode wind-down kills backgrounded children (0-byte delivery); the heartbeat is the observability channel.
- oh-my-pi phases: spawn the native `task` tool with a fresh `context` containing adapter-header + canonical-body + task-context. Capture the task result into `.devlyn/<phase>.stdout` and any tool error into `.devlyn/<phase>.stderr` before updating state. If the `task` tool is unavailable for an omp-routed phase, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable`; do not fall back to same-context execution or a nested `omp -p` subprocess.
- Default engine: Claude for PLAN / IMPLEMENT / BUILD_GATE / CLEANUP when the orchestrator has Claude Code's native `Agent` primitive; otherwise the default route is the current CLI's fresh worker (`codex` child process for Codex CLI, native `task` for oh-my-pi). Role resolution (`_shared/engine-preflight.md#role-resolution`): explicit `--engine` flag > machine-local `.devlyn/engines.json` `executor` pin > orchestrator-supported default above. Explicit routes and pins still fail closed when their required engine/spawn channel is unavailable. VERIFY/JUDGE selects the OTHER engine by default when available — OTHER = first adapter-valid, non-primary, available entry of `engines.json` `pair_judge_priority`, or the binary claude↔codex complement when unset.
- The `--engine` flag does not disable default pairing: the second judge uses the OTHER engine by default when available.
- Multi-LLM evolution: when a new model adapter ships in `_shared/adapters/`, that engine becomes selectable via `--engine <model>` without further skill changes (NORTH-STAR.md "Multi-LLM evolution direction").
</engine_routing>

<modes>
Three input shapes:

1. **Free-form**: `/devlyn:resolve "fix the login bug"` (inline goal) or `/devlyn:resolve --goal-file <path>` (goal text read from a file — the devlynd `ResolveAdapter` launcher path, injection-safe). PHASE 0 runs the complexity classifier and either proceeds with an internal mini-spec (trivial), drafts focused questions for in-prompt resolution (medium), or synthesizes a best-effort spec with a logged `## Assumptions` block (large; zero-scope-signal goals halt). No mid-pipeline prompts in any branch.
2. **Spec**: `/devlyn:resolve --spec docs/roadmap/phase-N/X.md`. Spec is read-only. Stage verification commands from sibling `spec.expected.json`; if absent, use the legacy `## Verification` JSON block.
3. **Verify-only**: `/devlyn:resolve --verify-only <diff-or-PR-ref> --spec <path>`. Skips PHASE 1-4. Runs PHASE 5 (VERIFY) on the supplied diff against the spec.
</modes>

<post_implement_invariant>
After `state.implement_passed_sha` is set: SURFACE_CLOSE and CLEANUP are limited to their allowlists (empty SURFACE_CLOSE PASS is valid; violations revert); VERIFY is fresh-context, findings-only, and mutation-free. No fresh VERIFY worker → `BLOCKED:fresh-context-unavailable`, never same-context review.
</post_implement_invariant>

<transition_protocol>
For every direct complete→spawn handoff, call `state-phase-write.py ... --phase <current> transition` with the current phase's normal completion/attestation arguments plus caller-specified `--next-phase`, `--next-round`, `--next-triggered-by`, `--next-engine`, `--next-model`, and any next-phase metadata. The verb validates a legal edge and commits both lifecycle writes atomically; it returns JSON state facts only. It never selects a phase/engine, renders a prompt, or spawns an agent. Use standalone `spawn` only for the initial post-bootstrap dispatch; use standalone `complete` when no next phase opens (including a halt).
</transition_protocol>

## PHASE 0: PARSE + CLASSIFY + ROUTE

1. Run the bootstrap once with the exact tokenized `<pipeline_config>` and this orchestrator's default engine from `<engine_routing>`:

   ```bash
   DEVLYN_DEFAULT_ENGINE="<current-cli-default>" python3 "$DEVLYN_SHARED_DIR/resolve-bootstrap.py" <pipeline_config tokens>
   ```

   Read its sole JSON result. On `ok:false`, halt on its exact report-level `blocked` string and show `detail`; init failures leave no partial run artifacts and create no phase verdict. On success, the script has atomically initialized the schema-v3 skeleton (`pair_verify: true` only when `--pair-verify` was passed), stamped the null-safe Claude session id, persisted exact-byte Goal/spec identity, staged spec verification inputs, and captured the verify-only external diff. It validates only flags needed for those init fields, including mode exclusivity, `--max-rounds`, `--bypass`, and `--pair-verify`/`--no-pair`; `--pair-verify` and `--no-pair` are mutually exclusive. Free-form init sets `state.source.type = "generated"`. Spec staging validates supported `complexity` frontmatter (including sibling spec `complexity` frontmatter) and any present actionable solo-headroom hypothesis, matching its command to `spec.expected.json.verification_commands[].cmd` or the inline `## Verification` JSON carrier. It does not validate engines, write the untracked baseline, classify complexity/risk, choose a route, or announce. `state.engine` is the raw `--engine` value with `engine_source: "flag"`, otherwise the passed `DEVLYN_DEFAULT_ENGINE` with `engine_source: "default"`; step 2 resolves and replaces both fields.

2. Engine pre-flight: follow `_shared/engine-preflight.md`, including role resolution. If `.devlyn/engines.json` exists: malformed JSON, any named engine without a `_shared/adapters/<name>.md` adapter, or an adapter that declares itself ineligible for the requested role, halts with report-level `BLOCKED:invalid-engine-config` naming the offending entry. A pin is an explicit route — a pinned but unavailable engine halts with `BLOCKED:<engine>-unavailable`. If a required engine is unavailable, halt with a BLOCKED verdict and setup instructions instead of downgrading. After successful role resolution, replace `state.engine` and `state.engine_source` with the resolved executor and its provenance (`"flag" | "engines.json" | "default"`). (These and all other PHASE-0 halts are report-level `BLOCKED:<reason>` strings only; the JSON `phases.*.verdict` carrier in `pipeline.state.json` always stays the bare enum `"BLOCKED"`.)

3. Write `.devlyn/untracked.baseline`: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --write-untracked-baseline`.

4. Read the Goal/spec through `state.source`. For free-form mode, run the deterministic classifier in `references/free-form-mode.md`. Zero-scope-signal goals halt with `BLOCKED:large-needs-ideation`; pair-evidence intent without an actionable solo-headroom hypothesis must halt with `BLOCKED:solo-headroom-hypothesis-required`; unmeasured pair-candidate intent without solo ceiling avoidance must halt with `BLOCKED:solo-ceiling-avoidance-required`. Follow the selected branch to write the trivial/medium/large body of `.devlyn/criteria.generated.md`, then set `state.complexity` and its raw-byte `criteria_sha256`. The Large `## Assumptions`/recommendation/final-report obligations remain unchanged.

   Compute `state.risk_profile` from the user goal plus spec/criteria text. Mark `high_risk: true` for auth/authz, permissions, security, token/session, payment/money/billing/invoice/pricing/tax/ledger, persistence/data mutation/deletion/migration, idempotency/replay/duplicate, API/webhook/raw-body/signature, allocation/scheduling/inventory/rollback/transaction, or explicit error-priority/output-shape contracts. Explicit `--risk-probes` sets both probe booleans true. Otherwise an automatic high-risk route enables probes only when the resolved OTHER engine is available and `--no-risk-probes` is absent; if unavailable, keep probes disabled and append `auto-risk-probes skipped: <engine>-unavailable`. `--no-pair` sets `pair_default_enabled: false`. Preserve strict boolean/list types and concise string reasons.

5. Announce one line: `resolve starting — run <run_id> — engine <engine> — mode <mode> — complexity <complexity-or-na> — pair <on|solo:auto_pair_other_engine_unavailable|disabled> — risk_probes <on|off>`.

6. Immediately before the first worker dispatch, open the caller-selected `plan` (normal run) or `verify` (verify-only) span with standalone `state-phase-write.py ... spawn`; then dispatch that same phase. The bootstrap never chooses a phase, engine, branch, prompt, or agent.

## PHASE 1: PLAN

Skip in verify-only mode. The heaviest phase by design — spec/criteria define non-negotiable invariants; plan formalizes how the implementation hits them.

Engine: Claude (PLAN-pair is **research-only** — iter-0033d/f/g; unblock conditions in PHASE 1 / iter-0033g §H; iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT PLAN-pair). Prompt body: `references/phases/plan.md`.

Subagent output (writes `.devlyn/plan.md`): file list to touch, risk list (out-of-scope expansions, ambiguous spec sections), acceptance restatement (what `## Verification` actually requires verbatim). For large work only, PLAN may add a fourth section `## Execution phases` under the conditions in `references/phases/plan.md`; a phase block missing a runnable `gate:` line disqualifies the whole section — treat the run as single-phase and log the disqualification.

State write: `phases.plan.{started_at, verdict, completed_at, duration_ms}`.

After return:
1. If `.devlyn/plan.md` lists zero files → halt with verdict `BLOCKED:plan-empty`.
2. If risk list flags an out-of-scope expansion the user did not authorize → re-spawn once with the reminder; second fail → halt.
3. After any re-spawn above, if `state.risk_profile.risk_probes_enabled == true` and `state.risk_profile.risk_probes_explicit == false`, parse the `authorized_surface` array from the JSON block under `<!-- devlyn:authorized-surface -->`. For a well-formed string array, compute `probe_scale_small := len(authorized_surface) <= 2 AND no entry ends in "/**"`. If true, set `risk_probes_enabled = false`, leave `high_risk` unchanged, and append `auto-risk-probes demoted: plan surface small (<n> paths)` to `reasons` using the actual length. A missing or malformed block leaves probe state unchanged; BUILD_GATE owns its malformed-block failure.

## PHASE 1.5: RISK_PROBES

Skip unless `--risk-probes` is set OR `state.risk_profile.risk_probes_enabled`
is true. This phase is findings-as-executable-checks, not a second plan and not
debate. When it runs, the OTHER engine is required: if unavailable, halt with
`BLOCKED:codex-unavailable` or `BLOCKED:claude-unavailable` plus setup guidance;
do not silently continue without probes. Reaching this halt means the route was
explicitly requested (`--risk-probes`) — an auto high-risk escalation toward an
unavailable OTHER engine was already gated off in PHASE 0 by leaving
`risk_probes_enabled: false`, so a single-engine high-risk run proceeds solo here.

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

- Invoke Codex only through the monitored wrapper path in `CODEX_MONITORED_PATH`
  resolved from `DEVLYN_SHARED_DIR`:
  `CODEX_MONITORED_ISOLATED=1 bash "$CODEX_MONITORED_PATH" -C "$PWD" -s workspace-write -c model_reasoning_effort=high "<probe prompt>"`.
  Isolation keeps user config, AGENTS.md, hooks, and project rules
  from adding hidden context, tool calls, or transcript side effects.
- Do not run `codex`, `codex exec`, `/Users/.../codex`, or a plugin-provided
  Codex binary directly. A raw Codex child can outlive the phase and makes the
  benchmark run invalid even if `.devlyn/risk-probes.jsonl` is written.
- Capture wrapper stdout/stderr to `.devlyn/probe-derive.stdout` and
  `.devlyn/probe-derive.stderr`; branch on the wrapper exit code before
  validating `.devlyn/risk-probes.jsonl`.

After return:
1. Run `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --validate-risk-probes`
   for the artifact boundary before IMPLEMENT; malformed probes halt with
   `BLOCKED:probe-derive-malformed`.
2. Compute `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --print-risk-probes-digest` and write the result to top-level `state.risk_probes_digest`:
   ```bash
   RISK_PROBES_DIGEST="$(python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --print-risk-probes-digest)"
   python3 - "$RISK_PROBES_DIGEST" <<'PY'
   import json, pathlib, sys
   path = pathlib.Path(".devlyn/pipeline.state.json")
   state = json.loads(path.read_text())
   state["risk_probes_digest"] = sys.argv[1]
   path.write_text(json.dumps(state, indent=2) + "\n")
   PY
   ```
   Any later legitimate probe regeneration is orchestrator-only and repeats validate plus digest-write.
3. IMPLEMENT receives `.devlyn/plan.md` plus `.devlyn/risk-probes.jsonl` as
   concrete acceptance obligations. It must not receive the producer engine's
   commentary or any mention of pair/critic/debate.

## PHASE 2: IMPLEMENT

Skip in verify-only mode. Constrained design judgment within PLAN's invariants. Writes code, tests, and inline doc-comments. No standalone DOCS phase — what the spec licenses is updated here, what it does not is out of scope.

Engine: per `--engine`. Prompt body: `references/phases/implement.md`.

State write: `phases.implement.{started_at, verdict, completed_at, duration_ms}`.

**Single-phase path** (plan.md has no `## Execution phases` section — every trivial/medium run, and any large run PLAN judged atomic): spawn IMPLEMENT once. No phase metadata of any kind appears in the prompt. After return:
1. `git diff --stat` — empty diff → halt with `BLOCKED:implement-empty`.
2. Set `state.implement_passed_sha = git rev-parse HEAD` (activates `<post_implement_invariant>`).
3. Checkpoint (**scoped staging** — this exact shape everywhere a pipeline commit is made): `bash -o pipefail -c 'python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --print-authorized-surface | git add --pathspec-from-file=- --pathspec-file-nul' && git commit -m "chore(pipeline): implement"`.

**Phase-gated path** (plan.md has `## Execution phases` with >1 phase): definitions are the contract in plan.md; progress is routing truth in `state.phases.implement.exec = { total, current, statuses, commits }` — never route on plan.md checkbox parsing. For each phase k = 1..N:
1. Spawn IMPLEMENT with the standard prompt plus: this phase's plan.md block only, the current worktree as the working base (overrides the body's `base_ref.sha` framing after phase 1), a `git diff <base_ref.sha>...HEAD --stat` summary, and the prior phase's gate output.
2. After return: run the phase's `gate:` commands directly — deterministic, exit-code truth, no LLM judgment.
3. Gate PASS → scoped-staging checkpoint with message `chore(pipeline): implement phase <k>/<N>`, write `exec.statuses[k-1] = "PASS"` + commit sha, advance `exec.current`, tick the plan.md checkbox mirror (display only).
4. Gate FAIL → no commit. One fix respawn for this phase with the gate output (increments `rounds.global`, shares `max_rounds`); second FAIL → `exec.statuses[k-1] = "FAIL"`, halt with `BLOCKED:phase-gate-exhausted`.

After the final phase's gate PASS: `git diff <base_ref.sha>...HEAD --stat` — empty → halt with `BLOCKED:implement-empty`; otherwise set `state.implement_passed_sha = git rev-parse HEAD` (phase commits already checkpoint the work — no extra commit).

## PHASE 2.5: SURFACE_CLOSE

Run once iff `state.source.type == "generated"` and complexity is trivial/medium. Engine is Claude always, pair-judge-routed; executor flag/pin ignored. Per `_shared/engine-preflight.md`, unavailability skips via `surface-skip`, reports `auto_surface_close_claude_unavailable`, never BLOCKs/reroutes.

Freeze `.devlyn/surface-close.input.patch`; assemble Claude adapter + `references/phases/surface-close.md` canonical body VERBATIM + data-only Goal/patch/hashes/surface/commands; hash the bytes and spawn with `--tools "Read,Grep,Glob,Edit,Write" --dangerously-skip-permissions --model claude-sonnet-5 --output-format json --strict-mcp-config --mcp-config '{"mcpServers":{}}'`, recording the same model at SPW spawn. Bound at 600s (native or `run-bounded.py 600 -- claude -p`), else block pre-spawn. Save raw stdout as `.devlyn/surface-close.output.json`, extract its `result` string to `.devlyn/surface-close.stdout`, retain `.devlyn/surface-close.worker-session.<round>.jsonl`, and complete with the wrapper as `--engine-session-log`; non-JSON/missing result follows the existing failure path. Workers execute nothing; `surface-check` gates rows, citations, scope, and execution. Empty PASS completes; authorized delta is scoped-staged and committed. Only `BLOCKED:surface-close-adjudication-malformed` runs `surface-adjudication-recover --authorized-surface-json <array>`, whose successful rollback and transcript Edit/Write audit complete the nonterminal skip carrier and continue to BUILD_GATE. Timeout, input/prompt mismatch, attestation failure, execution-audit violation, and out-of-surface delta run `surface-rollback`, complete bare `BLOCKED`, and halt; rollback failure also halts. One shot; no `max_rounds`.

**Common post-fix checkpoint (BUILD_GATE and VERIFY):** After fix IMPLEMENT returns, increment `state.rounds.global`; scoped-stage the authorized surface and commit `chore(pipeline): implement fix round <n>`; run `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase implement durability-enforce --round <n> --origin-phase <build_gate|verify>`. Its receipt must PASS before re-entry, which enforces it again before VERIFY artifact clearing or phase spawn.

## PHASE 3: BUILD_GATE

Skip in verify-only mode OR when `build-gate` in `state.bypasses`. Deterministic — same commands CI / Docker / production run.

Spawn Claude `Agent` (`mode: "bypassPermissions"`) with prompt body `references/phases/build-gate.md`. The agent:
1. Detects language/framework via project files (`package.json`, `pyproject.toml`, etc.).
2. Runs language-specific gates (tsc / lint / test).
3. Always runs `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` (verification_commands literal-match plus `.devlyn/risk-probes.jsonl` when present). If `state.risk_profile.risk_probes_enabled == true`, the script requires `.devlyn/risk-probes.jsonl`; a missing file is a CRITICAL mechanical blocker, not a silent solo run.
4. If diff touches web-surface files: run the browser tier with the repo's available toolchain (for example Playwright or curl).
5. Emits `.devlyn/build_gate.findings.jsonl` + `.devlyn/build_gate.log.md`.

State write: `phases.build_gate.{started_at, verdict, completed_at, duration_ms, artifacts}`.

Branch:
- `PASS` → PHASE 4.
- `FAIL` → fix loop. Spawn IMPLEMENT-engine agent with the build_gate findings as input, then run the common post-fix checkpoint with origin `build_gate`. On second FAIL with `state.rounds.global >= state.rounds.max_rounds` → halt with verdict `BLOCKED:build-gate-exhausted`.

## PHASE 4: CLEANUP

Skip if `cleanup` in `state.bypasses`. Task-scoped pass.

Engine: per `--engine`. Prompt body: `references/phases/cleanup.md`. Allowlist enforced post-spawn:
- Tooling artifacts the spec did not list as deliverables (`test-results/`, `playwright-report/`, `.last-run.json`, coverage HTML).
- Dead code added by this diff (not pre-existing dead code).
- Doc references whose target this diff renamed or removed.

Before spawn: pass `--pre-sha "$(git rev-parse HEAD)"` to the `state-phase-write.py ... spawn` call for this phase.

State write: `phases.cleanup.{started_at, verdict, completed_at, duration_ms, pre_sha, post_sha}`.

After return:
1. Run `git diff --name-only <pre_sha>` and compare new untracked files against `.devlyn/untracked.baseline` (`.devlyn/` exempt) — any path outside the cleanup allowlist (including a cleanup-created untracked file) → revert to `pre_sha`, delete the unauthorized untracked file, and emit `invariant.cleanup-out-of-scope` into `.devlyn/cleanup.findings.jsonl`.
2. If allowlist honored and diff non-empty: `git add -u && git commit -m "chore(pipeline): cleanup"`.
3. Complete cleanup with `--post-sha "$(git rev-parse HEAD)"` (also when the diff was empty).

## PHASE 5: VERIFY (fresh subagent, findings-only)

Independent quality layer. **Spawned with empty conversation context** — no carry-over from PHASE 1-4. Inputs limited to `spec.md` (or `.devlyn/criteria.generated.md`), `spec.expected.json`, the cumulative diff, and the spec hash. The fresh-context spawn is the structural guarantee of independence; the prompt body reinforces it.

Two sub-phases:

1. **MECHANICAL** (deterministic): re-run `SPEC_VERIFY_PHASE=verify_mechanical SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` against the post-CLEANUP code (independent of BUILD_GATE's earlier run). If `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker. This emits `.devlyn/verify-mechanical.findings.jsonl` for `verify-merge-findings.py`.

2. **JUDGE** (fresh-context Agent): grade the diff against the spec on rubric axes (spec compliance, scope, quality, consistency). Split each Requirement into binding clauses and trace code-order counterexamples; a passing verifier proves only the case it exercises, not neighboring `once` / `regardless` / `duplicate` / auth-order / rollback invariants. Respect scope qualifiers such as `inside a warehouse`, `per resource`, `for this line`, and `after validation`; do not widen a scoped clause into a global invariant, and compose multiple ordering rules in the stated order. For stateful flows, explicitly trace failed-operation rollback and the next entity's state before hunting broader edge cases. For high-complexity specs, construct at least one interaction counterexample that combines ordering/priority with failure handling and state mutation, then execute at least one such scenario through the repo's existing CLI/API/test runner without leaving tracked files behind; one-axis examples and pure mental tracing are insufficient. Default engine = same as IMPLEMENT. MECHANICAL always runs first; a verdict-binding blocker routes to the fix loop without either judge. After MECHANICAL passes, `--no-pair` continues solo with `user_no_pair`. Otherwise resolve the OTHER engine. An unavailable OTHER engine blocks an explicit `--pair-verify` promise; an automatic route records `auto_pair_other_engine_unavailable` and continues solo.

When the OTHER engine is available, persist `pair_trigger` before spawn with `pair.default` plus every applicable outcome-independent reason, then dispatch both judges concurrently against the same frozen diff via foreground parallel dispatch, never background shells. A primary blocker never cancels the pair judge. If foreground parallel dispatch is unavailable, run the same two required judges sequentially; this changes dispatch shape only and never permits outcome-dependent escalation or a pair skip. Prefer read-only checks and serialize probes that need exclusive shared state.

Keep the existing reasons as telemetry: `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, and `judge.warning`. Append the outcome-dependent reasons only after both judges return. Eligible schema-v3 state must include `pair.default`; all other applicable reasons remain completeness-checked. Malformed risk or trigger state BLOCKs VERIFY.

Pair-mode JUDGE: spawn a second Agent with the OTHER engine's adapter; the second judge is a bounded adversarial complement, not a duplicate broad audit. The primary judge owns broad coverage; pair-JUDGE targets the two highest-risk explicit `## Verification` bullets that cross state mutation, all-or-nothing rollback, ordering, idempotency, auth, or error-priority clauses. If the spec includes a solo-headroom hypothesis, one of those targeted probes must exercise that hypothesis with the visible command/input shape and full externally visible result, using the hypothesis's backticked observable command as its command anchor before adding bounded input variations. It must not read `.claude/skills`, `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness docs unless the orchestrator pasted a specific excerpt into the prompt. It may use only the spec, diff, implementation files, tests, and the repo's existing CLI/API/test runner. It may execute at most two targeted probes before first output, and each probe must compare the full externally visible result (exit/stdout/stderr plus full parsed output object, including accepted/scheduled rows, rejected rows, and remaining state when present), not just a single property. When the spec names exact keys, row shapes, JSON object shape, or an exact error body, pair-JUDGE must compare parsed key sets/deep equality so aliased keys, missing keys, and extra keys are verdict-binding failures, and it must construct inputs with the spec's visible key names. For priority/stateful specs, at least one probe must include an earlier input entity that would succeed under input-order processing, a later higher-priority entity that consumes or blocks the critical resource, and a failure/blocked/rollback edge that determines a later entity's state. For cart/pricing specs where visible verification combines duplicate items, line promotions, tax, coupon, and shipping, the success-path probe must include interleaved duplicates plus taxable and non-taxable items and assert full output rows. Scope qualifiers are binding: pair-JUDGE must not reinterpret `inside a warehouse`, `per resource`, or line-scoped rules as global rules. When both priority ordering and rollback/blocked-interval behavior appear in the spec, this dominance-loss probe is mandatory and comes before any other probe: an earlier lower-priority entity that would succeed alone or under input-order processing must lose because a later higher-priority entity is processed first; a failed/blocked middle entity must not corrupt later state; and the assertion must cover complete accepted/scheduled and rejected output ordering. It must stop and emit JSONL immediately on the first verdict-binding finding, and must emit PASS immediately if both probes plus static scope/dependency checks pass. Both judgments merge with the rule "any HIGH/CRITICAL finding either model surfaces is verdict-binding; high-confidence MEDIUM findings are also verdict-binding when they identify a concrete behavioral regression against the spec, public contract, or existing test contract." Cross-model disagreement on advisory lower-severity findings is logged but does not change the verdict. A primary JUDGE verdict-binding finding on a concurrent run does not cancel or discard the pair-JUDGE; both finding sets join the same fix round, and the merged verdict remains the worst source verdict without vote counting. `primary_judge_blocker` is parser-recognized only for archived v2.0 replay; new runs never write it. A verdict-binding MECHANICAL blocker still skips both judges and records `pair_judge: null`.

If the OTHER engine is unavailable, automatic VERIFY records
`auto_pair_other_engine_unavailable` and continues solo. Explicit `--pair-verify`
instead sets VERIFY to `BLOCKED:<engine>-unavailable`, preserves the failed
check, and prints setup guidance: install/configure the missing CLI, complete
its auth/login flow, verify `<engine> --version`, then rerun. `--no-pair` is only
for an intentional solo run.

Findings written to `.devlyn/verify.findings.jsonl`. **VERIFY agents have no code-mutation tools.** Codex pair-JUDGE is read-only: invoke `codex-monitored.sh` with `CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600` and `-c model_reasoning_effort=medium`, no `tail`/`head`/`grep` pipes, direct stdout/stderr capture, JSONL findings on stdout, and orchestrator-written `.devlyn/verify.pair.findings.jsonl`. Isolation blocks user config, AGENTS.md, hooks, and project rules from hidden context/tool/transcript side effects. If stdout is captured as `.devlyn/codex-judge.stdout`, run `python3 "$DEVLYN_SHARED_DIR/collect-codex-findings.py"` before merge; raw stdout is diagnostic only. If stdout contains findings or a non-PASS summary while `.devlyn/verify.pair.findings.jsonl` is empty, `verify-merge-findings.py` blocks VERIFY for `verify.pair.emission-contract`. Do not ask Codex to `apply_patch` or edit `.devlyn`. When the OTHER engine is Claude (codex/omp orchestrator), the judge call is wrapped as `python3 "$DEVLYN_SHARED_DIR/run-bounded.py" 600 -- claude -p ...` with the same flags as `_shared/adapters/claude.md` `## Invocation`, stdout captured as `.devlyn/claude-judge.stdout`, and the same emission contract applied to that file. On judge subprocess exit 124, the orchestrator writes `.devlyn/verify.pair.timeout.json` (`{"engine": "<codex|claude>", "budget_seconds": 600}`) before running `verify-merge-findings.py`. The orchestrator records `phases.verify.judge_durations_ms: {judge: <int>, pair_judge: <int|null>}` as it collects each judge result; durations never nest inside `sub_verdicts`. After primary and pair findings are written, run `python3 "$DEVLYN_SHARED_DIR/verify-merge-findings.py" --write-state`. Branch only on the merged `state.phases.verify.verdict`; a HIGH/CRITICAL finding from either judge must mechanically become `NEEDS_WORK`. Never write `.devlyn/verify-merged.findings.jsonl` or `.devlyn/verify-merge.summary.json` by hand; `verify-merge-findings.py` is their only writer. State write: `phases.verify.{started_at, verdict, completed_at, duration_ms, judge_durations_ms: {judge, pair_judge}, sub_verdicts: {mechanical, judge, pair_judge?}, artifacts}`.

Branch:
- `PASS` → PHASE 6.
- `PASS_WITH_ISSUES` (LOW severity only) → PHASE 6 with banner.
- `NEEDS_WORK` / `BLOCKED` → fix loop with `triggered_by: "verify"`. Spawn IMPLEMENT-engine agent with the verify findings, then run the common post-fix checkpoint with origin `verify`. Second `NEEDS_WORK` → halt with verdict `BLOCKED:verify-exhausted`.

## PHASE 6: FINAL REPORT + ARCHIVE

State write: `phases.final_report.started_at` at the top of this phase.

1. Kill any dev server PHASE 3 left running.

2. **FINISH GATE** — run `python3 "$DEVLYN_SHARED_DIR/finish-gate.py"`; branch only on exit code plus `.devlyn/finish-gate.findings.jsonl` existence: 0 without the file → clean; 0 with it → terminal verdict floors at `PASS_WITH_ISSUES` (report lists the reverted paths); 1 or 2 → `BLOCKED:finish-gate-unclean`.

3. **Terminal verdict** — derive from `state.phases.{plan, implement, surface_close, build_gate, cleanup, verify}.verdict` per the precedence rules in `references/state-schema.md#terminal-verdict`. Verify-only mode short-circuits to `state.phases.verify.verdict`.

4. **Render report** — sections: header (run_id, engine, mode, verdict, wall-time), per-phase summary (including SURFACE_CLOSE run or skip), pair/risk-probe status, findings table (verify + finish-gate findings), follow-up notes (the explicit line `pipeline continued to BUILD_GATE — surface_close_rolled_back_adjudication_malformed` when `continued_after_block` is set, any large-mode `## Assumptions` block, any pair-judge TIMEOUT (headline: solo verdict after pair TIMEOUT), any `--no-pair` / `--no-risk-probes` opt-out, any engine setup guidance after BLOCKED, `/devlyn:ideate` guidance after `BLOCKED:solo-headroom-hypothesis-required` that asks for the visible behavior `solo_claude` is expected to miss, and `/devlyn:ideate` guidance after `BLOCKED:solo-ceiling-avoidance-required` that asks for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`).

5. State write: `phases.final_report.{verdict, completed_at, duration_ms}` BEFORE archive runs (archive prune logic skips runs whose `final_report.verdict` is null).

6. **Archive** — invoke the deterministic script: `python3 "$DEVLYN_SHARED_DIR/archive_run.py"`. The script reads `run_id` from `.devlyn/pipeline.state.json`, moves the per-run artifact set (`PER_RUN_PATTERNS` in the script is the single source of truth) into `.devlyn/runs/<run_id>/`, then best-effort prunes to last 10 completed runs. Archive must run; running this step as deterministic-script-not-prose ensures the move actually happens (iter-0033a Smoke 3 caught a case where the agent claimed archive ran without moving the files).

## State management

`.devlyn/pipeline.state.json` is the single authoritative verdict source. Branch on `state.phases.<name>.verdict` directly; never parse `.devlyn/*.findings.jsonl` for routing decisions. Schema and write protocol: `references/state-schema.md`. Every "State write: `phases.X.{...}`" note above describes the resulting shape only — the orchestrator writes it via initial `spawn`, atomic `transition` for direct handoffs, or terminal `complete`; re-entry preserves the prior lifecycle in `history[]` (`references/state-schema.md#write-protocol`). Phase workers never edit `pipeline.state.json` directly.
