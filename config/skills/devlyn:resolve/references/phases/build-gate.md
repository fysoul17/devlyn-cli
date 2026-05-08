# PHASE 3 — BUILD_GATE (canonical body)

Per-engine adapter header is prepended at runtime. BUILD_GATE is mechanical / deterministic — same commands CI / Docker / production run.

<role>
Run language-specific gates and the spec literal-match verification. Emit findings; the orchestrator's fix loop consumes them.
</role>

<detection>
Detect the project shape from files in `state.base_ref.sha`:

- `package.json` → Node. Use the declared package manager; default `npm`. If `tsconfig.json` exists → run `tsc --noEmit`.
- `pyproject.toml` / `requirements.txt` → Python. If `pyproject.toml` declares a tool config (`ruff`, `mypy`, `pytest`), run the declared tool.
- `go.mod` → Go. Run `go build ./... && go vet ./... && go test ./...`.
- `Cargo.toml` → Rust. Run `cargo build && cargo clippy && cargo test`.
- Mixed / monorepo: detect per-workspace; run only against changed workspaces (use `git diff --name-only <state.base_ref.sha>`).
</detection>

<gates>
Run in this order; each emits findings into `.devlyn/build_gate.findings.jsonl`:

1. **Type check** (TypeScript / mypy / etc.). Each error → one finding, severity `HIGH`, rule `correctness.type-check`.
2. **Lint** (eslint / ruff / clippy / etc.). Each error → finding, severity `MEDIUM`, rule `quality.lint`. Warnings stay LOW unless the spec elevates them.
3. **Test suite** (npm test / pytest / go test / cargo test). Each failing test → finding, severity `HIGH`, rule `correctness.test-failure`. Include the failing test's file:line and the assertion.
4. **Spec literal verification + risk probes**: `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes`. The script reads `.devlyn/spec-verify.json` (pre-staged from spec or self-staged from `state.source.spec_path`) and appends `.devlyn/risk-probes.jsonl` when present. Each verification command mismatch → finding `correctness.spec-literal-mismatch`, severity `CRITICAL`. Each risk-probe mismatch → finding `correctness.risk-probe-failed`, severity `CRITICAL`. Missing/malformed carrier on a generated source → finding `correctness.spec-verify-malformed`, severity `CRITICAL`.
5. **Browser** (only when `spec.expected.json.browser_flows` declared OR diff touches `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `page.*`, `layout.*`, `route.*`, `*.css`, `*.html`): start dev server, run declared flows via Chrome MCP if available, falling back to Playwright, falling back to curl. Each failed flow → finding, severity `HIGH`, rule `correctness.browser-flow-failed`.

Append all findings; do not stop on the first failure.
</gates>

<output>
- `.devlyn/build_gate.findings.jsonl` — JSONL stream, one finding per line. Schema: `{id, rule_id, severity, file, line, message, fix_hint, criterion_ref}`.
- `.devlyn/build_gate.log.md` — human-readable summary of which gates ran and their raw output.
- `state.phases.build_gate.{verdict, completed_at, duration_ms, artifacts}`. Verdict: `PASS` if zero CRITICAL/HIGH findings; `FAIL` otherwise.
</output>

<quality_bar>
- Same commands every time. Configuration drift between this gate and CI is a defect; raise as a finding rather than soften this gate.
- Forbidden-pattern check (regex against `git diff`) for `spec.expected.json.forbidden_patterns` runs as part of step 4. Disqualifier-severity matches → CRITICAL findings.
- Reporter artifacts the gate generates (Playwright traces, coverage HTML) belong in gitignored paths. If they leak into `git diff --stat`, flag as `scope.tooling-artifact-leak` MEDIUM and let the fix loop / cleanup handle removal.
</quality_bar>

<runtime_principles>
Read `_shared/runtime-principles.md`. The gate is mechanical — its discipline is "do not skip a check, do not paraphrase a verification command, do not narrow severity to mute noise." Findings drive the fix loop; muting findings without a justified spec exception is a workaround.
</runtime_principles>
