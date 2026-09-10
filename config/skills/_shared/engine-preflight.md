# Shared — Engine Pre-flight

Used by `/devlyn:resolve` and `/devlyn:ideate`. One shared availability rule so every skill routes identically.

## Rule

Each skill resolves the effective engine from its own SKILL.md default plus any explicit `--engine` flag passed by the user. `/devlyn:resolve` also computes the default VERIFY-pair route and conditional risk-probe requirements before the phase that needs the OTHER engine.

Engine requirements have two classes:

- **Explicit routes** — `--engine`, `--risk-probes`, `--pair-verify`, configured executor/role/priority pins. These are promises. If the required engine is unavailable, fail closed with `BLOCKED:<engine>-unavailable` and never downgrade to solo.
- **Automatic routes** — high-risk risk-probes remain conditional; VERIFY pair-JUDGE is selected by default unless `--no-pair` was passed. Both require an available OTHER engine. If it is absent, proceed solo and report the skipped route and reason. This is route selection, not a fallback.

## Role resolution

The orchestrator is the CLI the user opened. PLAN remains orchestrator-fixed. Resolve the legacy executor as explicit `--engine` > `cwd/.devlyn/engines.json` `executor` > the invoking skill's supported default. BUILD_GATE and risk-probe derivation keep their existing routes.

The role profiles and `--role-config` below apply only to `/devlyn:resolve`; `/devlyn:ideate` keeps its existing `--engine` / legacy executor selection and never inherits worker/judge profiles. `role-config.py` is resolve’s deterministic resolver. Optional project `roles.worker`, `roles.primary_judge`, and `roles.pair_judge` each require `engine` and accept exact `model`/`effort`; `/devlyn:resolve --role-config <path>` supplies the same `{"roles": {...}}` object for one run. Each entry replaces the entire lower entry. Worker/primary precedence is run role > `--engine` engine-only > project role > legacy executor. Pair precedence is run role > project role > existing `pair_judge_priority`/binary complement. An absent primary profile follows the legacy executor, not the worker profile. No parent/global devlyn config lookup.

Worker controls IMPLEMENT/CLEANUP and their repair rounds only; primary/pair control VERIFY only. OTHER must differ from the resolved primary engine. Explicit same-engine pair is invalid; a legacy priority list skips the primary. `--no-pair` does not dispatch or check availability of an unused pair. Configured pins remain explicit promises, while an unconfigured unavailable automatic OTHER records its solo reason.

Before the first phase, `/devlyn:resolve` freezes resolution with `state-phase-write.py --freeze-roles`; subsequent status/dispatch reads that state instead of mutable config. `state.engine` stays the legacy executor. The resolver rejects statically unsupported selected channel fields before PLAN, and validates adapter names and the existing ASCII `executor: yes|no` / `pair_judge: yes|no` eligibility markers; absent eligibility section means both. Malformed configuration fails with `BLOCKED:invalid-engine-config`.

Before each affected worker/judge, read `role-config.py --state .devlyn/pipeline.state.json --role <role> [--resolved-model <inherited-exact-model>]`. It returns source/channel, requested values and argv additions. Explicit Codex options require current version-matching native model metadata; refresh the native CLI's cache when missing/stale. Explicit Claude judge effort requires the adapter's version/exact-model capability declaration; model-only selection passes the exact ID without that effort declaration and validates the native result. No model/effort fields means unchanged phase defaults. Unknown support fails with `BLOCKED:unsupported-role-option`; no clamp, fallback or invented model identity. Native Agent workers reject unsupported explicit Claude fields without switching to a CLI worker. Show inherited/unknown values honestly; availability is not role fitness.

Engine-only adapter routes remain supported according to existing eligibility. New adapters do not automatically gain explicit model/effort mappings. Status reports unavailable pins and unresolved legacy channels without weakening run freeze/dispatch. CLI presence is not authentication. Status never launches a model, changes user configuration or promotes a default.

When a run or phase requires engine `<name>` (claude, codex, omp, or any adapter-backed engine), before spawning that phase:

1. Run the adapter's availability probe — default `command -v <name> >/dev/null 2>&1`; an adapter's `## Invocation` section may declare a stricter contract (e.g. `adapters/claude.md`: the probe is necessary but not sufficient under a network-denying sandbox, so a failed spawn is handled identically to a failed probe).
2. On failure -> set the current phase/run verdict to `BLOCKED:<name>-unavailable`, preserve the failed check evidence, and show the adapter's setup guidance: install/configure that CLI, run its auth/login flow, verify `<name> --version`, then rerun. If the user intentionally wants solo VERIFY, they may rerun with `--no-pair`.
3. On success -> proceed with the original engine value.

Never prompt the user mid-pipeline. Missing engines for explicit routes are BLOCKED states, not silent fallbacks. Missing OTHER engines for automatic escalations are reported solo-skips, not fallbacks — the auto route was never selected.

Per-skill defaults: `/devlyn:resolve` uses Claude for PLAN/IMPLEMENT when the orchestrator has Claude Code's native Agent primitive; Codex CLI and oh-my-pi orchestrators use their own fresh worker as the default route (Codex child process, omp native `task`) so the pipeline still has structural phase isolation. VERIFY invokes the OTHER engine by default when available unless `--no-pair` was passed. `/devlyn:ideate` defaults to Claude; `--engine` selects the elicitation/normalization adapter, not an automatic cross-model challenge phase. Any future ideate read-only critique must follow `_shared/codex-config.md` isolation rules. Each SKILL.md flag block is source of truth for that skill's default.

## What a skill must report after a BLOCKED engine check

When an engine required by the selected route or default VERIFY pair route is absent, the final user-facing report/summary shows the requested route, the missing engine, and setup steps:

```
Engine: claude + codex pair required
Verdict: BLOCKED:codex-unavailable
Setup: install/configure Codex CLI; run the current Codex auth/login flow; verify `codex --version`; rerun. Use `--no-pair` only for an intentional solo VERIFY run.
```

Do not report a downgraded successful run when a required engine is missing.

## Canonical cross-engine invocations

For native Windows, use native Node/npm and Python (`python3` on PATH), with Git for Windows Bash for the shipped shell wrapper. Supported npm engine shims resolve to native argv; unsupported/malformed shims fail visibly. Deliver multiline prompts from files: Codex uses `DEVLYN_CODEX_PROMPT_FILE` with explicit `-`; Claude uses `run-bounded.py 600 --stdin-file <prompt-file> -- claude -p`. Retain generated transport evidence. A policy-denied Codex judge read uses the complete inline no-tools packet in `_shared/codex-config.md#constrained-windows-judge-reads`, keeping read-only isolation and the selected role.

After the availability check passes, Codex keeps the monitored `codex-monitored.sh`
path; every other resolved OTHER engine follows `_shared/adapters/<name>.md`
`## Invocation`. Capture `.devlyn/<name>-judge.stdout`, then normalize it with
`collect-codex-findings.py --devlyn-dir "<abs repo>/.devlyn" --stdout-file
<name>-judge.stdout`. A non-zero collector exit writes no canonical findings:
the pair source is `BLOCKED` for `verify.pair.emission-contract`, and unparsed
stdout remains diagnostic-only rather than being merged. On exit 124, the
timeout marker's `engine` field is the resolved `<name>`.
