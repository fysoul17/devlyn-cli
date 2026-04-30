# Build Gate — Project Type Detection & Commands

Reference for PHASE 1.4 (Build Gate). The build gate agent reads this file to determine which commands to run.

---

## Project Type Detection Matrix

Inspect the repository root and subdirectories (up to 2 levels). A repo can match **multiple** signals — run ALL matching gates. Do not pick "the main one"; a monorepo with a Next.js dashboard + Rust service needs both.

| Signal file(s) | Project type | Gate commands (run in order) |
|---|---|---|
| `package.json` with `next` dep | Next.js | `npx tsc --noEmit` → `npx next build` |
| `package.json` with `nuxt` dep | Nuxt | `npx nuxi typecheck` → `npx nuxi build` |
| `package.json` with `vite` + `tsconfig.json` | Vite+TS | `npx tsc --noEmit` → `npm run build` (if script exists) |
| `package.json` with `expo` dep | Expo (React Native) | `npx tsc --noEmit` → `npx expo-doctor` |
| `package.json` with `react-native` (no expo) | React Native | `npx tsc --noEmit` |
| `package.json` with `svelte` + `@sveltejs/kit` | SvelteKit | `npm run check` → `npm run build` |
| `package.json` only, has `build` script | Generic Node | `npm run build` |
| `package.json` only, has `tsconfig.json` but no `build` | TS library | `npx tsc --noEmit` |
| `pnpm-workspace.yaml` / `turbo.json` / `lerna.json` | Monorepo | `pnpm -r build` or `turbo run build typecheck lint` — **workspace-wide**, NOT just the changed package |
| `Cargo.toml` | Rust | `cargo check --all-targets` → `cargo clippy -- -D warnings` |
| `go.mod` | Go | `go build ./...` → `go vet ./...` |
| `foundry.toml` | Foundry (Solidity) | `forge build` |
| `hardhat.config.{js,ts,cjs}` | Hardhat (Solidity) | `npx hardhat compile` |
| `Anchor.toml` | Anchor (Solana) | `anchor build` |
| `Move.toml` | Move (Sui/Aptos) | `sui move build` or `aptos move compile` |
| `pyproject.toml` / `setup.py` + mypy config | Python+mypy | `mypy .` |
| `pyproject.toml` with `ruff` | Python+Ruff | `ruff check .` |
| `Package.swift` | Swift package | `swift build` |
| `*.xcodeproj` / `*.xcworkspace` | iOS/macOS (Xcode) | Skip by default — log "Xcode project detected, manual build gate recommended". Too project-specific without knowing the scheme. |
| `build.gradle*` / `settings.gradle*` | Gradle/Android | `./gradlew assembleDebug` (debug, not release — keep it fast) |
| `CMakeLists.txt` | C/C++ (CMake) | `cmake -B build && cmake --build build` |
| `Makefile` (with no other signals) | Generic Make | `make` (only if no other type matched — Makefiles are too generic) |
| `Unity/ProjectSettings/` or `ProjectSettings/ProjectVersion.txt` | Unity | Skip by default — log "Unity project detected, manual build gate recommended" |
| `project.godot` | Godot | Skip by default — log "Godot project detected, manual build gate recommended" |
| `Dockerfile*` | Docker | `docker build -f <dockerfile> -t _pipeline_gate_test .` — included by default in `auto` mode. Skip with `--build-gate no-docker`. |

## Package Manager Detection

Respect the project's package manager. Check in order:
1. `packageManager` field in root `package.json` → use that
2. `pnpm-lock.yaml` exists → `pnpm`
3. `yarn.lock` exists → `yarn`
4. `bun.lockb` / `bun.lock` exists → `bun`
5. Default → `npm`

Replace `npm run build` / `npx` accordingly: `pnpm build` / `pnpm exec`, `yarn build` / `yarn`, `bun run build` / `bunx`.

## Monorepo Handling

Monorepo is the most critical case — cross-package type drift is the #1 source of "tests pass locally, build fails in CI."

1. Detect workspace root markers: `pnpm-workspace.yaml`, `turbo.json`, `lerna.json`, `workspaces` in root `package.json`
2. Run gates at the **workspace root** level, not per-changed-package:
   - Turbo: `turbo run build typecheck lint` (respects dependency graph)
   - pnpm: `pnpm -r build` (runs in topological order)
   - yarn workspaces: `yarn workspaces foreach -A run build`
   - npm workspaces: `npm run build --workspaces`
3. This ensures Package A's type change that breaks Package B's consumer is caught, even if only Package A was directly modified.

## Strict Mode (`--build-gate strict`)

When strict mode is set, treat warnings as failures:
- TypeScript: add `--strict` if not already in tsconfig (or verify it's set)
- Clippy: `-D warnings` (already default in the matrix)
- ESLint: `--max-warnings 0`
- Go vet: already treats warnings as errors
- Foundry: `--deny-warnings`

In default (auto) mode, only hard errors (non-zero exit code from the tool's perspective) block.

## Docker Build (default in `auto` mode)

When `Dockerfile*` files are detected AND `--build-gate no-docker` is NOT set:
1. Run all non-Docker gates first (they're faster and catch most errors before the slow Docker step)
2. Then run `docker build -f <dockerfile> -t _pipeline_gate_test .` for each Dockerfile found in the repo root and subdirectories (up to 2 levels)
3. If Docker daemon is not available, log the skip with a warning but do NOT fail — developers without Docker should not be blocked. The warning should note: "Docker builds were skipped because the Docker daemon is unavailable. Use `--build-gate no-docker` to suppress this warning, or ensure Docker is running to catch Dockerfile-specific issues."
4. This catches Dockerfile-specific issues that no other gate can: COPY paths referencing files excluded by .dockerignore, multi-stage build failures, production-only dependency resolution, and environment differences between dev and container builds

Use `--build-gate no-docker` to skip Docker builds for faster iteration during development — the language-level gates (tsc, cargo check, etc.) still run and catch the majority of issues. Docker builds are most valuable as a final gate before shipping.

## Output Format

Emit two files plus one state update (schemas: `references/findings-schema.md`, `references/pipeline-state.md`).

### 1. `.devlyn/build_gate.findings.jsonl`

One JSON line per failing command's extracted root cause. Do NOT emit findings for PASSING commands. Each line follows the canonical findings schema:

```jsonl
{"id":"BGATE-0001","rule_id":"build.type-error","level":"error","severity":"HIGH","confidence":0.99,"message":"Property 'config' does not exist on type 'SettingsTabsProps'","file":"dashboard/app/(dashboard)/settings/page.tsx","line":90,"phase":"build_gate","criterion_ref":null,"fix_hint":"Read dashboard/app/(dashboard)/settings/page.tsx:88-93 and dashboard/components/settings/SettingsTabs.tsx (the SettingsTabsProps type definition). Either add 'config' to SettingsTabsProps or remove the prop from the parent.","blocking":true,"status":"open"}
```

Dedup key is `(rule_id, file, line)` per `findings-schema.md` — no fingerprint bookkeeping (removed in v3.4).

Suggested `rule_id` values: `build.type-error`, `build.lint-violation`, `build.dep-missing`, `build.docker-copy-mismatch`, `build.module-not-found`, `build.compile-error`.

### 2. `.devlyn/build_gate.log.md`

Human-readable run log. This is where the FULL raw stderr/stdout lives — not in the JSONL `message`. Structure:

```markdown
# Build Gate Run Log
## Detected Project Types
- [type] ([path/])

## Commands
| # | Command | Dir | Exit | Time |
|---|---|---|---|---|
| 1 | `npx tsc --noEmit` | dashboard/ | 0 | 4.2s |
| 2 | `npx next build` | dashboard/ | 1 | 9.8s |

## Raw Output — failing commands only

### #2: `npx next build` (dashboard/, exit 1)
\`\`\`
[full raw output — keep for debugging]
\`\`\`
```

### 3. Update `pipeline.state.json`

Set `phases.build_gate`:
- `verdict`: `PASS` if all exit codes == 0, else `FAIL`. If no gates detected, `PASS` with a note in log.md ("No build gate detected — project type unknown; consider adding `--build-gate deploy` if Dockerfiles are present.")
- `engine: "bash"`, `model: null`
- `started_at`, `completed_at`, `duration_ms`, `round`
- `artifacts.findings_file: ".devlyn/build_gate.findings.jsonl"`, `artifacts.log_file: ".devlyn/build_gate.log.md"`

The orchestrator branches on `phases.build_gate.verdict` — it does NOT re-read the findings or log file for routing decisions.

## Spec literal check (iter-0019.6)

In addition to the language-specific gates above, the BUILD_GATE Agent always invokes the spec-literal verifier:

```bash
python3 .claude/skills/_shared/spec-verify-check.py
```

The script reads `.devlyn/spec-verify.json`. **Three staging paths** (iter-0019.8 + iter-0019.9):

1. **Benchmark fixtures**: pre-staged by `benchmark/auto-resolve/scripts/run-fixture.sh:200-219` directly from `expected.json:verification_commands`. iter-0019.9: when `BENCH_WORKDIR` is set AND a pre-staged file already exists at script start, that contract is **authoritative** — the script skips source-extract entirely. This closed an F9 regression where the e2e novice flow's ideate-generated spec ships its own `## Verification` ` ```json ` block that drifts from the benchmark's expected.json contract (different field names, different output format), and the source-extract was overwriting the benchmark contract.
2. **Real-user runs (spec source)**: the script self-stages from `pipeline.state.json:source.spec_path` by extracting the canonical ` ```json ` fenced block under the spec's `## Verification` H2 section, **always overwriting** any pre-existing `.devlyn/spec-verify.json` (a stale file from a killed prior run is dropped — never trusted). `/devlyn:ideate` ships every item spec with this block (see `devlyn:ideate/references/templates/item-spec.md`) and validates each spec post-write via `--check` mode. Handwritten specs without the block: silent no-op (preserves iter-0019.6 backward compat); any stale pre-staged file is dropped.
3. **Real-user runs (generated source)**: same self-staging from `source.criteria_path` (`.devlyn/criteria.generated.md`). Generated criteria without the block emit a CRITICAL `correctness.spec-verify-malformed` finding so the fix-loop reruns BUILD — generated paths must ship a verifiable contract per `references/phases/phase-1-build.md` `<output_contract>`.

When present, the script runs each `verification_commands` entry in the work-dir, captures **combined stdout+stderr** (mirroring the post-run verifier semantics in `run-fixture.sh:431-450`), and asserts:

- `proc.returncode == expected.exit_code`
- All `stdout_contains` literals appear in combined output
- None of `stdout_not_contains` literals appear in combined output

On mismatch (per command):
- One CRITICAL finding written to `.devlyn/spec-verify-findings.jsonl` with `rule_id = "correctness.spec-literal-mismatch"`, `criterion_ref = "spec-verify://verification_commands/<index>"`, `blocking = true`, `status = "open"`. Schema matches `references/findings-schema.md`.
- Full per-command evidence (expected vs actual exit, stdout tail, reason) written to `.devlyn/spec-verify.results.json`.

**Merge step**: after running spec-verify-check.py, append `.devlyn/spec-verify-findings.jsonl` onto `.devlyn/build_gate.findings.jsonl` so the existing fix-loop picks the findings up unchanged. The verdict logic is unchanged — any CRITICAL finding in build_gate.findings.jsonl forces verdict=FAIL → PHASE 2.5.

**Why this exists** (iter-0019 lesson): F9's prompt-only "literal-verification rule" in `phase-2-evaluate.md` `<quality_bar>` (added in iter-0018.5) was empirically dead — verify=0.4 on F9 across all engines in the iter-0019 paid run. Same shape as iter-0008 prompt-only engine constraint dead-end. Mechanical bash-gate enforcement at BUILD_GATE forces the contract to be machine-checked before BUILD declares completion.

**Out of scope for iter-0019.6**: forbidden_patterns silent-catch enforcement (still post-run-only), tier_a_waivers, deps caps, scope-tier oracles. Each has its own enforcement layer.
