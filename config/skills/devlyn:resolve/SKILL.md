---
name: devlyn:resolve
description: Hands-free full pipeline for explicit resolve requests, formal specs, queue drains, material ambiguity, subsystem/design work, security/auth/payment/persistence/concurrency/public-API-contract changes, or no decisive acceptance check. Free-form goal or formal spec input. Plan → Implement → Build-gate → Cleanup → Verify (fresh subagent, findings-only). Mechanical-first verification; Verify dual-judge is default-when-available. Clear, local, reversible, low-risk conversational edits with decisive checks default to direct execution; explicit small resolve keeps the full workflow.
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
- Claude Code phases other than PLAN: spawn `Agent` (`mode: "bypassPermissions"`); prompt = adapter-header + canonical-body + task-context. PLAN uses the native foreground call shape in PHASE 1.
- Codex CLI phases: shell out via `bash "$CODEX_MONITORED_PATH"` with the same compounded prompt. Each `codex exec` child is a new session/fresh context. Write the compounded prompt to a file and set `DEVLYN_CODEX_PROMPT_FILE` with sole prompt argument `-`; the wrapper snapshots exact stdin bytes, seals transport evidence and emits a heartbeat. Without file transport stdin remains DEVNULL. No MCP. The wrapper call is foreground-blocking — never a background shell (`run_in_background`, `&`, `nohup`), never end your message while it runs: headless print-mode wind-down kills backgrounded children (0-byte delivery); the heartbeat is the observability channel.
- oh-my-pi phases: spawn the native `task` tool with a fresh `context` containing adapter-header + canonical-body + task-context. Capture the task result into `.devlyn/<phase>.stdout` and any tool error into `.devlyn/<phase>.stderr` before updating state. If the `task` tool is unavailable for an omp-routed phase, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable`; do not fall back to same-context execution or a nested `omp -p` subprocess.
- Default engine: Claude when the orchestrator has Claude Code’s native `Agent`; otherwise its own fresh worker. PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`. BUILD_GATE and probes retain their existing routes. `_shared/engine-preflight.md#role-resolution` defines the single resolver and explicit `--role-config` / project role precedence. Absent profiles preserve legacy `--engine` / executor / default behavior; VERIFY primary may be independently selected. Configured role/priority pins and flags fail closed on unavailable engine or failed authentication, including failures discovered at dispatch. Unconfigured automatic VERIFY selects an available OTHER engine.
- The `--engine` flag does not disable default pairing: the second judge uses the OTHER engine by default when available.
- Multi-LLM evolution: when a new model adapter ships in `_shared/adapters/`, that engine becomes selectable for the roles its adapter declares eligible without further skill changes (NORTH-STAR.md "Multi-LLM evolution direction").
</engine_routing>

<modes>
Three input shapes:

1. **Free-form**: `/devlyn:resolve "fix the login bug"` (inline goal) or `/devlyn:resolve --goal-file <path>` (goal text read from a file — the devlynd `ResolveAdapter` launcher path, injection-safe). PHASE 0 runs the complexity classifier and either proceeds with an internal mini-spec (trivial), drafts focused questions for in-prompt resolution (medium), or synthesizes a best-effort spec with a logged `## Assumptions` block (large; zero-scope-signal goals halt). No mid-pipeline prompts in any branch.
2. **Spec**: `/devlyn:resolve --spec docs/roadmap/phase-N/X.md`. Supplied specs and expected files are read-only inside resolve. Stage verification commands from sibling `spec.expected.json`; if absent, use the legacy `## Verification` JSON block.
3. **Verify-only**: `/devlyn:resolve --verify-only <diff-or-PR-ref> --spec <path>`. Skips PHASE 1-4. Runs PHASE 5 (VERIFY) on the supplied diff against the spec.
</modes>

<post_implement_invariant>
After `state.implement_passed_sha` is set: SURFACE_CLOSE and CLEANUP are limited to their allowlists (empty SURFACE_CLOSE PASS is valid; violations revert); VERIFY is fresh-context, findings-only, and mutation-free. No fresh VERIFY worker → `BLOCKED:fresh-context-unavailable`, never same-context review.
</post_implement_invariant>

<transition_protocol>
For every direct complete→spawn handoff, call `state-phase-write.py ... --phase <current> transition` with the current phase's normal completion/attestation arguments plus caller-specified `--next-phase`, `--next-round`, `--next-triggered-by`, `--next-engine`, `--next-model`, and any next-phase metadata. The verb validates a legal edge and commits both lifecycle writes atomically; it returns JSON state facts only. It never selects a phase/engine, renders a prompt, or spawns an agent. Use standalone `spawn` only for the initial post-bootstrap dispatch; use standalone `complete` when no next phase opens (including a halt).
</transition_protocol>

## PHASE 0: PARSE + CLASSIFY + ROUTE

Outer-owner boundary: before normal task writes, follow `references/task-completion.md` for prospective task-branch ownership (linked worktree optional) and `references/outer-loop.md` for owner-input commits. Existing branches cannot be retroactively adopted. Verify-only does not allocate or publish; phase workers never own delivery.

1. Run the bootstrap once with the exact tokenized `<pipeline_config>` and this orchestrator's default engine from `<engine_routing>`:

   ```bash
   DEVLYN_DEFAULT_ENGINE="<current-cli-default>" python3 "$DEVLYN_SHARED_DIR/resolve-bootstrap.py" <pipeline_config tokens>
   ```

   Read its sole JSON result. On `ok:false`, halt on its exact report-level `blocked` string and show `detail`; init failures create no phase verdict; crashes can leave owned residue, which bootstrap preserves and refuses to replace. Admission refusals require continuing the existing run through its owning session or starting in a distinct worktree. Never autoarchive to defeat a refusal; explicit manual archive is recovery only after the operator establishes that prior writers stopped. Valid completed runs still autoarchive normally, but a completed final report does not prove every interactive writer exited. On success, the script has atomically initialized the schema-v3 skeleton (`pair_verify: true` only when `--pair-verify` was passed), stamped the null-safe Claude session id, persisted exact-byte Goal/spec identity, staged spec verification inputs, and captured the verify-only external diff. It validates only flags needed for those init fields, including mode exclusivity, `--max-rounds`, `--bypass`, and `--pair-verify`/`--no-pair`; `--pair-verify` and `--no-pair` are mutually exclusive. Free-form init sets `state.source.type = "generated"`. Spec staging validates supported `complexity` frontmatter (including sibling spec `complexity` frontmatter) and any present actionable solo-headroom hypothesis, matching its command to `spec.expected.json.verification_commands[].cmd` or the inline `## Verification` JSON carrier. It stages and validates an explicit `--role-config` object into state with its path/digest, but does not resolve roles, write the untracked baseline, classify complexity/risk or announce. `state.engine` is the raw `--engine` value with `engine_source: "flag"`, otherwise the passed `DEVLYN_DEFAULT_ENGINE` with `engine_source: "default"`; step 2 resolves and replaces both fields.

2. Engine pre-flight: follow `_shared/engine-preflight.md`. Freeze the shared resolver once before any phase with `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --freeze-roles --default-engine "<current-cli-default>"`. It validates project/per-run roles and records `state.role_resolution`; legacy `state.engine`/`engine_source` remain the executor. Repeated reads return the same snapshot, never changed project settings. Keep availability/auth checks before each selected dispatch; explicit unavailable routes fail closed. These PHASE0 failures are report-level `BLOCKED:<reason>`; phase verdict carriers remain bare enums.

3. Write `.devlyn/untracked.baseline`: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --write-untracked-baseline`.

4. Read the Goal/spec through `state.source`. For free-form mode, run the deterministic classifier in `references/free-form-mode.md`. Zero-scope-signal goals halt with `BLOCKED:large-needs-ideation`; pair-evidence intent without an actionable solo-headroom hypothesis must halt with `BLOCKED:solo-headroom-hypothesis-required`; unmeasured pair-candidate intent without solo ceiling avoidance must halt with `BLOCKED:solo-ceiling-avoidance-required`. Follow the selected branch to write the trivial/medium/large body of `.devlyn/criteria.generated.md`, then set `state.complexity` and its raw-byte `criteria_sha256`. The Large `## Assumptions`/recommendation/final-report obligations remain unchanged.

   Compute `state.risk_profile` from the user goal plus spec/criteria text. Mark `high_risk: true` for auth/authz, permissions, security, token/session, payment/money/billing/invoice/pricing/tax/ledger, persistence/data mutation/deletion/migration, idempotency/replay/duplicate, API/webhook/raw-body/signature, allocation/scheduling/inventory/rollback/transaction, or explicit error-priority/output-shape contracts. Explicit `--risk-probes` sets both probe booleans true. Otherwise an automatic high-risk route enables probes only when the legacy executor’s OTHER engine (legacy pair priority/complement, independent of VERIFY profiles) is available and `--no-risk-probes` is absent; if unavailable, keep probes disabled and append `auto-risk-probes skipped: <engine>-unavailable`. `--no-pair` sets `pair_default_enabled: false`. Preserve strict boolean/list types and concise string reasons.

5. Announce one line: `resolve starting — run <run_id> — engine <engine> — mode <mode> — complexity <complexity-or-na> — pair <on|solo:auto_pair_other_engine_unavailable|disabled> — risk_probes <on|off>`.

6. Open the initial post-bootstrap span with standalone `state-phase-write.py ... spawn`: `plan` before its worker dispatch (normal run), or `verify` before MECHANICAL (verify-only). The bootstrap never chooses a phase, engine, branch, prompt, or agent.

### Explicit role dispatch

Use the frozen role entry and `role-config.py --state .devlyn/pipeline.state.json --role <worker|primary_judge|pair_judge> [--resolved-model <exact inherited model>]` before each affected dispatch. Keep model/effort values as individual argv elements. Replace that role's model/effort options, never append duplicates; omitted fields retain its current phase options. PLAN, BUILD_GATE, probes and SURFACE_CLOSE do not inherit worker/VERIFY profiles. A native option warning that ignores/rejects a requested field is BLOCKED even at exit0. Print requested values, source and channel before dispatch; report observed values only from validated evidence.

For a Codex worker with explicit effort, retain the exact wrapper arguments (excluding `bash` and the wrapper path) as `.devlyn/<phase>.argv.<round>.json` before launch. The wrapper's existing invocation receipt binds that array's canonical JSON hash; completion checks the requested effort against it. This adds no mutation receipt relaxation or new launcher.

For a judge with explicit model/effort, let `JUDGE_STEM=.devlyn/<engine>-judge.r<VERIFY-round>`. Retain the exact UTF-8 prompt as `$JUDGE_STEM.prompt` and complete dispatched argv array (including launcher) as `$JUDGE_STEM.argv.json`. Codex sets `DEVLYN_CODEX_PROMPT_FILE="$JUDGE_STEM.prompt"` and passes the sole prompt `-`; Claude uses `run-bounded.py 600 --stdin-file "$JUDGE_STEM.prompt" --record-transport -- claude -p` with no positional prompt. Preserve the generated `$JUDGE_STEM.prompt.transport.json`; it binds the snapshotted bytes and actual native argv, including wrapper-added isolation. Missing/mismatched transport evidence BLOCKs authentication; never fabricate the carrier. Codex uses the isolated read-only monitored route with timeout600 and redirects stdout/stderr to `$JUDGE_STEM.stdout`/`$JUDGE_STEM.stderr`. Claude uses the existing 600s `run-bounded.py` CLI route, `--tools Read,Grep,Glob --allowedTools Read,Grep,Glob --permission-mode dontAsk --setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}' --output-format json`; redirect raw JSON to `$JUDGE_STEM.output.json` and stderr to `$JUDGE_STEM.stderr`. Never substitute a Claude CLI worker for native Agent.

After the actual process exits, run `python3 "$DEVLYN_SHARED_DIR/judge-role-evidence.py" --devlyn-dir .devlyn --role <primary_judge|pair_judge> --exit-code <actual-exit>`. On failure preserve raw artifacts and BLOCK the source; never create successful evidence manually. On success it retains round-scoped evidence and produces canonical `.devlyn/<engine>-judge.stdout` (exact Claude result extraction, exact Codex stdout copy) for the unchanged findings collector. Merge revalidates/binds evidence and archives all bound originals, including prior rounds. Missing explicit judge evidence cannot become PASS. Unconfigured judge routes retain their existing capture format.

## PHASE 1: PLAN

Skip in verify-only mode. The heaviest phase by design — spec/criteria define non-negotiable invariants; plan formalizes how the implementation hits them.

Engine: PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`; Claude Code uses a native Claude `Agent` worker, while Codex CLI / oh-my-pi use their own fresh worker per `_shared/engine-preflight.md` (PLAN-pair is **research-only** — iter-0033d/f/g; unblock conditions in PHASE 1 / iter-0033g §H; iter-0020 falsified Codex-BUILD/IMPLEMENT, NOT PLAN-pair). Before rendering, assign the current orchestrator's literal adapter name (`PLAN_ENGINE=claude`, `PLAN_ENGINE=codex`, or `PLAN_ENGINE=omp`) and assign `PLAN_MODEL=<exact model id passed to that fresh worker>`; replace the metavalue and fail closed if either assignment is empty. Write the data-only task context to `.devlyn/plan.task-context` with `PLAN_WORKING_DIR="$(pwd -P)"`: its first two lines are exactly `Working directory: $PLAN_WORKING_DIR` and `Plan output: $PLAN_WORKING_DIR/.devlyn/plan.md`, followed by the task data. For round `PLAN_ROUND`, render adapter + `references/phases/plan.md` + task context without byte normalization to `PLAN_PROMPT_FILE=.devlyn/plan.prompt.$PLAN_ROUND`, and set `PLAN_PROMPT_SHA256="$(python3 "$DEVLYN_SHARED_DIR/phase-prompt-render.py" --adapter "$DEVLYN_SHARED_DIR/adapters/$PLAN_ENGINE.md" --canonical-body "$DEVLYN_SKILL_DIR/references/phases/plan.md" --task-context .devlyn/plan.task-context --output "$PLAN_PROMPT_FILE")"`. The renderer fails closed before writing the round-scoped prompt if either fixed header field is missing, non-absolute, or mismatches the active repository paths. Open round 0 with `state-phase-write.py ... --phase plan spawn --round 0 --engine "$PLAN_ENGINE" --model "$PLAN_MODEL" --prompt-sha256 "$PLAN_PROMPT_SHA256"`. In Claude Code, invoke the native `Agent` with its `prompt` field set to the exact `PLAN_PROMPT_FILE` bytes without appending a terminal LF (the renderer emits none), explicitly set `run_in_background: false`, and omit `mode`; this is a data field, so a path, `$(cat ...)`, or any variable-reference substitution is not the rendered prompt. If native input validation rejects this call, surface the failure without retrying a different `mode` or background shape and fail closed through the existing `BLOCKED:fresh-context-unavailable` path. The PLAN worker inherits the parent's permission context: the hands-free parent already uses native `bypassPermissions`, while a non-bypass parent's permission prompt remains the user's native boundary and is never silently escalated. A Codex CLI PLAN must pass explicit `-m "$PLAN_MODEL"` and the seven `DEVLYN_INVOCATION_*` values around `codex-monitored.sh`, using phase `plan`, `PLAN_ROUND`, `PLAN_WORKING_DIR`, `PLAN_PROMPT_FILE`, `PLAN_SESSION_FILE=.devlyn/plan.worker-session.$PLAN_ROUND.jsonl`, and `PLAN_RECEIPT_FILE=.devlyn/plan.invocation.$PLAN_ROUND.json`; invoke the wrapper as `DEVLYN_CODEX_PROMPT_FILE="$PLAN_PROMPT_FILE" bash "$CODEX_MONITORED_PATH" --json -C "$PLAN_WORKING_DIR" -s workspace-write -m "$PLAN_MODEL" -c sandbox_workspace_write.network_access=false <other options> - >"$PLAN_SESSION_FILE" 2>.devlyn/plan.stderr`, then pass that same session as `state-phase-write.py ... --engine-session-log "$PLAN_SESSION_FILE"` on completion/transition. The wrapper must write and finish the receipt around that direct capture; this state-bound receipt proves requested-model dispatch and prompt/session binding; effective model remains unknown, and a native model-reroute event blocks completion. oh-my-pi delivers the same prompt through its unchanged route. Product code records rendered intent; it never parses a transcript or intercepts, rewrites, wraps, or forces native delivery.

Subagent output (writes `.devlyn/plan.md`): file list to touch, risk list (out-of-scope expansions, ambiguous spec sections), acceptance restatement (what `## Verification` actually requires verbatim). For large work only, PLAN may add a fourth section `## Execution phases` under the conditions in `references/phases/plan.md`; a phase block missing a runnable `gate:` line disqualifies the whole section — treat the run as single-phase and log the disqualification.

State write: each PLAN receipt carries spawn-known `round`, `started_at`, `triggered_by`, `engine`, `model_requested`, and `prompt_sha256`; completion adds `completed_at`, `duration_ms`, `verdict`, nullable `model_effective`, and `output_sha256` under `references/state-schema.md`. Later mutations rehash bound output. Never edit PLAN to widen scope after completion; only the bounded PLAN re-spawn may replace its receipt.

After return:
1. If `.devlyn/plan.md` lists zero files → halt with verdict `BLOCKED:plan-empty`.
2. If risk list flags an out-of-scope expansion the user did not authorize → the sole legal corrective re-spawn is round 1: update the data-only task context, repeat render + digest into `.devlyn/plan.prompt.1`, open PLAN with `--round 1 --triggered-by plan` and the actual engine/model/digest, then deliver those exact prompt bytes using the same native or receipt-bound CLI call shape as round 0. A second failed plan halts; no further PLAN dispatch is authorized.
3. After any re-spawn above, if `state.risk_profile.risk_probes_enabled == true` and `state.risk_profile.risk_probes_explicit == false`, parse the `authorized_surface` array from the JSON block under `<!-- devlyn:authorized-surface -->`. For a well-formed string array, compute `probe_scale_small := len(authorized_surface) <= 2 AND no entry ends in "/**"`. If true, set `risk_probes_enabled = false`, leave `high_risk` unchanged, and append `auto-risk-probes demoted: plan surface small (<n> paths)` to `reasons` using the actual length. A missing or malformed block leaves probe state unchanged; BUILD_GATE owns its malformed-block failure.

## PHASE 1.5: RISK_PROBES

Skip unless `--risk-probes` is set OR `state.risk_profile.risk_probes_enabled`
is true. This phase is findings-as-executable-checks, not a second plan and not
debate. When it runs, the OTHER engine is required: if unavailable, halt with
`BLOCKED:<engine>-unavailable` plus setup guidance;
do not silently continue without probes. Reaching this halt means the route was
explicitly requested (`--risk-probes`) — an auto high-risk escalation toward an
unavailable OTHER engine was already gated off in PHASE 0 by leaving
`risk_probes_enabled: false`, so a single-engine high-risk run proceeds solo here.

Engine: OTHER engine from the legacy executor and legacy pair priority/complement; worker/VERIFY profiles do not reroute probes. Prompt body:
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
include `visible_text_names_exact_json_error_object` and
`asserts_exact_error_object`. Cart/pricing success probes should use
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
  `DEVLYN_CODEX_PROMPT_FILE="<probe-prompt-file>" CODEX_MONITORED_ISOLATED=1 bash "$CODEX_MONITORED_PATH" -C "$PWD" -s workspace-write -c sandbox_workspace_write.network_access=false -c model_reasoning_effort=high -`.
  Append `-c sandbox_workspace_write.network_access=true` only when a probe's visible Verification command requires a localhost service (for example, a DB test harness); never as a default.
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

Engine/model/effort: frozen `role_resolution.roles.worker`; obtain validated argv additions using `role-config.py --state .devlyn/pipeline.state.json --role worker --resolved-model <existing-exact-phase-model>`. Prompt body: `references/phases/implement.md`.

For every Codex-routed IMPLEMENT, BUILD_GATE, or CLEANUP spawn, render the exact
prompt to `.devlyn/<phase>.prompt.<round>`, pass its SHA-256 to `state-phase-write.py
spawn --prompt-sha256`, and invoke only through `codex-monitored.sh` with these
seven variables set to the active state identity:
`DEVLYN_INVOCATION_{RUN_ID,PHASE,ROUND,WORKDIR,PROMPT_FILE,SESSION_FILE,RECEIPT}`.
Set `DEVLYN_CODEX_PROMPT_FILE` to that same prompt file and pass sole prompt `-`; retain its generated `.transport.json` carrier.
The session and receipt paths are `.devlyn/<phase>.worker-session.<round>.jsonl`
and `.devlyn/<phase>.invocation.<round>.json`. These three paths are round-scoped
so a retry cannot overwrite earlier prompt/session evidence. Every invocation
must include `--json -m <model_requested>` and `-c sandbox_workspace_write.network_access=<true|false>`: exactly
`true` for BUILD_GATE and exactly `false` for PLAN, IMPLEMENT, and CLEANUP, so
user configuration cannot silently change the phase capability. Redirect wrapper stdout directly
to that session path. The wrapper rejects bypass/yolo flags and any sandbox other
than `workspace-write`. The receipt seals the requested model, sandbox, phase-scoped
network capability, prompt, terminal exit, and session digest; completion passes the
same canonical session via `--engine-session-log`. A missing/mismatched receipt
or same-round retry blocks. Respawn with a new round instead of replacing it.

State write: `phases.implement.{started_at, verdict, completed_at, duration_ms}`.

Before accepting an IMPLEMENT `PASS` / `PASS_WITH_ISSUES` completion or
transition, `state-phase-write.py` validates every sibling
`spec.expected.json.process_evidence[]` obligation for `phase: "implement"`,
rehashes its raw streams, and appends the validated carrier to
`state.process_evidence`. A missing, altered, escaping, duplicate, or
expectation-mismatched carrier blocks the checkpoint.

**Single-phase path** (plan.md has no `## Execution phases` section — every trivial/medium run, and any large run PLAN judged atomic): spawn IMPLEMENT once. No phase metadata of any kind appears in the prompt. After return:
1. `git diff --stat` — empty diff → halt with `BLOCKED:implement-empty`.
2. Checkpoint (**scoped staging** — this exact shape everywhere a pipeline commit is made): `bash -o pipefail -c 'python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --print-authorized-surface | git add --pathspec-from-file=- --pathspec-file-nul' && git commit -m "chore(pipeline): implement"`.
3. After the checkpoint succeeds, set `state.implement_passed_sha = git rev-parse HEAD` before downstream phases (activates `<post_implement_invariant>`).

**Phase-gated path** (plan.md has `## Execution phases` with >1 phase): definitions are the contract in plan.md; progress is routing truth in `state.phases.implement.exec = { total, current, statuses, commits }` — never route on plan.md checkbox parsing. For each phase k = 1..N:
1. Spawn IMPLEMENT with the standard prompt plus: this phase's plan.md block only, the current worktree as the working base (overrides the body's `base_ref.sha` framing after phase 1), a `git diff <base_ref.sha>...HEAD --stat` summary, and the prior phase's gate output.
2. After return: run the phase's `gate:` commands directly — deterministic, exit-code truth, no LLM judgment.
3. Gate PASS → scoped-staging checkpoint with message `chore(pipeline): implement phase <k>/<N>`, write `exec.statuses[k-1] = "PASS"` + commit sha, advance `exec.current`, tick the plan.md checkbox mirror (display only).
4. Gate FAIL → no commit. One fix respawn for this phase with the gate output (increments `rounds.global`, shares `max_rounds`); second FAIL → `exec.statuses[k-1] = "FAIL"`, halt with `BLOCKED:phase-gate-exhausted`.

After the final phase's gate PASS: `git diff <base_ref.sha>...HEAD --stat` — empty → halt with `BLOCKED:implement-empty`; otherwise set `state.implement_passed_sha = git rev-parse HEAD` (phase commits already checkpoint the work — no extra commit).

## PHASE 2.5: SURFACE_CLOSE

Run once iff `state.source.type == "generated"` and complexity is trivial/medium. Engine is Claude always, pair-judge-routed; executor flag/pin ignored. Per `_shared/engine-preflight.md`, unavailability skips via `surface-skip`, reports `auto_surface_close_claude_unavailable`, never BLOCKs/reroutes.

Freeze `.devlyn/surface-close.input.patch`; assemble Claude adapter + `references/phases/surface-close.md` canonical body VERBATIM + data-only Goal/patch/hashes/surface/commands; write the exact bytes to `.devlyn/surface-close.prompt.<round>`, hash them and spawn with `--tools "Read,Grep,Glob,Edit,Write" --dangerously-skip-permissions --output-format json --strict-mcp-config --mcp-config '{"mcpServers":{}}'`, omitting `--model` at SPW spawn to inherit native Claude model settings. Record the effective model from the native JSON result. Use no positional prompt on the CLI route and retain its generated transport carrier. Bound at 600s (native or `run-bounded.py 600 --stdin-file .devlyn/surface-close.prompt.<round> --record-transport -- claude -p`), else block pre-spawn. Save raw stdout as `.devlyn/surface-close.output.json`, extract its `result` string to `.devlyn/surface-close.stdout`, retain `.devlyn/surface-close.worker-session.<round>.jsonl`, and complete with `.devlyn/surface-close.output.json` as `--engine-session-log`; non-JSON/missing result follows the existing failure path. Workers execute nothing; `surface-check` gates rows, citations, scope, and execution. Empty PASS completes; authorized delta is scoped-staged and committed. Only `BLOCKED:surface-close-adjudication-malformed` runs `surface-adjudication-recover --authorized-surface-json <array>`, whose successful rollback and transcript Edit/Write audit complete the nonterminal skip carrier and continue to BUILD_GATE. Timeout, input/prompt mismatch, attestation failure, execution-audit violation, and out-of-surface delta run `surface-rollback`, complete bare `BLOCKED`, and halt; rollback failure also halts. One shot; no `max_rounds`.

**Common post-fix checkpoint (BUILD_GATE and VERIFY):** After fix IMPLEMENT returns, increment `state.rounds.global`; scoped-stage the authorized surface and commit `chore(pipeline): implement fix round <n>`; run `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase implement durability-enforce --round <n> --origin-phase <build_gate|verify>`. Its receipt must PASS before re-entry, which enforces it again before VERIFY artifact clearing or phase spawn.

## PHASE 3: BUILD_GATE

Skip in verify-only mode OR when `build-gate` in `state.bypasses`. Deterministic — same commands CI / Docker / production run.

Spawn the resolved BUILD_GATE engine through the fresh-worker route in
`<engine_routing>` with prompt body `references/phases/build-gate.md`. A Codex
route must inherit CI-equivalent capabilities from the parent invocation; it
must not add isolation, narrow the sandbox, or widen permissions inside the
worker. Invoke a Codex BUILD_GATE with
`-s workspace-write -c sandbox_workspace_write.network_access=true`; the
receipt rejects a missing, false, duplicate, or non-BUILD_GATE network override
before the worker starts. This retains the write sandbox while allowing the
loopback and network operations exercised by CI-equivalent gates. If an
authoritative route/tool response denies a required filesystem,
subprocess, loopback, PTY, or network operation, preserve that denial through
the BUILD_GATE process-evidence manifest and complete the phase as
`BLOCKED:build-env-underprovisioned`, not as a product finding or substitute
command. The worker:
1. Detects language/framework via project files (`package.json`, `pyproject.toml`, etc.).
2. Runs language-specific gates (tsc / lint / test), deferring exact literal overlaps under `references/phases/build-gate.md`'s current-contract/current-round rule; task-context prompts must preserve that rule.
3. Always runs `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` (verification_commands literal-match plus `.devlyn/risk-probes.jsonl` when present). If `state.risk_profile.risk_probes_enabled == true`, the script requires `.devlyn/risk-probes.jsonl`; a missing file is a CRITICAL mechanical blocker, not a silent solo run. The script routes each command through `process-evidence.py`; preserve `.devlyn/spec-verify.results.json` and its validated BUILD_GATE carrier for the state-bound archive flow.
4. If diff touches web-surface files: run the browser tier with the repo's available toolchain (for example Playwright or curl).
5. Emits `.devlyn/build_gate.findings.jsonl` + `.devlyn/build_gate.log.md`.

State write: `phases.build_gate.{started_at, verdict, completed_at, duration_ms, artifacts}`.

Branch:
- `PASS` → PHASE 4.
- `FAIL` → before product repair, halt with report-level `BLOCKED:required-tools-unavailable` only if a parent probe confirms the failed invocation's external gate tool is absent, unchanged `state.base_ref.sha` configuration requires it, and cited explicit task/spec constraints prohibit supplying it through any authorized route. Derive the tool from that configuration and invocation, never diagnostic text; bind the probe's interpreter, work root and normalized child environment to the runner call sites and actual gate invocation, not parent PATH or a manifest command string alone. An available authorized tool route, product-module/configuration failure, changed tool configuration, permitted or unspecified supply, or uncertain probe/identity/environment retains the fix loop. A confirmed prohibited-tool blocker wins even with other product findings: leave them unrepaired and preserve phase `FAIL`, findings, raw streams and sealed manifests unchanged. Record the probe and constraint citation separately in parent halt evidence; no repair means no round increment. Otherwise spawn IMPLEMENT-engine agent with the build_gate findings as input, then run the common post-fix checkpoint with origin `build_gate`. On second FAIL with `state.rounds.global >= state.rounds.max_rounds` → halt with verdict `BLOCKED:build-gate-exhausted`.
- `BLOCKED:build-env-underprovisioned` → halt immediately with the denied operation, original command, and process-evidence manifest/id; do not enter the product fix loop.

## PHASE 4: CLEANUP

Skip if `cleanup` in `state.bypasses`. Task-scoped pass.

Engine/model/effort: the same frozen worker profile, with validated role-config argv additions. Prompt body: `references/phases/cleanup.md`. Allowlist enforced post-spawn:
- Tooling artifacts the spec did not list as deliverables (`test-results/`, `playwright-report/`, `.last-run.json`, coverage HTML).
- Dead code added by this diff (not pre-existing dead code).
- Doc references whose target this diff renamed or removed.

Before spawn: pass `--pre-sha "$(git rev-parse HEAD)"` to the `state-phase-write.py ... spawn` call for this phase.

State write: `phases.cleanup.{started_at, verdict, completed_at, duration_ms, pre_sha, post_sha}`.

After return:
1. Run `git diff --name-only <pre_sha>` and compare new untracked files against `.devlyn/untracked.baseline` (`.devlyn/` exempt) — any path outside the cleanup allowlist (including a cleanup-created untracked file) → revert to `pre_sha`, delete the unauthorized untracked file, and emit `invariant.cleanup-out-of-scope` into `.devlyn/cleanup.findings.jsonl`.
2. If allowlist honored and diff non-empty: `git add -u && git commit -m "chore(pipeline): cleanup"`.
3. Transition CLEANUP→VERIFY through `<transition_protocol>` with `--post-sha "$(git rev-parse HEAD)"` (also when the diff was empty), preserving completion/session arguments and the next-phase identity below.

## PHASE 5: VERIFY (fresh subagent, findings-only)

Independent quality layer. MECHANICAL runs first on the post-CLEANUP code. Each
JUDGE is then **spawned with empty conversation context** — no carry-over from
PHASE 1-4 — and receives only `spec.md` (or
`.devlyn/criteria.generated.md`), sibling `spec.expected.json`, the cumulative
diff, the source hash, `.devlyn/spec-verify.results.json`, and the validated
VERIFY process-evidence manifest/raw streams named by that results carrier. The
fresh-context spawn plus immutable evidence inputs are the structural guarantee
of independence.

Before MECHANICAL, open VERIFY with frozen `role_resolution.roles.primary_judge`; without a profile it follows the legacy executor. Use that engine/model and the current round/trigger metadata in the predecessor's `<transition_protocol>` handoff, including bypass and repair paths; initial verify-only uses PHASE 0's standalone spawn. This records the phase span, not a judge invocation, and requires no rendered judge prompt or prompt digest.

Two sub-phases:

1. **MECHANICAL** (deterministic, orchestrator-owned): re-run `SPEC_VERIFY_PHASE=verify_mechanical SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` against the post-CLEANUP code (independent of BUILD_GATE's earlier run). If `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker. This emits `.devlyn/verify-mechanical.findings.jsonl` plus `.devlyn/spec-verify.results.json` with the VERIFY process-evidence carrier. Validate that carrier and all named raw streams before JUDGE spawn; a verdict-binding blocker skips both judges.

2. **JUDGE** (fresh-context Agent): grade the diff against the spec on rubric axes (spec compliance, scope, quality, consistency). Split each Requirement into binding clauses and trace code-order counterexamples; a passing sealed result proves only the case it exercises, not neighboring `once` / `regardless` / `duplicate` / auth-order / rollback invariants. Respect scope qualifiers such as `inside a warehouse`, `per resource`, `for this line`, and `after validation`; do not widen a scoped clause into a global invariant, and compose multiple ordering rules in the stated order. For stateful flows, explicitly trace failed-operation rollback and the next entity's state. For high-complexity specs, review at least one interaction counterexample that combines ordering/priority with failure handling and state mutation against the implementation and sealed MECHANICAL results. JUDGE never executes literal verification, lint, test, build, risk-probe, or newly invented interaction commands; missing executable coverage is a finding against the expected contract/risk probes. After MECHANICAL passes, `--no-pair` continues solo with `user_no_pair`. Otherwise use the frozen pair profile/priority resolved against the primary. An unavailable OTHER engine or failed authentication blocks `--pair-verify` and configured pair role/priority pins; only an unconfigured automatic route records `auto_pair_other_engine_unavailable` and continues solo.

When the OTHER engine is available, persist `pair_trigger` before spawn with `pair.default` plus every applicable outcome-independent reason, then dispatch both judges concurrently against the same frozen diff and sealed MECHANICAL evidence via foreground parallel dispatch, never background shells. A primary blocker never cancels the pair judge. If foreground parallel dispatch is unavailable, run the same two required judges sequentially; this changes dispatch shape only and never permits outcome-dependent escalation or a pair skip.

Keep the existing reasons as telemetry: `mode.verify-only`, `mode.pair-verify`, `complexity.high`, `complexity.large`, `spec.complexity.high`, `spec.complexity.large`, `spec.solo_headroom_hypothesis`, `risk.high`, `risk_probes.enabled`, `risk_probes.present`, `coverage.failed`, `mechanical.warning`, and `judge.warning`. Append the outcome-dependent reasons only after both judges return. Eligible schema-v3 state must include `pair.default`; all other applicable reasons remain completeness-checked. Malformed risk or trigger state BLOCKs VERIFY.

Pair-mode JUDGE: spawn a second Agent with the OTHER engine's adapter; the second judge is a bounded adversarial complement, not a duplicate broad audit. The primary judge owns broad coverage; pair-JUDGE reviews the two highest-risk explicit `## Verification` bullets that cross state mutation, all-or-nothing rollback, ordering, idempotency, auth, or error-priority clauses. If the spec includes a solo-headroom hypothesis, one targeted review must use the hypothesis's backticked observable command as the exact anchor and inspect its complete sealed result (exit/stdout/stderr plus the full parsed output object). It must not read `.claude/skills`, `.codex/skills`, `CLAUDE.md`, `AGENTS.md`, or other harness docs unless the orchestrator pasted a specific excerpt into the prompt. It may use only the spec, diff, implementation files, tests, and sealed MECHANICAL evidence. It performs at most two targeted reviews before first output; inspection remains read-only. When the spec names exact keys, row shapes, JSON object shape, or an exact error body, pair-JUDGE compares the sealed parsed key sets/deep equality so aliased keys, missing keys, and extra keys are verdict-binding failures. For priority/stateful specs, trace code order for an earlier input entity that would succeed under input-order processing, a later higher-priority entity that consumes or blocks the critical resource, and a failure/blocked/rollback edge that determines a later entity's state. Scope qualifiers are binding: pair-JUDGE must not reinterpret `inside a warehouse`, `per resource`, or line-scoped rules as global rules. When both priority ordering and rollback/blocked-interval behavior appear in the spec, this dominance-loss review comes first: trace whether the earlier lower-priority entity loses because the later higher-priority entity is processed first, whether a failed/blocked middle entity leaves later state intact, and whether the sealed evidence covers complete accepted/scheduled and rejected output ordering. Missing executable coverage is a verdict-binding coverage finding; JUDGE does not invent or run the missing scenario. Pair-JUDGE output: emit JSONL findings then a bare terminal verdict line, or emit only `PASS` when clean. `_shared/judge-output-parser.py` is the single acceptance rule for pair output: JSONL findings, then a `# SUMMARY {json}` line or a bare verdict line (`PASS` alone when clean); it ignores bare code-fence lines and unwraps the registered Codex JSON envelope including its narrated-preamble recovery (iter-0082), and binds a whole-message NDJSON capture only through its uniquely attested terminal `end_turn` assistant message (iter-0106); every other non-empty line blocks the pair source. Both judgments merge with the rule "any HIGH/CRITICAL finding is verdict-binding; any MEDIUM with literal `verdict_binding: true` is also binding, regardless of confidence." Demonstrated applicable mandatory-clause violations, including unmet new requirements and incorrect customer documentation, must use one of those binding forms. Apply the canonical VERIFY clause/evidence and advisory boundaries; impact, rarity or pre-existing origin alone does not excuse an applicable violation. Cross-model disagreement on advisory lower-severity findings is logged but does not change the verdict. A primary JUDGE verdict-binding finding on a concurrent run does not cancel or discard the pair-JUDGE; both finding sets join the same fix round, and the merged verdict remains the worst source verdict without vote counting. `primary_judge_blocker` is parser-recognized only for archived v2.0 replay; new runs never write it. A verdict-binding MECHANICAL blocker still skips both judges and records `pair_judge: null`.

If the OTHER engine is unavailable, only unconfigured automatic VERIFY records
`auto_pair_other_engine_unavailable` and continues solo. Explicit `--pair-verify`,
pair profiles and priority pins instead set VERIFY to `BLOCKED:<engine>-unavailable`, preserves the failed
check, and prints setup guidance: install/configure the missing CLI, complete
its auth/login flow, verify `<engine> --version`, then rerun. `--no-pair` is only
for an intentional solo run.

For policy-denied Windows Codex judge reads, prepare the complete inline evidence packet from `_shared/codex-config.md#constrained-windows-judge-reads` for each fresh judge, explicitly instructing no tools. Missing inputs produce a verdict-binding BLOCKED finding; sandbox, isolation, model/effort and 600s bounds remain unchanged.

Findings are written to `.devlyn/verify.findings.jsonl`. **Except on the supplied no-tools route, VERIFY agents may inspect authorized source, diff and sealed evidence using native read/search tools or non-mutating shell commands. They must not mutate files or execute verification, lint, test, build, probe or invented-scenario commands.** Capture the primary reply as `.devlyn/<primary-engine>-judge.stdout` and its stderr sibling; never use the generic `.devlyn/verify-judge.stdout`. A Codex primary-JUDGE uses the distinct route `DEVLYN_CODEX_PROMPT_FILE="<primary-prompt-file>" CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600 bash "$CODEX_MONITORED_PATH" -C "$PWD" -s read-only -c model_reasoning_effort=high - >.devlyn/codex-judge.stdout 2>.devlyn/codex-judge.stderr`: omit `-m` only without an explicit model; an explicit profile supplies the validated model/effort additions below. Omit bypass flags and capture both streams directly without pipes. On primary exit 124, write `.devlyn/verify.primary.timeout.json` with exactly `{"engine": "<resolved-primary-engine>", "budget_seconds": 600}` before merge. A malformed marker BLOCKs; a valid marker preserves canonical primary findings and floors `judge` at `BLOCKED` even when output is empty, never `PASS`, a solo verdict, or pair-style `TIMEOUT`. Without the marker, existing required-primary failure behavior is unchanged. For Codex pair-JUDGE, set `DEVLYN_CODEX_PROMPT_FILE="<pair-prompt-file>"` with sole prompt `-` and keep the read-only `codex-monitored.sh` route with `CODEX_MONITORED_ISOLATED=1 CODEX_MONITORED_TIMEOUT_SEC=600` and `-c model_reasoning_effort=medium`, no `tail`/`head`/`grep` pipes, and direct stdout/stderr capture; every other resolved OTHER engine follows `_shared/adapters/<name>.md` `## Invocation`. Capture the pair reply as `.devlyn/<other-engine>-judge.stdout`, then run `python3 "$DEVLYN_SHARED_DIR/collect-codex-findings.py" --devlyn-dir "<abs repo>/.devlyn" --stdout-file <other-engine>-judge.stdout` before merge. Raw stdout is diagnostic-only. A non-zero collector exit must write no canonical `.devlyn/verify.pair.findings.jsonl`; set the pair source to `BLOCKED` for `verify.pair.emission-contract` and never merge as though unparsed stdout were only a diagnostic. VERIFY prompts remain bounded, read-only, and must not ask the judge to edit `.devlyn`. On pair-JUDGE subprocess exit 124, write `.devlyn/verify.pair.timeout.json` with `{"engine": "<resolved name>", "budget_seconds": 600}` before merge. With that marker, a capture the parser rejects solely because its message stream was truncated before the terminal result stays `TIMEOUT`; every other parser rejection stays `BLOCKED`. The orchestrator records `phases.verify.judge_durations_ms: {judge: <int>, pair_judge: <int|null>}` as it collects each judge result; durations never nest inside `sub_verdicts`. After primary and pair findings are written, run `python3 "$DEVLYN_SHARED_DIR/verify-merge-findings.py" --write-state`; it rehashes and binds the VERIFY process-evidence carrier before merging. Branch only on the merged `state.phases.verify.verdict`; a HIGH/CRITICAL finding from either judge must mechanically become `NEEDS_WORK`. Never write `.devlyn/verify-merged.findings.jsonl` or `.devlyn/verify-merge.summary.json` by hand; `verify-merge-findings.py` is their only writer. State write: `phases.verify.{started_at, verdict, completed_at, duration_ms, judge_durations_ms: {judge, pair_judge}, sub_verdicts: {mechanical, judge, pair_judge?}, artifacts}`.

Branch:
- `PASS` → PHASE 6.
- `PASS_WITH_ISSUES` (no verdict-binding findings) → PHASE 6 with banner.
- `NEEDS_WORK` / `BLOCKED` → fix loop with `triggered_by: "verify"`. Spawn IMPLEMENT-engine agent with the verify findings, then run the common post-fix checkpoint with origin `verify`. Second `NEEDS_WORK` → halt with verdict `BLOCKED:verify-exhausted`.

## PHASE 6: FINAL REPORT + ARCHIVE

Open the `final_report` span through the predecessor's `state-phase-write.py --devlyn-dir .devlyn --phase <predecessor> transition --next-phase final_report --next-round 0 …` on a direct handoff; after a halt, use standalone `state-phase-write.py --devlyn-dir .devlyn --phase final_report spawn --round 0` only if the span is unopened.

1. Kill any dev server PHASE 3 left running.

2. **FINISH GATE** — run `python3 "$DEVLYN_SHARED_DIR/finish-gate.py"`; branch only on exit code: 0 → clean; 1 or 2 → `BLOCKED:finish-gate-unclean`, and report the `.devlyn/finish-gate.findings.jsonl` listing, including reverted paths. Offenders exit 2 even when every revert succeeded — a silent revert must never ride an exit-0 pass.

3. **Terminal verdict** — derive from `state.phases.{plan, implement, surface_close, build_gate, cleanup, verify}.verdict` per the precedence rules in `references/state-schema.md#terminal-verdict`. Verify-only mode short-circuits to `state.phases.verify.verdict`.

4. **Render report to `.devlyn/final-report.md` before completion** — first line exactly `<!-- devlyn:final-report run_id=<current state.run_id> -->`, once only, followed by a nonempty report body. Sections: header (run_id, engine, mode, verdict, wall-time), per-phase summary (including SURFACE_CLOSE run or skip), pair/risk-probe status, findings table (verify + finish-gate findings), follow-up notes (the explicit line `pipeline continued to BUILD_GATE — surface_close_rolled_back_adjudication_malformed` when `continued_after_block` is set, any large-mode `## Assumptions` block, any pair-judge TIMEOUT (headline: solo verdict after pair TIMEOUT), any `--no-pair` / `--no-risk-probes` opt-out, any engine setup guidance after BLOCKED, `/devlyn:ideate` guidance after `BLOCKED:solo-headroom-hypothesis-required` that asks for the visible behavior `solo_claude` is expected to miss, and `/devlyn:ideate` guidance after `BLOCKED:solo-ceiling-avoidance-required` that asks for the concrete difference from rejected or solo-saturated controls such as `S2`-`S6`). User-facing text may follow archive; it cannot substitute for this file.

5. Complete the span with `state-phase-write.py --devlyn-dir .devlyn --phase final_report complete --verdict <bare enum> --log-file .devlyn/final-report.md` — the enum class of the terminal verdict (`BLOCKED:<reason>` → `BLOCKED`; `NEEDS_WORK` / `PASS_WITH_ISSUES` / `PASS` unchanged) — BEFORE archive runs (archive prune skips runs whose `final_report.verdict` is null). The writer validates the canonical nonsymlink regular file, current run marker and nonempty body, then binds its exact bytes; validation failure leaves the phase open. Never hand-edit lifecycle fields in `pipeline.state.json` (`references/state-schema.md` § Write protocol).

6. **Archive** — invoke the deterministic script: `python3 "$DEVLYN_SHARED_DIR/archive_run.py"`. The script reads `run_id` from `.devlyn/pipeline.state.json`, moves the static per-run artifact set (`PER_RUN_PATTERNS` remains the single ownership list) plus every state-bound process-evidence manifest/raw stream into `.devlyn/runs/<run_id>/`, preserves evidence-relative layout, and rehashes bound bytes before any move. An unsafe/missing/altered evidence path or destination collision reports archive failure without changing the already-derived product verdict. It then best-effort prunes to the last 10 completed runs. Archive must run; running this step as deterministic-script-not-prose ensures the move actually happens (iter-0033a Smoke 3 caught a case where the agent claimed archive ran without moving the files).

After successful normal-run archive, return to the outer owner for `references/task-completion.md`. A queue owner first commits its terminal queue transition, then completes once. Honor local-only/no-push; report delivery pending/failure separately from the archived product verdict. This is outside the phase graph.

## State management

`.devlyn/pipeline.state.json` is the single authoritative verdict source. Branch on `state.phases.<name>.verdict` directly; never parse `.devlyn/*.findings.jsonl` for routing decisions. Schema and write protocol: `references/state-schema.md`. Every "State write: `phases.X.{...}`" note above describes the resulting shape only — the orchestrator writes it via initial `spawn`, atomic `transition` for direct handoffs, or terminal `complete`; re-entry preserves the prior lifecycle in `history[]` (`references/state-schema.md#write-protocol`). Phase workers never edit `pipeline.state.json` directly.
