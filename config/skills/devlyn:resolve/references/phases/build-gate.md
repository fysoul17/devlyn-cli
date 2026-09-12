# PHASE 3 — BUILD_GATE (canonical body)

Per-engine adapter header is prepended at runtime. BUILD_GATE is mechanical / deterministic — same commands CI / Docker / production run.

<role>
Run language-specific gates and the spec literal-match verification. Emit findings; the orchestrator's fix loop consumes them.
</role>

<capability_contract>
A Codex BUILD_GATE runs on the parent-provided CI-equivalent route. Required
filesystem, subprocess, loopback, PTY, and network capabilities are part of the
gate input, not permissions this worker may widen.

If the parent route or an authoritative tool response explicitly denies a
required operation before the command can produce product output:

1. Preserve the exact original command, denied operation, and raw denial through
   the shared `process-evidence.py` manifest for this BUILD_GATE run/round. Use
   its `capability_denied` classification; a matching stderr phrase is never
   sufficient classification.
2. Stop with `BLOCKED:build-env-underprovisioned`, citing
   `operation=<filesystem|subprocess|loopback|pty|network>`, the command, and the
   manifest path plus evidence id.
3. Do not emit a product finding, run a substitute command, narrow the command,
   retry it on another route, or treat the denial as test/lint output.

The state writer derives the phase verdict floor from this sealed manifest. A
capability denial can complete only as `BLOCKED`; a failed product expectation
cannot complete as `PASS` or `PASS_WITH_ISSUES` even if a mutable results or
findings file claims otherwise.

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
</detection>

<gates>
Resolve the concrete commands for steps 1–3; detection examples are not command identities. Run them in order unless step 4's current valid literal contract, using its source precedence and checker defaults, schedules the exact command with the same source/test inputs, working directory and effective environment. Establish the work root and normalized child environment from the checker/runner call sites and the current invocation; a manifest's command string alone does not establish them. The literal must expect exit 0, cover every gate assertion and use the same effective timeout as the planned gate invocation; uncertain matches run normally. Defer a matching gate to step 4 and derive its usual per-error findings and severity from that invocation's validated current BUILD_GATE run/round raw streams, citing the evidence id. A completed nonzero exit still supplies the gate's usual failure findings. If step 4 leaves no validated exit-kind result for a deferred gate, run that gate normally and append its findings, preserving step 4's failures; capability denials retain the stop contract above. Keep every literal invocation and independent post-CLEANUP VERIFY. Each gate emits findings into `.devlyn/build_gate.findings.jsonl`:

1. **Type check** (TypeScript / mypy / etc.). Each error → one finding, severity `HIGH`, rule `correctness.type-check`.
2. **Lint**. Run a recognized configured language linter (for example, ESLint with a config, `ruff`, or `clippy`) and/or the exact `package.json` `scripts.lint` command. A declared specialized `lint:*` script (for example, `lint:json`) is not the general language lint gate on the strength of its declaration alone. If the spec's verification commands explicitly name such a specialized command, step 4 executes it and preserves its real failure severity. If no linter is applicable, log an explicit SKIP in `.devlyn/build_gate.log.md` and emit zero lint findings. Each error → finding, severity `MEDIUM`, rule `quality.lint`. Warnings stay LOW unless the spec elevates them.
3. **Test suite** (npm test / pytest / go test / cargo test). Each failing test → finding, severity `HIGH`, rule `correctness.test-failure`. Include the failing test's file:line and the assertion.
4. **Spec literal verification + risk probes**: `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes`. The script routes every literal command and risk probe through `process-evidence.py`, preserving exact command, outcome, raw stdout/stderr, and digests in the BUILD_GATE run/round manifest. It self-stages from sibling `spec.expected.json` next to `state.source.spec_path`, or the legacy inline carrier when the sibling is absent; benchmark-prestaged `.devlyn/spec-verify.json` still wins. It appends `.devlyn/risk-probes.jsonl` when present, and requires that file when `state.risk_profile.risk_probes_enabled == true`. Malformed `state.risk_profile` is also CRITICAL because it can hide enabled risk probes. When probes are enabled or `.devlyn/risk-probes.jsonl` exists, missing or mismatched top-level `state.risk_probes_digest` emits `correctness.risk-probe-integrity` CRITICAL; the digest binds `.devlyn/risk-probes.jsonl` plus referenced `.devlyn/probes/` script bytes. Command or risk-probe mismatch → CRITICAL finding. Missing required risk probes, missing/malformed generated carrier, or malformed sibling expected file → `correctness.spec-verify-malformed` CRITICAL. The same invocation also enforces PLAN's declared `authorized_surface` (the json block under `.devlyn/plan.md`'s `<!-- devlyn:authorized-surface -->` section, located by that sentinel regardless of the heading's language) against this run's diff and untracked delta: any changed path or created-during-run untracked path outside the declared surface → `scope.out-of-scope-file` CRITICAL (`.devlyn/` exempt) — the only sanctioned fix is removing the file, never widening the declared surface, since that would let the same worker that leaked scope self-authorize the leak; missing sentinel, malformed `plan.md`/surface block, or missing `.devlyn/untracked.baseline` → `scope.authorized-surface-malformed` CRITICAL. This scope check runs only here (BUILD_GATE), not when VERIFY MECHANICAL reuses this script post-CLEANUP, because CLEANUP's own allowlist legitimately touches paths PLAN never declared.
5. **Browser** (only when diff touches `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `page.*`, `layout.*`, `route.*`, `*.css`, `*.html`): start the dev server and run the repo's existing browser checks, or a minimal curl/HTML check when no browser test harness exists. Each failed check → finding, severity `HIGH`, rule `correctness.browser-flow-failed`.

Append all findings; do not stop on the first failure.
</gates>

<output>
- `.devlyn/build_gate.findings.jsonl` — JSONL stream, one finding per line. Schema: `{id, rule_id, severity, file, line, message, fix_hint, criterion_ref}`.
- `.devlyn/build_gate.log.md` — human-readable gate results with raw output or links to complete raw-output files, using sealed artifacts where available. Retain complete inventories/hash maps in `.devlyn/` files; report their paths, digests and relevant deltas instead of dumping them into the conversation.
- Report `PASS` if zero CRITICAL/HIGH findings, `FAIL` for genuine product findings, or `BLOCKED:build-env-underprovisioned` only for the evidence-backed capability path above. A capability blocker leaves no product finding. Do not edit `pipeline.state.json` yourself — the orchestrator records it via `state-phase-write.py` from these artifacts.
</output>

<quality_bar>
- Same commands every time. Configuration drift between this gate and CI is a defect; raise as a finding rather than soften this gate. A package-script declaration alone is not evidence that CI executes it.
- Forbidden-pattern check (regex against `git diff`) for `spec.expected.json.forbidden_patterns` runs as part of step 4. Disqualifier-severity matches → CRITICAL findings.
- Reporter artifacts the gate generates (Playwright traces, coverage HTML) belong in gitignored paths. If they leak into `git diff --stat`, flag as `scope.tooling-artifact-leak` MEDIUM and let the fix loop / cleanup handle removal.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. The gate is mechanical — its discipline is "do not skip a check, do not paraphrase a verification command, do not narrow severity to mute noise." Findings drive the fix loop; muting findings without a justified spec exception is a workaround.
</runtime_principles>
