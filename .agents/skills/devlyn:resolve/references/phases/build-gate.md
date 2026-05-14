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
4. **Spec literal verification + risk probes**: `python3 .claude/skills/_shared/spec-verify-check.py --include-risk-probes`. The script self-stages from sibling `spec.expected.json` next to `state.source.spec_path`, or the legacy inline carrier when the sibling is absent; benchmark-prestaged `.devlyn/spec-verify.json` still wins. It appends `.devlyn/risk-probes.jsonl` when present, and requires that file when `state.risk_profile.risk_probes_enabled == true`. Malformed `state.risk_profile` is also CRITICAL because it can hide enabled risk probes. Command or risk-probe mismatch → CRITICAL finding. Missing required risk probes, missing/malformed generated carrier, or malformed sibling expected file → `correctness.spec-verify-malformed` CRITICAL.
5. **Browser** (only when diff touches `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `page.*`, `layout.*`, `route.*`, `*.css`, `*.html`): start the dev server and run the repo's existing browser checks, or a minimal curl/HTML check when no browser test harness exists. Each failed check → finding, severity `HIGH`, rule `correctness.browser-flow-failed`.

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
