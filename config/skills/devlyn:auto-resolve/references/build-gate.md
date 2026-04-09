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

Write results to `.devlyn/BUILD-GATE.md`:

```markdown
# Build Gate Results
## Verdict: [PASS / FAIL]
## Detected Project Types
- [type] ([path/])
## Gate Commands Run
| # | Command | Dir | Exit | Status | Time |
|---|---|---|---|---|---|
| 1 | `npx tsc --noEmit` | dashboard/ | 0 | PASS | 4.2s |
| 2 | `npx next build` | dashboard/ | 1 | FAIL | 9.8s |
| 3 | `cargo check --all-targets` | services/indexer/ | 0 | PASS | 12.1s |

## Failures

### Command #2: `npx next build` (dashboard/, exit 1)
```
[full error output — do NOT truncate. Build errors reference files from earlier in output.]
```

**Root file:line(s)**:
- `dashboard/app/(dashboard)/settings/page.tsx:90` — Type error: Property 'config' does not exist on type 'SettingsTabsProps'

**Fix guidance**:
Read `dashboard/app/(dashboard)/settings/page.tsx:88-93` and `dashboard/components/settings/SettingsTabs.tsx` (the SettingsTabsProps type definition). Either add `config` to SettingsTabsProps or remove the prop from the parent. Then re-run `npx next build` from `dashboard/` to verify.
```

Verdict rules:
- Any exit code != 0 → **FAIL**
- All exit codes == 0 → **PASS**
- No gates detected → **PASS** with note "No build gate detected — project type unknown. Consider adding `--build-gate deploy` if Dockerfiles are present."
