---
name: devlyn-resolve
description: Default to direct work after inspecting scope and verification, including bounded multi-file changes. Use full resolve for explicit resolve/spec-mode requests, queue drains, or concrete interacting requirements or verification too complex for the current context. Domain labels, file count, spec documents and quoted skill paths alone do not trigger it. Investigate or clarify missing intent/access first. Explicit small resolve retains all phases and independent verification. Verify dual-judge is default-when-available.
---

The current CLI owns PHASE 0, state transitions, Git checkpoints and final report/archive. Spawn the canonical phase workers from this process; never delegate the whole run to another parent orchestrator. VERIFY uses a fresh, findings-only worker.

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
5. Halt only on unrecoverable worker failure, empty IMPLEMENT, refused shared repair admission or VERIFY BLOCKED, or SURFACE_CLOSE timeout / input-or-prompt mismatch / attestation failure / execution-audit violation / out-of-surface delta / rollback failure; adjudication-malformed SURFACE_CLOSE continues after successful rollback plus transcript write-audit; otherwise continue.
</autonomy_contract>

<harness_principles>
Every phase applies Subtractive-first / Goal-locked / No-workaround / Evidence, loaded by file or inline; Codex routes receive it inline.
</harness_principles>

<runtime_paths>
Before PHASE 0 or any phase command, establish the bindings below.

Resolve bundled resources from the SKILL.md loaded for this invocation.

Reader-rendered directory hint:
```text
${CLAUDE_SKILL_DIR}
```

Treat the hint as literal path data, never shell code. If the reader
replaced it with an absolute directory, use that directory. Otherwise
use the filesystem path or base directory reported for this loaded
SKILL.md. Resolve virtual URIs through the reader's native filesystem
mapping. If available source locations name different directories,
stop.

Bind DEVLYN_SKILL_DIR to that absolute directory. Do not obtain this
binding from an environment variable, cwd, or another installation.
Verify its SKILL.md before proceeding. Missing or conflicting source
identity is BLOCKED:skill-source-unresolved; include the failed path
when known.

Resolve bundled references against this directory. These bindings are
workflow values: establish them explicitly using each tool or shell's
literal-path rules, and include their absolute values in every fresh
worker's prompt, telling it to set them from those values, never from
its inherited environment. Do not rely on shell state surviving between
calls.

Resolve directory symlinks on DEVLYN_SKILL_DIR before deriving its
sibling _shared. Bind that directory as DEVLYN_SHARED_DIR. References
written as _shared/... use this binding. Verify the directory and each
required resource before use; failure is BLOCKED:shared-dir-unresolved
with the failed path. Never search another installation.

Bind CODEX_MONITORED_PATH to DEVLYN_SHARED_DIR/codex-monitored.sh and verify that file before proceeding. Pass DEVLYN_SKILL_DIR, DEVLYN_SHARED_DIR, and CODEX_MONITORED_PATH explicitly to every fresh phase worker. In omp, when this skill was selected by name, resolve it with `printf '%s\n' skill://devlyn-resolve` in its Bash tool.
</runtime_paths>

<engine_routing>
Each model-invoked phase routes to an engine and prepends the per-engine adapter header from `_shared/adapters/<engine>.md` (e.g. `claude.md`, `codex.md`) to the canonical phase body. Adapter is the per-model delta (Anthropic's prompt-engineering guide for Claude, OpenAI's prompt guidance for Codex). Canonical body is engine-agnostic.

- PLAN runs in the owner context; BUILD_GATE and CLEANUP run orchestrator commands with no separate model. The selected IMPLEMENT worker also owns code/doc cleanup before its final checkpoint. IMPLEMENT and VERIFY still require fresh workers. If the current CLI cannot spawn a required worker, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable` with the failed spawn command; do not continue with ad-hoc same-context execution.
- Claude Code model-invoked phases other than VERIFY: spawn `Agent` (`mode: "bypassPermissions"`); prompt = adapter-header + canonical-body + task-context.
- Codex CLI model-invoked phases: shell out via `bash "$CODEX_MONITORED_PATH"` with the same compounded prompt. Each `codex exec` child is a new session/fresh context. Write the compounded prompt to a file and set `DEVLYN_CODEX_PROMPT_FILE` with sole prompt argument `-`; the wrapper snapshots exact stdin bytes, seals transport evidence and emits a heartbeat. Without file transport stdin remains DEVNULL. No MCP. The wrapper call is foreground-blocking — never a background shell (`run_in_background`, `&`, `nohup`), never end your message while it runs: headless print-mode wind-down kills backgrounded children (0-byte delivery); the heartbeat is the observability channel.
- oh-my-pi model-invoked phases other than VERIFY: spawn the native `task` tool with a fresh `context` containing adapter-header + canonical-body + task-context. Capture the task result into `.devlyn/<phase>.stdout` and any tool error into `.devlyn/<phase>.stderr` before updating state. If the `task` tool is unavailable for an omp-routed phase, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable`; do not fall back to same-context execution or a nested `omp -p` subprocess.
- Default engine: Claude when the orchestrator has Claude Code’s native `Agent`; otherwise its own fresh worker. PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`. BUILD_GATE runs orchestrator commands; probes retain their existing routes. `_shared/engine-preflight.md#role-resolution` defines the single resolver and explicit `--role-config` / project role precedence. Absent profiles preserve legacy `--engine` / executor / default behavior; VERIFY primary may be independently selected. Configured role/priority pins and flags fail closed on unavailable engine or failed authentication, including failures discovered at dispatch. Unconfigured automatic VERIFY selects an available OTHER engine.
- The `--engine` flag does not disable default pairing: the second judge uses the OTHER engine by default when available.
- VERIFY judges: `verify-judges.py` launches both seats from any orchestrator (Claude through `claude -p`, Codex through the monitored route); other engines are unsupported judge seats.
- Multi-LLM evolution: when a new model adapter ships in `_shared/adapters/`, that engine becomes selectable for the worker role its adapter declares eligible without further skill changes; a judge seat also needs a `verify-judges.py` route (NORTH-STAR.md "Multi-LLM evolution direction").
</engine_routing>

<modes>
Three input shapes:

1. **Free-form**: `/devlyn-resolve "fix the login bug"` (inline goal) or `/devlyn-resolve --goal-file <path>` (goal text read from a file — the devlynd `ResolveAdapter` launcher path, injection-safe). PHASE 0 runs the complexity classifier and either proceeds with an internal mini-spec (trivial), drafts focused questions for in-prompt resolution (medium), or synthesizes a best-effort spec with a logged `## Assumptions` block (large; zero-scope-signal goals halt). No mid-pipeline prompts in any branch.
2. **Spec**: `/devlyn-resolve --spec docs/roadmap/phase-N/X.md`. Supplied specs and expected files are read-only inside resolve. Stage verification commands from sibling `spec.expected.json`; if absent, use the legacy `## Verification` JSON block.
3. **Verify-only**: `/devlyn-resolve --verify-only <diff-or-PR-ref> --spec <path>`. Skips PHASE 1-4. Runs PHASE 5 (VERIFY) on the supplied diff against the spec.
</modes>

<post_implement_invariant>
After `state.implement_passed_sha` is set: SURFACE_CLOSE and CLEANUP are limited to their allowlists (empty SURFACE_CLOSE PASS is valid; violations revert); VERIFY is fresh-context, findings-only, and mutation-free. No fresh VERIFY worker → `BLOCKED:fresh-context-unavailable`, never same-context review.
</post_implement_invariant>

<transition_protocol>
For every direct complete→spawn handoff, call `state-phase-write.py ... --phase <current> transition` with the current phase's normal completion/attestation arguments plus caller-specified `--next-phase`, `--next-round`, `--next-triggered-by`, `--next-engine`, `--next-model`, and any next-phase metadata. For owner PLAN/BUILD_GATE/CLEANUP, omit engine/model/prompt/session arguments. PLAN records `execution_kind: "orchestrator_context"`; BUILD_GATE/CLEANUP record `execution_kind: "orchestrator_commands"`, all with null worker identity. Existing metadata-bearing PLAN/CLEANUP and already-open absent-kind BUILD spans retain historical worker validation; never relabel their evidence. The verb validates a legal edge and commits both lifecycle writes atomically; it returns JSON state facts only. It never selects a phase/engine, renders a prompt, or spawns an agent. Use standalone `spawn` only for the initial post-bootstrap dispatch; use standalone `complete` when no next phase opens (including a halt).
</transition_protocol>

## PHASE 0: PARSE + CLASSIFY + ROUTE

Outer-owner boundary: before normal task writes, follow `references/task-completion.md` for prospective task-branch ownership (own linked worktree) and `references/outer-loop.md` for owner-input commits. Existing branches cannot be retroactively adopted. Verify-only does not allocate or publish; phase workers never own delivery.

1. Run the bootstrap once with the exact tokenized `<pipeline_config>` and this orchestrator's default engine from `<engine_routing>`:

   ```bash
   DEVLYN_DEFAULT_ENGINE="<current-cli-default>" python3 "$DEVLYN_SHARED_DIR/resolve-bootstrap.py" <pipeline_config tokens>
   ```

   Read its sole JSON result. On `ok:false`, halt on its exact report-level `blocked` string and show `detail`; init failures create no phase verdict; crashes can leave owned residue, which bootstrap preserves and refuses to replace. Admission refusals require continuing the existing run through its owning session or starting in a distinct worktree. Never autoarchive to defeat a refusal; explicit manual archive is recovery only after the operator establishes that prior writers stopped. Valid completed runs still autoarchive normally, but a completed final report does not prove every interactive writer exited. On success, the script has atomically initialized the schema-v3 skeleton (`pair_verify: true` only when `--pair-verify` was passed), stamped the null-safe Claude session id, persisted exact-byte Goal/spec identity, staged spec verification inputs, and captured the verify-only external diff. It validates only flags needed for those init fields, including mode exclusivity, `--max-rounds`, `--bypass`, and `--pair-verify`/`--no-pair`; `--pair-verify` and `--no-pair` are mutually exclusive. Free-form init sets `state.source.type = "generated"`. Spec staging validates supported `complexity` frontmatter (including sibling spec `complexity` frontmatter). It stages and validates an explicit `--role-config` object into state with its path/digest, but does not resolve roles, write the untracked baseline, classify complexity/risk or announce. `state.engine` is the raw `--engine` value with `engine_source: "flag"`, otherwise the passed `DEVLYN_DEFAULT_ENGINE` with `engine_source: "default"`; step 2 resolves and replaces both fields.

2. Engine pre-flight: follow `_shared/engine-preflight.md`. Freeze the shared resolver once before any phase with `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --freeze-roles --default-engine "<current-cli-default>"`. It validates project/per-run roles and records `state.role_resolution`; legacy `state.engine`/`engine_source` remain the executor. Repeated reads return the same snapshot, never changed project settings. Keep availability/auth checks before each selected dispatch; explicit unavailable routes fail closed. These PHASE0 failures are report-level `BLOCKED:<reason>`; phase verdict carriers remain bare enums.

3. Write `.devlyn/untracked.baseline`: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --write-untracked-baseline`.

4. Read the Goal/spec through `state.source`. For free-form mode, run the deterministic classifier in `references/free-form-mode.md`. Zero-scope-signal goals halt with `BLOCKED:large-needs-ideation`. Follow the selected branch to write the trivial/medium/large body of `.devlyn/criteria.generated.md`, then set `state.complexity` and its raw-byte `criteria_sha256`. The Large `## Assumptions`/recommendation/final-report obligations remain unchanged.

   Compute `state.risk_profile` from the user goal plus spec/criteria text. Mark `high_risk: true` for auth/authz, permissions, security, token/session, payment/money/billing/invoice/pricing/tax/ledger, persistence/data mutation/deletion/migration, idempotency/replay/duplicate, API/webhook/raw-body/signature, allocation/scheduling/inventory/rollback/transaction, or explicit error-priority/output-shape contracts. Explicit `--risk-probes` sets both probe booleans true. Otherwise an automatic high-risk route enables probes only when the legacy executor’s OTHER engine (legacy pair priority/complement, independent of VERIFY profiles) is available and `--no-risk-probes` is absent; if unavailable, keep probes disabled and append `auto-risk-probes skipped: <engine>-unavailable`. `--no-pair` sets `pair_default_enabled: false`. Preserve strict boolean/list types and concise string reasons.

5. Announce one line: `resolve starting — run <run_id> — engine <engine> — mode <mode> — complexity <complexity-or-na> — pair <on|solo:auto_pair_other_engine_unavailable|disabled> — risk_probes <on|off>`.

6. Open the initial post-bootstrap span with standalone `state-phase-write.py ... spawn`: `plan` before owner planning (normal run), or `verify` before MECHANICAL (verify-only). The bootstrap never chooses a phase, engine, branch, prompt, or agent.

### Explicit role dispatch

Use the frozen role entry and `role-config.py --state .devlyn/pipeline.state.json --role worker [--resolved-model <exact inherited model>]` before each affected worker dispatch; `verify-judges.py` applies the same validation to both judge seats. Keep model/effort values as individual argv elements. Replace that role's model/effort options, never append duplicates; omitted fields retain its current phase options. PLAN, BUILD_GATE, probes and SURFACE_CLOSE do not inherit worker/VERIFY profiles. A native option warning that ignores/rejects a requested field is BLOCKED even at exit0. Print requested values, source and channel before dispatch; report observed values only from validated evidence.

For a Codex worker with explicit effort, retain the exact wrapper arguments (excluding `bash` and the wrapper path) as `.devlyn/<phase>.argv.<round>.json` before launch. The wrapper's existing invocation receipt binds that array's canonical JSON hash; completion checks the requested effort against it. This adds no mutation receipt relaxation or new launcher.

`verify-judges.py` owns every judge dispatch, profiled or not: it writes `.devlyn/<engine>-judge.r<VERIFY-round>.{prompt,argv.json}`, captures raw output and stderr, keeps the runner-written `.prompt.transport.json` (prompt bytes, actual argv, outcome and timing), and writes round-scoped role evidence with `judge-role-evidence.py` for each successful seat. The merge authenticates that evidence and archives every bound original, including prior rounds. Never create judge carriers or evidence by hand.

## PHASE 1: PLAN

Skip in verify-only mode. PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`. The owner reads `references/phases/plan.md` and the original request/spec, then writes `.devlyn/plan.md` before product edits. Open with `state-phase-write.py ... --phase plan spawn --round 0`, without worker identity or a prompt dispatch. This is owner reasoning, not zero-cost mechanical work.

Keep the file list/authorized surface, risks and verbatim verification requirements. Large work may include the existing execution-phase section only when every boundary has a runnable gate. Completing PLAN binds the exact output digest; all later mutations rehash it. Never widen it after implementation starts.

After return:
1. If `.devlyn/plan.md` lists zero files → halt with verdict `BLOCKED:plan-empty`.
2. If the plan exceeds the authorized scope, the sole correction is owner round 1 with `--triggered-by plan`, before implementation starts. Narrow to the original authorization, complete and bind the new output; a second failed plan halts. No worker dispatch or new permission is implied.
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
  run invalid even if `.devlyn/risk-probes.jsonl` is written.
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

Engine/model/effort: frozen `role_resolution.roles.worker`, including code/doc cleanup within this same invocation before its final checks; obtain validated argv additions using `role-config.py --state .devlyn/pipeline.state.json --role worker --resolved-model <existing-exact-phase-model>`. Prompt body: `references/phases/implement.md`.

For every Codex-routed IMPLEMENT spawn, render the exact
prompt to `.devlyn/<phase>.prompt.<round>`, pass its SHA-256 to `state-phase-write.py
spawn --prompt-sha256`, and invoke only through `codex-monitored.sh` with these
seven variables set to the active state identity:
`DEVLYN_INVOCATION_{RUN_ID,PHASE,ROUND,WORKDIR,PROMPT_FILE,SESSION_FILE,RECEIPT}`.
Set `DEVLYN_CODEX_PROMPT_FILE` to that same prompt file and pass sole prompt `-`; retain its generated `.transport.json` carrier.
The session and receipt paths are `.devlyn/<phase>.worker-session.<round>.jsonl`
and `.devlyn/<phase>.invocation.<round>.json`. These three paths are round-scoped
so a retry cannot overwrite earlier prompt/session evidence. Every invocation
must include `--json -m <model_requested>` and `-c sandbox_workspace_write.network_access=<true|false>`: exactly
`false` for IMPLEMENT, so
user configuration cannot silently change the phase capability. Redirect wrapper stdout directly
to that session path. The wrapper rejects bypass/yolo flags and any sandbox other
than `workspace-write`. The receipt seals the requested model, sandbox, phase-scoped
network capability, prompt, terminal exit, and session digest; completion passes the
same canonical session via `--engine-session-log`. A missing/mismatched receipt
or same-round retry blocks. Respawn with a new round instead of replacing it.
Historical metadata-bearing PLAN/CLEANUP and absent-kind BUILD spans retain their original receipt-bound worker routes (network false for PLAN/CLEANUP, true for BUILD). New owner spans never create worker receipts.

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
4. Gate FAIL → no commit. Persist `exec.statuses[k-1] = "FAIL"`, retain `exec.current`, and request IMPLEMENT admission with a fresh invocation round and null trigger. The writer charges the shared repair budget on admission. On budget refusal, close the still-open IMPLEMENT span with `--verdict FAIL`, then report `BLOCKED:repair-budget-exhausted` with the gate output, origin and counters.

After the final phase's gate PASS: `git diff <base_ref.sha>...HEAD --stat` — empty → halt with `BLOCKED:implement-empty`; otherwise set `state.implement_passed_sha = git rev-parse HEAD` (phase commits already checkpoint the work — no extra commit).

## PHASE 2.5: SURFACE_CLOSE

Run once iff `state.source.type == "generated"` and complexity is trivial/medium. Engine is Claude always, pair-judge-routed; executor flag/pin ignored. Per `_shared/engine-preflight.md`, unavailability skips via `surface-skip`, reports `auto_surface_close_claude_unavailable`, never BLOCKs/reroutes.

Freeze `.devlyn/surface-close.input.patch`; assemble Claude adapter + `references/phases/surface-close.md` canonical body VERBATIM + data-only Goal/patch/hashes/surface/commands; write the exact bytes to `.devlyn/surface-close.prompt.<round>`, hash them and spawn with `--tools "Read,Grep,Glob,Edit,Write" --dangerously-skip-permissions --output-format json --strict-mcp-config --mcp-config '{"mcpServers":{}}'`, omitting `--model` at SPW spawn to inherit native Claude model settings. Record the effective model from the native JSON result. Use no positional prompt on the CLI route and retain its generated transport carrier. Bound at 600s (native or `run-bounded.py 600 --stdin-file .devlyn/surface-close.prompt.<round> --record-transport -- claude -p`), else block pre-spawn. Save raw stdout as `.devlyn/surface-close.output.json`, extract its `result` string to `.devlyn/surface-close.stdout`, retain `.devlyn/surface-close.worker-session.<round>.jsonl`, and complete with `.devlyn/surface-close.output.json` as `--engine-session-log`; non-JSON/missing result follows the existing failure path. Workers execute nothing; `surface-check` gates rows, citations, scope, and execution. Empty PASS completes; authorized delta is scoped-staged and committed. Only `BLOCKED:surface-close-adjudication-malformed` runs `surface-adjudication-recover --authorized-surface-json <array>`, whose successful rollback and transcript Edit/Write audit complete the nonterminal skip carrier and continue to BUILD_GATE. Timeout, input/prompt mismatch, attestation failure, execution-audit violation, and out-of-surface delta run `surface-rollback`, complete bare `BLOCKED`, and halt; rollback failure also halts. One shot; no `max_rounds`.

**Common post-fix checkpoint (BUILD_GATE and VERIFY):** CLEANUP findings use the same checkpoint with origin `cleanup`. After the budget-admitted fix IMPLEMENT returns, scoped-stage the authorized surface and commit `chore(pipeline): implement fix round <n>`, where `<n>` is the IMPLEMENT invocation round; run `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase implement durability-enforce --round <n> --origin-phase <build_gate|cleanup|verify>`. Its receipt must PASS before re-entry, which enforces it again before VERIFY artifact clearing or phase spawn.

## PHASE 3: BUILD_GATE

Skip in verify-only mode OR when `build-gate` in `state.bypasses`. Deterministic — same commands CI / Docker / production run.

The orchestrator reads `references/phases/build-gate.md` and runs the gates directly: no adapter header, rendered worker prompt or separate model. Open its span through the predecessor transition with no BUILD engine/model/prompt/session arguments. New spans record `execution_kind: "orchestrator_commands"`; historical already-open spans with that field absent retain their worker attestation contract.

Follow the BUILD body's capability contract on the parent's actual command route and log that basis; no child receipt attests it. Authoritative denial yields report-level `BLOCKED:build-env-underprovisioned` (bare `BLOCKED` in state). Keep spec/probe capture and its conditional post-spec denial carrier refresh; ordinary gates retain findings and raw logs. The orchestrator:
1. Detects language/framework via project files (`package.json`, `pyproject.toml`, etc.).
2. Runs language-specific gates (tsc / lint / test), deferring exact literal overlaps under `references/phases/build-gate.md`'s current-contract/current-round rule; task-context prompts must preserve that rule.
3. Always runs `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` (verification_commands literal-match plus `.devlyn/risk-probes.jsonl` when present). If `state.risk_profile.risk_probes_enabled == true`, the script requires `.devlyn/risk-probes.jsonl`; a missing file is a CRITICAL mechanical blocker, not a silent solo run. The script routes each command through `process-evidence.py`; preserve `.devlyn/spec-verify.results.json` and its validated BUILD_GATE carrier for the state-bound archive flow.
4. If diff touches web-surface files: run the browser tier with the repo's available toolchain (for example Playwright or curl).
5. Emits `.devlyn/build_gate.findings.jsonl` + `.devlyn/build_gate.log.md`.

State write: `phases.build_gate.{execution_kind, started_at, verdict, completed_at, duration_ms, artifacts}`; engine/model fields are null, with no worker prompt or receipt. Completion keeps PLAN integrity and process-evidence floors.

Branch:
- `PASS` → PHASE 4.
- `FAIL` → before product repair, halt with report-level `BLOCKED:required-tools-unavailable` only if a parent probe confirms the failed invocation's external gate tool is absent, unchanged `state.base_ref.sha` configuration requires it, and cited explicit task/spec constraints prohibit supplying it through any authorized route. Derive the tool from that configuration and invocation, never diagnostic text; bind the probe's interpreter, work root and normalized child environment to the runner call sites and actual gate invocation, not parent PATH or a manifest command string alone. An available authorized tool route, product-module/configuration failure, changed tool configuration, permitted or unspecified supply, or uncertain probe/identity/environment retains the fix loop. A confirmed prohibited-tool blocker wins even with other product findings: leave them unrepaired and preserve phase `FAIL`, findings, raw streams and sealed manifests unchanged. Record the probe and constraint citation separately in parent halt evidence; no repair means no round increment. Otherwise request BUILD_GATE-origin IMPLEMENT admission with `--next-triggered-by build_gate` and the findings, then run the common post-fix checkpoint. On `BLOCKED:repair-budget-exhausted`, close an open BUILD_GATE with the original FAIL completion arguments, then report that terminal verdict with origin and counters.
- `BLOCKED:build-env-underprovisioned` → halt immediately with the denied operation, original command, and process-evidence manifest/id; do not enter the product fix loop.

## PHASE 4: CLEANUP

Skip if `cleanup` in `state.bypasses`. The owner reads `references/phases/cleanup.md`; no separate model invocation. Code/doc cleanup already belongs to the selected IMPLEMENT worker, with its original engine/model/effort and receipt.

Open through the predecessor transition with `--next-pre-sha "$(git rev-parse HEAD)"`, omitting worker identity. Remove only observed generated, untracked/ignored artifacts owned by this run and not required deliverables; preserve source, user data, evidence and restart records. For PASS, tracked source and HEAD must equal `pre_sha`; the state writer checks them against `--post-sha` and rejects new untracked files relative to `.devlyn/untracked.baseline` (`.devlyn/` exempt). FAIL/BLOCKED closure preserves the observed delta and cannot enter VERIFY.

If a new code/doc cleanup issue appears after BUILD, emit a concrete finding and request budget-admitted IMPLEMENT repair from CLEANUP FAIL with `--next-triggered-by cleanup`. On `BLOCKED:repair-budget-exhausted`, close an open CLEANUP with the original FAIL completion arguments and report `BLOCKED:repair-budget-exhausted` with origin and counters. After admission and repair, checkpoint and rerun BUILD_GATE before CLEANUP and fresh VERIFY; never reuse the earlier green checks. Keep the existing authorized surface, allowlist and durability checks. Do not broaden scope for cleanup.

On success transition CLEANUP→VERIFY with `--post-sha "$(git rev-parse HEAD)"` and the next judge identity. VERIFY MECHANICAL runs independently on the final source.

## PHASE 5: VERIFY (fresh subagent, findings-only)

Independent quality layer. MECHANICAL runs first on the post-CLEANUP code. Two
JUDGES are then **spawned with empty conversation context** — no carry-over from
PHASE 1-4 — and receive one script-derived snapshot: `spec.md` (or
`.devlyn/criteria.generated.md` with the raw goal), sibling `spec.expected.json`,
the authorized surface, the cumulative diff, and `.devlyn/spec-verify.results.json`
with the validated VERIFY process-evidence manifest/raw streams it names. The
fresh-context spawn plus immutable evidence inputs are the structural guarantee
of independence.

Before MECHANICAL, open VERIFY with frozen `role_resolution.roles.primary_judge`; without a profile it follows the legacy executor. Use that engine/model and the current round/trigger metadata in the predecessor's `<transition_protocol>` handoff, including bypass and repair paths; initial verify-only uses PHASE 0's standalone spawn. This records the phase span, not a judge invocation, and requires no rendered judge prompt or prompt digest.

Two sub-phases:

1. **MECHANICAL** (deterministic, orchestrator-owned): re-run `SPEC_VERIFY_PHASE=verify_mechanical SPEC_VERIFY_FINDINGS_FILE=verify-mechanical.findings.jsonl SPEC_VERIFY_FINDING_PREFIX=VERIFY-MECH python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` against the post-CLEANUP code (independent of BUILD_GATE's earlier run). If `state.risk_profile.risk_probes_enabled == true`, missing `.devlyn/risk-probes.jsonl` is a CRITICAL mechanical blocker. This emits `.devlyn/verify-mechanical.findings.jsonl` plus `.devlyn/spec-verify.results.json` with the VERIFY process-evidence carrier. Always continue to step 2: on a verdict-binding MECHANICAL result `verify-judges.py` dispatches neither judge, records `mechanical_blocker`, and still writes the VERIFY verdict.

2. **JUDGES**: run exactly one foreground command — never a background shell — with an explicit Bash timeout of at least 720000 ms:

   `python3 "$DEVLYN_SHARED_DIR/verify-judges.py" --devlyn-dir "$PWD/.devlyn"`

   It claims the round by exclusively creating `.devlyn/verify-judge.r<round>.dispatch.json`, then routes each seat from the frozen roles at dispatch time: an explicit route (`--pair-verify`, role or priority pins) whose engine is unavailable is `BLOCKED:<engine>-unavailable`; an unconfigured automatic pair without its engine records `auto_pair_other_engine_unavailable` and runs solo; `--no-pair` records `user_no_pair`; grok and omp seats are `BLOCKED:judge-route-unsupported:<engine>`. It renders both prompts from the same hash-checked snapshot with `phase-prompt-render.py`, starts both judges before waiting on either (each bounded at 600 s), writes role evidence for each successful seat, and ends with the single `verify-merge-findings.py --write-state` call. Its stdout is the merge summary; a refused claim prints `{"verdict": "BLOCKED", "error": ...}` and exits 1. Never write judge prompts, findings or merge artifacts by hand.

The merge regenerates `.devlyn/verify.findings.jsonl` and `.devlyn/verify.pair.findings.jsonl` from authenticated judge output and publishes the pre-launch `pair_trigger` (its reasons are telemetry). Both judgments merge with the rule "any HIGH/CRITICAL finding is verdict-binding; any MEDIUM with literal `verdict_binding: true` is also binding, regardless of confidence." Each seat's verdict is the worse of its findings and its own terminal verdict. The runner-written transport outcome decides timeouts: a primary timeout is `BLOCKED`, a pair timeout with no findings is `TIMEOUT` (headline: solo verdict after pair TIMEOUT), and any other unsuccessful seat is `BLOCKED`. One seat's failure never discards the other's findings, and the merged verdict is the worst source verdict without vote counting. `primary_judge_blocker` is parser-recognized only for archived v2.0 replay; new runs never write it. State write: `phases.verify.{started_at, verdict, completed_at, duration_ms, judge_durations_ms: {judge, pair_judge}, sub_verdicts: {mechanical, judge, pair_judge?}, pair_trigger, dispatch, role_evidence, executions, merged, artifacts}`.

Branch:
- `PASS` → PHASE 6.
- `PASS_WITH_ISSUES` (no verdict-binding findings) → PHASE 6 with banner.
- `NEEDS_WORK` → in normal mode, request IMPLEMENT admission with `triggered_by: "verify"` and the merged findings. On admission, run the common post-fix checkpoint with origin `verify`; on budget refusal, close VERIFY and report terminal `NEEDS_WORK`.
- `BLOCKED` → close VERIFY and proceed directly to PHASE 6 with its blocker evidence; do not spawn IMPLEMENT or consume repair budget.

## PHASE 6: FINAL REPORT + ARCHIVE

Open the `final_report` span through the predecessor's `state-phase-write.py --devlyn-dir .devlyn --phase <predecessor> transition --next-phase final_report --next-round 0 …` on a direct handoff. Only `BLOCKED:repair-budget-exhausted` invokes exhaustion closure: after a refused transition, first complete its still-open predecessor with the original completion arguments (`--verdict FAIL` for pre-VERIFY origins; omit `--verdict` for VERIFY), then spawn FINAL_REPORT round zero. If standalone repair spawn was refused after completion, do not complete twice. After other halts, use standalone FINAL_REPORT spawn only if unopened.

1. Kill any dev server PHASE 3 left running.

2. **FINISH GATE** — run `python3 "$DEVLYN_SHARED_DIR/finish-gate.py"`; branch only on exit code: 0 → clean; 1 or 2 → `BLOCKED:finish-gate-unclean`, and report the `.devlyn/finish-gate.findings.jsonl` listing, including reverted paths. Offenders exit 2 even when every revert succeeded — a silent revert must never ride an exit-0 pass.

3. **Terminal verdict** — derive from `state.phases.{plan, implement, surface_close, build_gate, cleanup, verify}.verdict` per the precedence rules in `references/state-schema.md#terminal-verdict`. Verify-only mode short-circuits to `state.phases.verify.verdict`.

4. **Render report to `.devlyn/final-report.md` before completion** — first line exactly `<!-- devlyn:final-report run_id=<current state.run_id> -->`, once only, followed by a nonempty report body. Sections: header (run_id, engine, mode, verdict, wall-time), per-phase summary (including SURFACE_CLOSE run or skip, owner PLAN reasoning, and BUILD_GATE/CLEANUP as orchestrator commands with no separate model; code cleanup is included in IMPLEMENT cost), pair/risk-probe status, findings table (verify + finish-gate findings), follow-up notes (the explicit line `pipeline continued to BUILD_GATE — surface_close_rolled_back_adjudication_malformed` when `continued_after_block` is set, any large-mode `## Assumptions` block, any pair-judge TIMEOUT (headline: solo verdict after pair TIMEOUT), any `--no-pair` / `--no-risk-probes` opt-out, and any engine setup guidance after BLOCKED). User-facing text may follow archive; it cannot substitute for this file.

5. Complete the span with `state-phase-write.py --devlyn-dir .devlyn --phase final_report complete --verdict <terminal verdict> --log-file .devlyn/final-report.md` BEFORE archive runs (archive prune skips runs whose `final_report.verdict` is null). The writer validates the canonical nonsymlink regular file, current run marker and nonempty body, then binds its exact bytes; validation failure leaves the phase open. Never hand-edit lifecycle fields in `pipeline.state.json` (`references/state-schema.md` § Write protocol).

6. **Archive** — invoke the deterministic script: `python3 "$DEVLYN_SHARED_DIR/archive_run.py"`. The script reads `run_id` from `.devlyn/pipeline.state.json`, moves the static per-run artifact set (`PER_RUN_PATTERNS` remains the single ownership list) plus every state-bound process-evidence manifest/raw stream into `.devlyn/runs/<run_id>/`, preserves evidence-relative layout, and rehashes bound bytes before any move. An unsafe/missing/altered evidence path or destination collision reports archive failure without changing the already-derived product verdict. It then best-effort prunes to the last 10 completed runs. Archive must run; running this step as deterministic-script-not-prose ensures the move actually happens (iter-0033a Smoke 3 caught a case where the agent claimed archive ran without moving the files).

After successful normal-run archive, return to the outer owner for `references/task-completion.md`. A queue owner first commits its terminal queue transition, then completes once. Honor local-only/no-push; report delivery pending/failure separately from the archived product verdict. This is outside the phase graph.

## State management

`.devlyn/pipeline.state.json` is the single authoritative verdict source. Branch on `state.phases.<name>.verdict` directly; never parse `.devlyn/*.findings.jsonl` for routing decisions. Schema and write protocol: `references/state-schema.md`. Every "State write: `phases.X.{...}`" note above describes the resulting shape only — the orchestrator writes it via initial `spawn`, atomic `transition` for direct handoffs, or terminal `complete`; re-entry preserves the prior lifecycle in `history[]` (`references/state-schema.md#write-protocol`). Phase workers never edit `pipeline.state.json` directly.
