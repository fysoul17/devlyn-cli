---
name: devlyn-resolve
description: Default to direct work after inspecting scope and verification, including bounded multi-file changes. Use full resolve for explicit resolve/spec-mode requests, queue drains, or concrete interacting requirements or verification too complex for the current context. Domain labels, file count, spec documents and quoted skill paths alone do not trigger it. Investigate or clarify missing intent/access first. Explicit small resolve retains all phases and independent verification. Verify dual-judge is default-when-available.
---

The current CLI owns PHASE 0, state transitions, Git checkpoints and final report/archive. Spawn the canonical phase workers from this process; never delegate the whole run to another parent orchestrator. VERIFY uses a fresh, findings-only worker.

<pipeline_config>
$ARGUMENTS
</pipeline_config>

<orchestrator_context>
Long-horizon agentic work; context auto-compacts. State lives in `.devlyn/pipeline.state.json` — the single authoritative verdict source. Best at `xhigh` effort.
</orchestrator_context>

<autonomy_contract>
Hands-free. Measured by how far we get without human intervention.

1. Do not prompt the user mid-pipeline. When tempted to ask, pick the safe default, proceed, and log it in the final report.
2. Engine availability: follow `_shared/engine-preflight.md` for the explicit-route-vs-automatic-escalation distinction and BLOCKED-vs-skip behavior. Explicit routes (`--engine`, `--risk-probes`, `--pair-verify`) never downgrade to solo; unavailable auto-escalations proceed solo and report the skip.
3. Order: PLAN → RISK_PROBES? → IMPLEMENT → VERIFY → FINAL_REPORT. No others.
4. Orchestrator does not write code. It parses input, spawns phases, reads state, branches on verdicts, emits the report.
5. Halt only on unrecoverable worker failure, empty IMPLEMENT, refused shared repair admission or VERIFY BLOCKED; otherwise continue.
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

- PLAN runs in the owner context; VERIFY MECHANICAL runs orchestrator commands with no separate model. The selected IMPLEMENT worker also owns code/doc upkeep before its final checkpoint. IMPLEMENT and the VERIFY judges still require fresh workers. If the current CLI cannot spawn a required worker, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable` with the failed spawn command; do not continue with ad-hoc same-context execution.
- Claude Code model-invoked phases other than VERIFY: spawn `Agent` (`mode: "bypassPermissions"`); its prompt is the rendered prompt file's bytes, unmodified.
- Codex CLI model-invoked phases: shell out via `bash "$CODEX_MONITORED_PATH"` with the rendered prompt file. Each `codex exec` child is a new session/fresh context. Set `DEVLYN_CODEX_PROMPT_FILE` to that file with sole prompt argument `-`; the wrapper snapshots exact stdin bytes, seals transport evidence and emits a heartbeat. Without file transport stdin remains DEVNULL. No MCP. The wrapper call is foreground-blocking — never a background shell (`run_in_background`, `&`, `nohup`), never end your message while it runs: headless print-mode wind-down kills backgrounded children (0-byte delivery). Make it one foreground call whose host timeout exceeds the phase budget; set `CODEX_MONITORED_TIMEOUT_SEC` to that budget so the wrapper cancels its own process group and exits 124. Do not read heartbeat, status or log files while it runs. If the host returns before the wrapper exits, wait again with the host's maximum wait and make no other call. This saves owner turns; whether a host can still continue early is unverified.
- oh-my-pi model-invoked phases other than VERIFY: spawn the native `task` tool with a fresh `context` holding the rendered prompt file's bytes, unmodified. Capture the task result into `.devlyn/<phase>.stdout` and any tool error into `.devlyn/<phase>.stderr` before updating state. If the `task` tool is unavailable for an omp-routed phase, write the current phase verdict as `"BLOCKED"` and report `BLOCKED:fresh-context-unavailable`; do not fall back to same-context execution or a nested `omp -p` subprocess.
- Default engine: Claude when the orchestrator has Claude Code’s native `Agent`; otherwise its own fresh worker. PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`. VERIFY MECHANICAL runs orchestrator commands; probes retain their existing routes. `_shared/engine-preflight.md#role-resolution` defines the single resolver and explicit `--role-config` / project role precedence. Absent profiles preserve legacy `--engine` / executor / default behavior, except that an inherited primary judge on an engine with no scripted judge route (omp) goes to the first available of claude, codex other than an explicit pair seat; VERIFY primary may be independently selected. Configured role/priority pins and flags fail closed on unavailable engine or failed authentication, including failures discovered at dispatch. Unconfigured automatic VERIFY selects an available OTHER engine.
- The `--engine` flag does not disable default pairing: the second judge uses the OTHER engine by default when available.
- VERIFY judges: `verify-judges.py` launches both seats from any orchestrator (Claude through `claude -p`, Codex through the monitored route); other engines are unsupported judge seats.
- Multi-LLM evolution: when a new model adapter ships in `_shared/adapters/`, that engine becomes selectable for the worker role its adapter declares eligible without further skill changes; a judge seat also needs a `verify-judges.py` route (NORTH-STAR.md "Multi-LLM evolution direction").
</engine_routing>

<modes>
Three input shapes:

1. **Free-form**: `/devlyn-resolve "fix the login bug"` (inline goal) or `/devlyn-resolve --goal-file <path>` (goal text read from a file — the devlynd `ResolveAdapter` launcher path, injection-safe). PHASE 0 runs the complexity classifier and either proceeds with an internal mini-spec (trivial), drafts focused questions for in-prompt resolution (medium), or synthesizes a best-effort spec with a logged `## Assumptions` block (large; zero-scope-signal goals halt). No mid-pipeline prompts in any branch.
2. **Spec**: `/devlyn-resolve --spec docs/roadmap/phase-N/X.md`. Supplied specs and expected files are read-only inside resolve. Stage verification commands from sibling `spec.expected.json`; if absent, use the legacy `## Verification` JSON block.
3. **Verify-only**: `/devlyn-resolve --verify-only <diff-or-PR-ref> --spec <path>`. Skips PHASE 1-2. Runs PHASE 5 (VERIFY) on the supplied diff against the spec.
</modes>

<post_implement_invariant>
After the IMPLEMENT checkpoint, VERIFY changes no source: MECHANICAL only runs checks and removes run-owned artifacts, and the judges are fresh-context and findings-only. No fresh VERIFY worker → `BLOCKED:fresh-context-unavailable`, never same-context review.
</post_implement_invariant>

<transition_protocol>
For every direct complete→spawn handoff, call `state-phase-write.py ... --phase <current> transition` with the current phase's normal completion/attestation arguments plus caller-specified `--next-phase`, `--next-round`, `--next-triggered-by`, `--next-engine`, `--next-model`, and any next-phase metadata. For owner PLAN, omit engine/model/prompt/session arguments; it records `execution_kind: "orchestrator_context"` with null worker identity. Existing metadata-bearing PLAN spans retain historical worker validation; never relabel their evidence. Opening VERIFY records its `pre_sha` (HEAD); the caller never supplies a SHA. The verb validates a legal edge and commits both lifecycle writes atomically; it returns JSON state facts only. It never selects a phase/engine, renders a prompt, or spawns an agent. Every edge into a worker phase (PROBE_DERIVE, IMPLEMENT) instead runs standalone `complete` → render → standalone `spawn`: the renderer reads only completed state and a Codex IMPLEMENT spawn needs the rendered prompt's digest. Use standalone `spawn` also for the initial post-bootstrap dispatch, and standalone `complete` when no next phase opens (including a halt).
</transition_protocol>

## PHASE 0: PARSE + CLASSIFY + ROUTE

Outer-owner boundary: a full run starts only from committed owner inputs; whenever this session commits owner inputs, drains a queue or completes delivery, follow `references/outer-loop.md`. Before normal task writes, read `references/task-completion.md` only if this session has not allocated its own task branch (own linked worktree); existing branches cannot be retroactively adopted. Verify-only does not allocate or publish; phase workers never own delivery.

1. Run the bootstrap once with the exact tokenized `<pipeline_config>` and this orchestrator's default engine from `<engine_routing>`:

   ```bash
   DEVLYN_DEFAULT_ENGINE="<current-cli-default>" python3 "$DEVLYN_SHARED_DIR/resolve-bootstrap.py" <pipeline_config tokens>
   ```

   Read its sole JSON result. On `ok:false`, halt on its exact report-level `blocked` string and show `detail`; init failures create no phase verdict; crashes can leave owned residue, which bootstrap preserves and refuses to replace. Admission refusals require continuing the existing run through its owning session or starting in a distinct worktree. Never autoarchive to defeat a refusal; explicit manual archive is recovery only after the operator establishes that prior writers stopped. Valid completed runs still autoarchive normally, but a completed final report does not prove every interactive writer exited. On success, the script has atomically initialized the schema-v3 skeleton (`pair_verify: true` only when `--pair-verify` was passed; `risk_profile` records `--risk-probes`, `--no-risk-probes` and `--no-pair`), stamped the null-safe Claude session id, persisted exact-byte Goal/spec identity, staged spec verification inputs, and captured the verify-only external diff. `--pair-verify` and `--no-pair` are mutually exclusive, as are `--risk-probes` and `--no-risk-probes`; `--risk-probes` is also refused with `--verify-only` or for a spec without the `<!-- devlyn:verification -->` section probes derive from. Free-form init sets `state.source.type = "generated"`. Spec staging validates supported `complexity` frontmatter (including sibling spec `complexity` frontmatter); an explicit `--role-config` object is staged with its path/digest. `state.engine` is the raw `--engine` value with `engine_source: "flag"`, otherwise the passed `DEVLYN_DEFAULT_ENGINE` with `engine_source: "default"`; step 4 resolves and replaces both fields.

2. Write `.devlyn/untracked.baseline`, which lists the untracked files and a sparse checkout's absent paths: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --write-untracked-baseline`. If it fails, close the run as a PHASE 0 halt with `BLOCKED:untracked-baseline-unwritable`. The first phase spawn binds its digest; MECHANICAL seals only against those bytes.

3. Classify. Read the Goal/spec through `state.source`. For free-form mode, run the deterministic classifier in `references/free-form-mode.md`; zero-scope-signal goals halt with `BLOCKED:large-needs-ideation`; otherwise write the selected branch's `.devlyn/criteria.generated.md` (the Large `## Assumptions`/recommendation obligations remain). From the user goal plus spec/criteria text, name one concise reason per matching high-risk category: auth/authz, permissions, security, token/session, payment/money/billing/invoice/pricing/tax/ledger, persistence/data mutation/deletion/migration, idempotency/replay/duplicate, API/webhook/raw-body/signature, allocation/scheduling/inventory/rollback/transaction, or explicit error-priority/output-shape contracts.

4. Freeze roles and classification once, before any phase:

   ```bash
   python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --freeze-roles --default-engine "<current-cli-default>" [--complexity <trivial|medium|large>] [--high-risk-reason "<reason>"]...
   ```

   `--complexity` is required for free-form and refused otherwise. The writer resolves roles per `_shared/engine-preflight.md` into `state.role_resolution` (legacy `state.engine`/`engine_source` remain the executor), binds `source.criteria_sha256` from the criteria bytes, and records `risk_profile.high_risk`/`reasons`. An automatic high-risk run (no explicit probe flag, not verify-only) enables probes only when the legacy executor's OTHER engine is available; otherwise it appends `auto-risk-probes skipped: <engine>-unavailable`, or `auto-risk-probes skipped: no-verification-section` when the source has no verification section to derive probes from. An identical repeat returns the same snapshot; a differing one is refused. Keep availability/auth checks before each selected dispatch; explicit unavailable routes fail closed. PHASE 0 failures are report-level `BLOCKED:<reason>`; phase verdict carriers remain bare enums. Once bootstrap has initialized state, close such a halt like any other: standalone FINAL_REPORT spawn, the finish gate, `complete --verdict BLOCKED:<reason>` (only a PHASE 0 reason: a role-resolution refusal, `invalid-classification`, `large-needs-ideation` or `untracked-baseline-unwritable`), archive.

5. Announce one line: `resolve starting — run <run_id> — engine <engine> — mode <mode> — complexity <complexity-or-na> — pair <on|solo:auto_pair_other_engine_unavailable|disabled> — risk_probes <on|off>`.

6. Open the initial post-bootstrap span with standalone `state-phase-write.py ... spawn`: `plan` before owner planning (normal run), or `verify` before MECHANICAL (verify-only). The bootstrap never chooses a phase, engine, branch, prompt, or agent.

### Explicit role dispatch

Use the frozen role entry and `role-config.py --state .devlyn/pipeline.state.json --role worker [--resolved-model <exact inherited model>]` before each affected worker dispatch; `verify-judges.py` applies the same validation to both judge seats. Keep model/effort values as individual argv elements. Replace that role's model/effort options, never append duplicates; omitted fields retain its current phase options. PLAN, MECHANICAL and probes do not inherit worker/VERIFY profiles. A native option warning that ignores/rejects a requested field is BLOCKED even at exit0. Print requested values, source and channel before dispatch; report observed values only from validated evidence.

For a Codex worker with explicit effort, retain the exact wrapper arguments (excluding `bash` and the wrapper path) as `.devlyn/<phase>.argv.<round>.json` before launch. The wrapper's existing invocation receipt binds that array's canonical JSON hash; completion checks the requested effort against it. This adds no mutation receipt relaxation or new launcher.

`verify-judges.py` owns every judge dispatch, profiled or not: it writes `.devlyn/<engine>-judge.r<VERIFY-round>.{prompt,argv.json}`, captures raw output and stderr, keeps the runner-written `.prompt.transport.json` (prompt bytes, actual argv, outcome and timing), and writes round-scoped role evidence with `judge-role-evidence.py` for each successful seat. The merge authenticates that evidence and archives every bound original, including prior rounds. Never create judge carriers or evidence by hand.

## PHASE 1: PLAN

Skip in verify-only mode. PLAN is orchestrator-fixed and never inherits `--engine`, an executor pin, or `state.engine`. The owner reads `references/phases/plan.md` and the original request/spec, then writes `.devlyn/plan.md` before product edits. Open with `state-phase-write.py ... --phase plan spawn --round 0`, without worker identity or a prompt dispatch. This is owner reasoning, not zero-cost mechanical work.

Keep the file list/authorized surface and the risks the contract leaves open; never restate the contract. Large work may include the existing execution-phase section only when every boundary has a runnable gate. Completing PLAN binds the exact output digest; all later mutations rehash it. Never widen it after implementation starts.

After return:
1. If `.devlyn/plan.md` lists zero files → halt with verdict `BLOCKED:plan-empty`.
2. If the plan exceeds the authorized scope, the sole correction is owner round 1 with `--triggered-by plan`, before implementation starts. Narrow to the original authorization, complete and bind the new output; a second failed plan halts. No worker dispatch or new permission is implied.

## PHASE 1.5: RISK_PROBES

Runs only when `state.risk_profile.risk_probes_enabled` is true; then read and follow `references/risk-probes.md`. Complete PLAN, render the probe prompt, then spawn PROBE_DERIVE; a renderer refusal closes the run as in PHASE 2. The OTHER engine is required: an explicit `--risk-probes` route whose engine is unavailable halts with `BLOCKED:<engine>-unavailable` plus setup guidance (an automatic route toward an unavailable engine was already left disabled at freeze).

After return, complete PROBE_DERIVE, then render and spawn IMPLEMENT (PHASE 2). A passing completion validates `.devlyn/risk-probes.jsonl` with `spec-verify-check.py --validate-risk-probes` and binds `state.risk_probes_digest` under the state lock; malformed probes refuse the completion with `BLOCKED:probe-derive-malformed` (complete BLOCKED and halt). IMPLEMENT reads `.devlyn/risk-probes.jsonl` by path as acceptance obligations; its rendered prompt carries no producer commentary.

## PHASE 2: IMPLEMENT

Skip in verify-only mode. Constrained design judgment within PLAN's invariants. Writes code, tests, and inline doc-comments. No standalone DOCS phase — what the spec licenses is updated here, what it does not is out of scope.

Engine/model/effort: frozen `role_resolution.roles.worker`, including code/doc upkeep within this same invocation before its final checks; obtain validated argv additions using `role-config.py --state .devlyn/pipeline.state.json --role worker --resolved-model <existing-exact-phase-model>`. Prompt body: `references/phases/implement.md`.

Every IMPLEMENT span opens in this order: complete the predecessor, render the prompt, then `state-phase-write.py --devlyn-dir .devlyn --phase implement spawn --round <round> [--triggered-by verify] --engine <engine> [--model <model>] [--prompt-sha256 <sha>]` (Codex requires the digest, and the model unless the frozen worker role pins one). The renderer builds the prompt from state — the canonical body, the exact contract and goal bytes, path bindings, any phase-gated `exec`, and on a VERIFY repair the merged findings — writes `.devlyn/implement.prompt.<round>` and prints its SHA-256. The owner adds no prompt text and passes the file's bytes unchanged:

```bash
python3 "$DEVLYN_SHARED_DIR/phase-prompt-render.py" --devlyn-dir .devlyn --phase implement --engine <engine> --round <round>
```

A renderer refusal (`BLOCKED:phase-input-invalid:<kind>:<detail>`) leaves the predecessor completed and the worker phase unopened: open FINAL_REPORT with standalone spawn and complete it with `--verdict BLOCKED:phase-input-invalid --detail "<message>"` — or without `--verdict` when the writer derives the verdict itself (an exhausted repair budget gives `NEEDS_WORK` or `BLOCKED:repair-budget-exhausted`; finish-gate offenders give `BLOCKED:finish-gate-unclean`); a refused `--verdict` names the derived one.

For Codex, after the span opens, invoke only through the wrapper with the active state identity. Add the validated `role-config.py` options before the final `-`; only an option list that names a model replaces `-m <model_requested>`:

```bash
DEVLYN_INVOCATION_RUN_ID=<run_id> DEVLYN_INVOCATION_PHASE=implement DEVLYN_INVOCATION_ROUND=<round> DEVLYN_INVOCATION_WORKDIR="$PWD" DEVLYN_INVOCATION_PROMPT_FILE=.devlyn/implement.prompt.<round> DEVLYN_INVOCATION_SESSION_FILE=.devlyn/implement.worker-session.<round>.jsonl DEVLYN_INVOCATION_RECEIPT=.devlyn/implement.invocation.<round>.json DEVLYN_CODEX_PROMPT_FILE=.devlyn/implement.prompt.<round> bash "$CODEX_MONITORED_PATH" -C "$PWD" -s workspace-write --json -m <model_requested> -c sandbox_workspace_write.network_access=false - > .devlyn/implement.worker-session.<round>.jsonl
```

Retain the generated `.transport.json` carrier. The prompt, session and receipt paths are round-scoped so a retry cannot overwrite earlier evidence; network access is exactly `false` so user configuration cannot change the phase capability. The wrapper rejects bypass/yolo flags and any sandbox other
than `workspace-write`. The receipt seals the requested model, sandbox, phase-scoped
network capability, prompt, terminal exit, and session digest; completion passes the
same canonical session via `--engine-session-log`. A missing/mismatched receipt
or same-round retry blocks. Respawn with a new round instead of replacing it.
Historical metadata-bearing PLAN spans retain their original receipt-bound worker route (network false). New owner spans never create worker receipts.

State write: `phases.implement.{started_at, verdict, completed_at, duration_ms}`.

Before accepting an IMPLEMENT `PASS` / `PASS_WITH_ISSUES` completion or
transition, `state-phase-write.py` validates every sibling
`spec.expected.json.process_evidence[]` obligation for `phase: "implement"`,
rehashes its raw streams, and appends the validated carrier to
`state.process_evidence`. A missing, altered, escaping, duplicate, or
expectation-mismatched carrier blocks the checkpoint.

**Single-phase path** (plan.md has no `## Execution phases` section — every trivial/medium run, and any large run PLAN judged atomic): spawn IMPLEMENT once. No phase metadata of any kind appears in the prompt. After return:
1. `git diff --stat` — empty diff → halt with `BLOCKED:implement-empty`.
2. Checkpoint (**scoped staging** — this exact shape everywhere a pipeline commit is made): `bash -o pipefail -c 'python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --print-authorized-surface | git --literal-pathspecs add --pathspec-from-file=- --pathspec-file-nul' && git commit -m "chore(pipeline): implement"`. Every deliverable, including new files, must be in this commit: MECHANICAL seals only a clean tree. An untracked file that predates the run is staged only when plan.md's surface names its exact path.

**Phase-gated path** (plan.md's `## Execution phases` section has two or more `### Phase <k>` headings outside fenced blocks): definitions are the contract in plan.md; progress is routing truth in `state.phases.implement.exec = { total, current, statuses }`, which the writer creates at the first IMPLEMENT spawn and advances on each passing phase. For each phase k = 1..N:
1. Render and spawn IMPLEMENT; the prompt's `metadata.exec` names the current phase, and the worker implements that phase in the current worktree and reruns its `gate:` line.
2. After return: run the phase's `gate:` commands directly — deterministic, exit-code truth, no LLM judgment.
3. Gate PASS → scoped-staging checkpoint with message `chore(pipeline): implement phase <k>/<N>`. For a phase before the last, complete IMPLEMENT `PASS` (the writer marks the phase and advances `exec.current`); the next phase renders and spawns uncharged with the next round. The last phase is handled below.
4. Gate FAIL → no commit. Complete IMPLEMENT `FAIL` (the writer records the phase's FAIL and keeps `exec.current`), then render and request IMPLEMENT admission with a fresh invocation round and null trigger. The writer charges the shared repair budget on admission. A refused spawn leaves the FAIL completion as the last span; report `BLOCKED:repair-budget-exhausted` with the gate output, origin and counters.

After the final phase's gate PASS and checkpoint: `git diff <base_ref.sha>...HEAD --stat` — empty → complete IMPLEMENT and halt with `BLOCKED:implement-empty`; otherwise open VERIFY with the IMPLEMENT → VERIFY `transition`, which completes the last phase `PASS` (phase commits already checkpoint the work — no extra commit).

**Post-fix checkpoint:** after a budget-admitted VERIFY repair IMPLEMENT returns, settle each path that this round's `scope.out-of-scope-file` findings name. Restore one that exists at `base_ref.sha` with `git --literal-pathspecs restore --source=<base_ref.sha> --staged --worktree -- <path>`. For any other path, drop only its index entry with `git --literal-pathspecs rm -q --cached --ignore-unmatch -- <path>` and keep the file. Only the repair deletes a file, and only one it created itself. Then scoped-stage the authorized surface and commit with `git commit --allow-empty -m "chore(pipeline): implement fix round <n>"`, where `<n>` is the IMPLEMENT invocation round (empty when the repair only removed out-of-surface changes); run `python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase implement durability-enforce --round <n>`. It records the clean fix commit and the triggering merged findings; fresh VERIFY re-entry rechecks that receipt before VERIFY artifact clearing or phase spawn, and MECHANICAL runs again on the new source — earlier green checks are never reused.

## PHASE 5: VERIFY (MECHANICAL, then fresh findings-only judges)

Independent quality layer. MECHANICAL runs first and seals the final source. Two
JUDGES are then **spawned with empty conversation context** — no carry-over from
PLAN or IMPLEMENT — and receive one script-derived snapshot: `spec.md` (or
`.devlyn/criteria.generated.md` with the raw goal), sibling `spec.expected.json`,
the authorized surface, the cumulative diff, and `.devlyn/spec-verify.results.json`
with the validated VERIFY process-evidence manifest/raw streams it names. The
fresh-context spawn plus immutable evidence inputs are the structural guarantee
of independence.

Before MECHANICAL, open VERIFY with frozen `role_resolution.roles.primary_judge`; without a profile it follows the legacy executor, or the routed claude/codex seat for an omp executor. Use that engine/model and the current round/trigger metadata in the predecessor's `<transition_protocol>` handoff, including repair paths; initial verify-only uses PHASE 0's standalone spawn. This records the phase span, not a judge invocation, and requires no rendered judge prompt or prompt digest.

Two sub-phases:

1. **MECHANICAL** (deterministic, orchestrator-owned; no adapter header or separate model): read `references/phases/mechanical.md` and run its steps once per VERIFY round, in both normal and verify-only modes:
   1. Remove proven run-owned generated artifacts (as in step 3), then `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` records the source snapshot, then runs the literal commands, risk probes and expected-contract checks through `process-evidence.py` and, in normal mode, the authorized-surface scope check. If `state.risk_profile.risk_probes_enabled == true`, a missing `.devlyn/risk-probes.jsonl` is a CRITICAL blocker. It writes `.devlyn/verify-mechanical.findings.jsonl` and `.devlyn/spec-verify.results.json` with the VERIFY process-evidence carrier.
   2. The binding language gates (type check, lint, tests) and, for web-surface diffs, the browser tier, appending findings. Commands the spec, repo or CI require stay binding; only a genuinely inapplicable inferred check may SKIP, visibly.
   3. Remove proven run-owned generated artifacts; never touch tracked source.
   4. `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --seal` seals the source only if it is unchanged since step 1 and admissible then (`mechanical.md` step 5, including what the seal does not attest). A refusal appends `scope.unsealed-source`, a binding finding.

   An authoritative capability denial, including a required tool proven absent whose supply the task prohibits (operation `tool`; proof rules in `mechanical.md`), makes VERIFY `BLOCKED` with report-level `BLOCKED:build-env-underprovisioned`: no judge runs and no repair is admitted. Always continue to step 2: on a verdict-binding MECHANICAL result `verify-judges.py` dispatches neither judge, records `mechanical_blocker`, and still writes the VERIFY verdict.

2. **JUDGES**: run exactly one foreground command — never a background shell — with an explicit Bash timeout of at least 720000 ms:

   `python3 "$DEVLYN_SHARED_DIR/verify-judges.py" --devlyn-dir "$PWD/.devlyn"`

   It claims the round by exclusively creating `.devlyn/verify-judge.r<round>.dispatch.json`, then routes each seat from the frozen roles at dispatch time: an explicit route (`--pair-verify`, role or priority pins) whose engine is unavailable is `BLOCKED:<engine>-unavailable`; an unconfigured automatic pair without its engine records `auto_pair_other_engine_unavailable` and runs solo; `--no-pair` records `user_no_pair`; grok and omp seats are `BLOCKED:judge-route-unsupported:<engine>`. It renders both prompts from the same hash-checked snapshot with `phase-prompt-render.py`, starts both judges before waiting on either (each bounded at 600 s), writes role evidence for each successful seat, and ends with the single `verify-merge-findings.py --write-state` call. Its stdout is the merge summary; a refused claim prints `{"verdict": "BLOCKED", "error": ...}` and exits 1. Never write judge prompts, findings or merge artifacts by hand.

The merge regenerates `.devlyn/verify.findings.jsonl` and `.devlyn/verify.pair.findings.jsonl` from authenticated judge output and publishes the pre-launch `pair_trigger` (its reasons are telemetry). Both judgments merge with the rule "any HIGH/CRITICAL finding is verdict-binding; any MEDIUM with literal `verdict_binding: true` is also binding, regardless of confidence." Each seat's verdict is the worse of its findings and its own terminal verdict. The runner-written transport outcome decides timeouts: a primary timeout is `BLOCKED`, a pair timeout with no findings is `TIMEOUT` (headline: solo verdict after pair TIMEOUT), and any other unsuccessful seat is `BLOCKED`. One seat's failure never discards the other's findings, and the merged verdict is the worst source verdict without vote counting. `primary_judge_blocker` is parser-recognized only for archived v2.0 replay; new runs never write it. State write: `phases.verify.{started_at, pre_sha, verdict, completed_at, duration_ms, judge_durations_ms: {judge, pair_judge}, sub_verdicts: {mechanical, judge, pair_judge?}, pair_trigger, dispatch, role_evidence, executions, merged, source_seal, artifacts}`.

Branch:
- `PASS` → PHASE 6.
- `PASS_WITH_ISSUES` (no verdict-binding findings) → PHASE 6 with banner.
- `NEEDS_WORK` → in normal mode, complete VERIFY, render (its findings frame carries the merged findings, MECHANICAL ones included) and request IMPLEMENT admission with `--triggered-by verify`. On admission, run the post-fix checkpoint; on budget refusal, report terminal `NEEDS_WORK`.
- `BLOCKED` → close VERIFY and proceed directly to PHASE 6 with its blocker evidence; do not spawn IMPLEMENT or consume repair budget.

## PHASE 6: FINAL REPORT + ARCHIVE

Open the `final_report` span through the predecessor's `state-phase-write.py --devlyn-dir .devlyn --phase <predecessor> transition --next-phase final_report --next-round 0 …` on a direct handoff. Any other halt after bootstrap — a refused repair spawn, a renderer refusal, a PHASE 0 halt — uses standalone FINAL_REPORT spawn (round zero) only if unopened; a completed predecessor is never completed twice.

1. Kill any dev server MECHANICAL left running.

2. **FINISH GATE** — run `python3 "$DEVLYN_SHARED_DIR/finish-gate.py"` once (a rerun returns the run's first result); branch only on exit code: 0 → clean; 2, or 1 after IMPLEMENT started → `BLOCKED:finish-gate-unclean`, and report the `.devlyn/finish-gate.findings.jsonl` listing, including reverted paths. Offenders exit 2 even when every revert succeeded — a silent revert must never ride an exit-0 pass.

3. **Terminal verdict and report** — after the finish gate, complete the span; the writer derives the verdict, renders `.devlyn/final-report.md`, binds its bytes and prints it:

   ```bash
   python3 "$DEVLYN_SHARED_DIR/state-phase-write.py" --devlyn-dir .devlyn --phase final_report complete [--verdict BLOCKED:<reason>] [--detail "<failed command or guidance>"]
   ```

   Complete before archive (archive prune skips runs whose `final_report.verdict` is null). Precedence: a completed PLAN whose bound output no longer verifies → `BLOCKED:phase-input-invalid` (work phases refuse it; FINAL_REPORT records it); finish-gate offenders (exit 2), or a malformed gate (exit 1) after IMPLEMENT started → `BLOCKED:finish-gate-unclean`; a BLOCKED phase → the reason its bound evidence records (MECHANICAL capability denial → `BLOCKED:build-env-underprovisioned`; a blocked judge seat → its dispatch reason); refused repair admission with exhausted counters → VERIFY `NEEDS_WORK` or phase-gate `BLOCKED:repair-budget-exhausted`; verify-only → the VERIFY verdict; otherwise VERIFY `PASS`/`PASS_WITH_ISSUES`. Pass `--verdict BLOCKED:<reason>` whenever the writer cannot derive the reason: a BLOCKED phase without a denial or blocked seat (judge timeout or invalid output, `probe-derive-malformed`, a worker BLOCKED), or a halt that state does not record (`plan-empty`, `implement-empty`, `fresh-context-unavailable`, `phase-input-invalid`, an IMPLEMENT/probe engine unavailable, including before a repair span opens). A reason is a bare label (`judge-route-unsupported:<engine>` is the one qualified family); explanations go to `--detail`. A supplied verdict that contradicts the evidence, an evidence-only reason without its evidence, or anything else in a reason is refused and nothing is written. Never write the report or lifecycle fields by hand.

4. **Archive** — invoke the deterministic script: `python3 "$DEVLYN_SHARED_DIR/archive_run.py"`. The script reads `run_id` from `.devlyn/pipeline.state.json`, moves the static per-run artifact set (`PER_RUN_PATTERNS` remains the single ownership list) plus every state-bound process-evidence manifest/raw stream into `.devlyn/runs/<run_id>/`, preserves evidence-relative layout, and rehashes bound bytes before any move. An unsafe/missing/altered evidence path or destination collision reports archive failure without changing the already-derived product verdict. It then best-effort prunes to the last 10 completed runs. Archive must run; running this step as deterministic-script-not-prose ensures the move actually happens (iter-0033a Smoke 3 caught a case where the agent claimed archive ran without moving the files).

After archive, relay the printed report byte for byte as the final user-facing report; other text may follow it but cannot substitute for it. After successful normal-run archive, return to the outer owner for `references/task-completion.md`. A queue owner first commits its terminal queue transition, then completes once. Honor local-only/no-push; report delivery pending/failure separately from the archived product verdict. This is outside the phase graph.

## State management

`.devlyn/pipeline.state.json` is the single authoritative verdict source. Branch on `state.phases.<name>.verdict` directly; never parse `.devlyn/*.findings.jsonl` for routing decisions. Every "State write: `phases.X.{...}`" note above describes the resulting shape only — the orchestrator writes it via initial `spawn`, atomic `transition` for direct handoffs, complete → render → spawn into a worker phase, or terminal `complete`; re-entry preserves the prior lifecycle in `history[]`. Phase workers never edit `pipeline.state.json` directly.
