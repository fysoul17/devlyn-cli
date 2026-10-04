# VERIFY MECHANICAL (canonical body)

The orchestrator reads this body directly at the start of each VERIFY round, without an adapter header or worker prompt. MECHANICAL runs the same commands CI / Docker / production run, once, against the final source, and seals that source; gate selection and diagnosis remain orchestrator work.

<role>
Remove run-owned artifacts, run the spec literal check, the binding language gates and the browser tier, remove run-owned artifacts again, then seal the source. Emit findings; the repair loop consumes them. Git staging and commits belong to the IMPLEMENT checkpoint; verify any staging prerequisite with read-only Git inspection, never repeat `git add` or forward task staging instructions as worker actions. Never edit tracked source.
</role>

<capability_contract>
Before executing gates, inspect the orchestrator command route's effective filesystem, subprocess, loopback, PTY and network capabilities and record the actual basis in `.devlyn/mechanical.log.md`. Use an already authorized CI-equivalent route; do not infer capabilities from an engine name or unrelated command success, narrow the route, or widen permissions. No child receipt attests these parent capabilities.

If the parent route or an authoritative tool response explicitly denies a
required operation before the command can produce product output:

1. Preserve the exact original command, denied operation, and raw denial through
   the shared `process-evidence.py` manifest for this VERIFY run/round. Use
   its `capability_denied` classification; a matching stderr phrase is never
   sufficient classification. Record it with
   `python3 "$DEVLYN_SHARED_DIR/process-evidence.py" --devlyn-dir .devlyn record-capability-denial --phase verify --id <gate-id> --cmd '<exact command>' --operation <operation> --detail '<raw denial>'`
   (omit `--cmd` for a declared obligation); it also refreshes `.devlyn/spec-verify.results.json`.
2. Stop with `BLOCKED:build-env-underprovisioned`, citing
   `operation=<filesystem|subprocess|loopback|pty|network|tool>`, the command, and the
   manifest path plus evidence id.
3. Do not emit a product finding, run a substitute command, narrow the command,
   retry it on another route, or treat the denial as test/lint output.

A required tool is a denial with operation `tool` only if a parent probe confirms the failed invocation's external gate tool is absent, unchanged `state.base_ref.sha` configuration requires it, and cited explicit task/spec constraints prohibit supplying it through any authorized route. Derive the tool from that configuration and invocation, never diagnostic text; bind the probe's interpreter, work root and normalized child environment to the runner call sites and actual gate invocation, not parent PATH or a manifest command string alone. Put the probe and the constraint citation in the denial detail. An available authorized tool route, product-module/configuration failure, changed tool configuration, permitted or unspecified supply, or uncertain probe/identity/environment is an ordinary gate failure with findings. A confirmed prohibited-tool denial wins even with other product findings: leave them unrepaired and preserve findings, raw streams and sealed manifests unchanged.

The merge derives the VERIFY verdict floor from this sealed manifest. A
capability denial makes VERIFY `BLOCKED` with no judge and no repair; a failed
product expectation cannot merge as `PASS` or `PASS_WITH_ISSUES` even if a
mutable results or findings file claims otherwise.

An executed command that exits nonzero remains a genuine product result even if
its stdout/stderr contains text such as `permission denied` or `operation not
permitted`. Preserve the existing finding rules below. Only explicit route/tool
capability evidence produces the blocker.
</capability_contract>

<detection>
Detect the project shape from files in `state.base_ref.sha`:

- `package.json` → Node. Use the declared package manager; default `npm`. If `tsconfig.json` exists → run `tsc --noEmit`.
- `pyproject.toml` / `requirements.txt` → Python. If `pyproject.toml` declares a tool config (`ruff`, `mypy`, `pytest`), run the declared tool.
- `go.mod` → Go. Run `go build ./... && go vet ./... && go test ./...`.
- `Cargo.toml` → Rust. Run `cargo build && cargo clippy && cargo test`.
- Mixed / monorepo: detect per-workspace; run only against changed workspaces (use `git diff --name-only <state.base_ref.sha>`).

Gates the spec, base-ref configuration or scripts, or CI require are binding. Only a gate that detection inferred on its own, and that genuinely does not apply, may SKIP. Record this round's skips in `.devlyn/mechanical.log.md` as one marked block, which the final report lists:

````text
<!-- devlyn:mechanical-skips -->
```json
{"run_id": "<state.run_id>", "round": <VERIFY round>, "skips": [{"gate": "lint", "reason": "<why it does not apply>"}]}
```
````
</detection>

<steps>
Every finding goes to `.devlyn/verify-mechanical.findings.jsonl` (appended; step 1 opens the round's file). Append all findings; do not stop on the first failure.

1. **Spec literal verification + risk probes**: first remove run-owned artifacts as in step 4 (IMPLEMENT's own checks leave them), then run `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes`. It first records the round's source snapshot in `.devlyn/source-seal.json`. It routes every literal command and risk probe through `process-evidence.py`, preserving exact command, outcome, raw stdout/stderr, and digests in the VERIFY run/round manifest. It self-stages from sibling `spec.expected.json` next to `state.source.spec_path`, or the legacy inline carrier when the sibling is absent; benchmark-prestaged `.devlyn/spec-verify.json` still wins. It appends `.devlyn/risk-probes.jsonl` when present, and requires that file when `state.risk_profile.risk_probes_enabled == true`. Malformed `state.risk_profile` is also CRITICAL because it can hide enabled risk probes. When probes are enabled or `.devlyn/risk-probes.jsonl` exists, missing or mismatched top-level `state.risk_probes_digest` emits `correctness.risk-probe-integrity` CRITICAL; the digest binds `.devlyn/risk-probes.jsonl` plus referenced `.devlyn/probes/` script bytes. Command or risk-probe mismatch → CRITICAL finding. Missing required risk probes or a malformed sibling expected file → `correctness.spec-verify-malformed` CRITICAL; a missing or malformed generated carrier never reaches VERIFY, because the PHASE 0 freeze refuses it (`BLOCKED:invalid-classification`). In normal mode the same invocation enforces PLAN's declared `authorized_surface` (the json block under `.devlyn/plan.md`'s `<!-- devlyn:authorized-surface -->` section, located by that sentinel regardless of the heading's language) against this run's diff and untracked delta: any changed path or untracked path outside the PHASE 0 baseline and outside the declared surface → `scope.out-of-scope-file` CRITICAL (`.devlyn/` exempt), and so is a baseline (user) file that only a glob would cover, since only an exact surface entry adopts it. The sanctioned fix takes the path out of the change: restore it to base, or drop its index entry and keep the bytes. The repair deletes only a file it created. It never widens the declared surface, since that would let the same worker that leaked scope self-authorize the leak; missing sentinel, malformed `plan.md`/surface block, or missing `.devlyn/untracked.baseline` → `scope.authorized-surface-malformed` CRITICAL. Verify-only reviews a supplied diff and has no PLAN scope check.
2. **Language gates**: resolve the concrete commands; detection examples are not command identities. Run them in order unless step 1's current valid literal contract, using its source precedence and checker defaults, already ran the exact command with the same source/test inputs, working directory and effective environment. Establish the work root and normalized child environment from the checker/runner call sites and the current invocation; a manifest's command string alone does not establish them. The literal must expect exit 0, cover every gate assertion and use the same effective timeout as the planned gate invocation; uncertain matches run normally. A matching gate takes its usual per-error findings and severity from step 1's validated current VERIFY run/round raw streams, citing the evidence id; a completed nonzero exit still supplies the gate's usual failure findings.
   1. **Type check** (TypeScript / mypy / etc.). Each error → one finding, severity `HIGH`, rule `correctness.type-check`.
   2. **Lint**. Run a recognized configured language linter (for example, ESLint with a config, `ruff`, or `clippy`) and/or the exact `package.json` `scripts.lint` command. A declared specialized `lint:*` script (for example, `lint:json`) is not the general language lint gate on the strength of its declaration alone. If the spec's verification commands explicitly name such a specialized command, step 1 executes it and preserves its real failure severity. If no linter is applicable, record an explicit SKIP in the marked skip block and emit zero lint findings. Each error → finding, severity `MEDIUM`, rule `quality.lint`. Warnings stay LOW unless the spec elevates them.
   3. **Test suite** (npm test / pytest / go test / cargo test). Each failing test → finding, severity `HIGH`, rule `correctness.test-failure`. Include the failing test's file:line and the assertion.
3. **Browser** (only when diff touches `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `page.*`, `layout.*`, `route.*`, `*.css`, `*.html`): start the dev server and run the repo's existing browser checks, or a minimal curl/HTML check when no browser test harness exists. Each failed check → finding, severity `HIGH`, rule `correctness.browser-flow-failed`. Stop the dev server before step 4.
4. **Run-owned artifacts**: remove only untracked or ignored generated artifacts this run created that are not deliverables — `test-results/`, `playwright-report/`, `.last-run.json`, coverage output, build artifacts, runtime caches (`__pycache__/`, `*.pyc`, `.cache/`). Preserve deliverables, evidence, `.devlyn/` and every path in `.devlyn/untracked.baseline`'s `untracked` list. Never touch tracked files.
5. **Seal**: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --seal`. Git is observed with index flags, its status caches and hooks neutralized, so nothing they would hide escapes. It seals the source only if it is unchanged since step 1's snapshot and was admissible then. In normal mode that means no tracked or staged change, no untracked file outside the PHASE 0 baseline, and HEAD at the VERIFY span's `pre_sha`. In every mode it means a usable baseline that still matches its bound digest. Trusted environment the seal does not attest (owner decisions 2026-10-04): ignore rules from every source, including rules added during the run, and the content they hide (a rule change that alters which files are visible still changes the observed source); Git's conversion filters, stat cache and other repository configuration; the content of untracked files the PHASE 0 baseline lists (checked by path and kind only); index flags and ignore rules inside submodules; a change undone within a single command. A split index's read refreshes its shared index's mtime, and expanding a sparse index may write tree objects; the real index is never written. A refusal appends one `scope.unsealed-source` finding naming the paths; it routes to repair like any binding finding. Judges review only a sealed round, and the seal is rechecked at dispatch, merge and delivery.
</steps>

<output>
- `.devlyn/verify-mechanical.findings.jsonl` — JSONL stream, one finding per line. Schema: `{id, rule_id, severity, file, line, message, fix_hint, criterion_ref}`.
- `.devlyn/spec-verify.results.json` and `.devlyn/source-seal.json` — written by the checker; never edit them by hand.
- `.devlyn/mechanical.log.md` — human-readable gate results with raw output or links to complete raw-output files, using sealed artifacts where available. Retain complete inventories/hash maps in `.devlyn/` files; report their paths, digests and relevant deltas instead of dumping them into the conversation.
- Then run the JUDGES step; `verify-judges.py` skips both judges on a verdict-binding MECHANICAL result and still writes the VERIFY verdict. Do not edit `pipeline.state.json` yourself.
</output>

<quality_bar>
- Same commands every time. Configuration drift between this gate and CI is a defect; raise as a finding rather than soften this gate. A package-script declaration alone is not evidence that CI executes it.
- Forbidden-pattern check (regex against `git diff`) for `spec.expected.json.forbidden_patterns` runs as part of step 1. Disqualifier-severity matches → CRITICAL findings.
- Reporter artifacts the gates generate (Playwright traces, coverage HTML) belong in gitignored paths. Step 4 removes run-owned leftovers; a tracked artifact in the diff is a `scope.tooling-artifact-leak` MEDIUM finding for the repair loop.
</quality_bar>

<runtime_principles>
The gate is mechanical — its discipline is "do not skip a check, do not paraphrase a verification command, do not narrow severity to mute noise." Findings drive the repair loop; muting findings without a justified spec exception is a workaround.
</runtime_principles>
