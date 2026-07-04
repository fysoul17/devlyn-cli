# Shared — Engine Pre-flight

Used by `/devlyn:resolve` and `/devlyn:ideate`. One shared availability rule so every skill routes identically.

## Rule

Each skill resolves the effective engine from its own SKILL.md default plus any explicit `--engine` flag passed by the user. `/devlyn:resolve` also computes conditional pair/risk-probe requirements before the phase that needs the OTHER engine.

Engine requirements have two classes:

- **Explicit routes** — `--engine`, `--risk-probes`, `--pair-verify`. These are promises. If the required engine is unavailable, fail closed with `BLOCKED:<engine>-unavailable` and never downgrade to solo.
- **Automatic escalations** — auto high-risk risk-probes and auto VERIFY pair-JUDGE inferred from the spec. These are candidate routes, selected only when their preconditions hold, OTHER-engine availability included. If an auto candidate would fire but the OTHER engine is absent, do not select the cross-engine route: proceed solo and report the skipped escalation and its reason. This is route selection, not a fallback.

## Role resolution

Two configurable roles; the orchestrator role is whichever CLI the user opened and is not configurable here.

- **Executor** (IMPLEMENT / CLEANUP / primary VERIFY judge): explicit `--engine` flag > `cwd/.devlyn/engines.json` `executor` > built-in default `claude`. No parent-directory or global config lookup. Requires an adapter that is executor-eligible (below).
- **Pair judge** (VERIFY pair-JUDGE, risk-probe derivation): first entry of `engines.json` `pair_judge_priority` that is (a) adapter-valid, (b) pair-judge-eligible (below), (c) not the primary judge engine, (d) available. When the key or file is absent: the binary claude↔codex complement.

Validation is fail-closed: malformed JSON, any engine name without a `_shared/adapters/<name>.md` adapter file under `DEVLYN_SHARED_DIR`, or an adapter that declares itself ineligible for the requested role, halts with report-level `BLOCKED:invalid-engine-config` naming the offending entry. This is the plug-in point for new engines — ship an adapter file and the name becomes valid with zero skill-body changes. Availability probe default is `command -v <name>`; an adapter may declare a different probe. A pin is an explicit route (same promise class as `--engine`): pinned-but-unavailable → `BLOCKED:<engine>-unavailable`, never a silent downgrade. `engines.json` is machine-local config — not committed, not archived (`archive_run.py` moves only `PER_RUN_PATTERNS`).

**Role eligibility** — an adapter's optional `## Role eligibility` section (`_shared/adapters/README.md`) declares `executor: yes|no` / `pair_judge: yes|no` as fixed ASCII fields. Absent section = eligible for both roles (every adapter shipped before iter-0051). A completion-only local backend with no tool/file-edit access declares `executor: no`: an `executor <name>` pin against it is invalid config, not an availability gap, and fails the same `BLOCKED:invalid-engine-config` path above rather than `BLOCKED:<name>-unavailable`.

The explicit-vs-automatic split above applies unchanged to resolved engines: explicit routes (`--engine`, `--risk-probes`, `--pair-verify`, config pins) fail closed; automatic escalations select a cross-engine route only when the resolved pair-judge engine is available, else proceed solo and report the skip.

When a run or phase requires engine `<name>` (claude, codex, omp, or any adapter-backed engine), before spawning that phase:

1. Run the adapter's availability probe — default `command -v <name> >/dev/null 2>&1`; an adapter's `## Invocation` section may declare a stricter contract (e.g. `adapters/claude.md`: the probe is necessary but not sufficient under a network-denying sandbox, so a failed spawn is handled identically to a failed probe).
2. On failure -> set the current phase/run verdict to `BLOCKED:<name>-unavailable`, preserve the failed check evidence, and show the adapter's setup guidance: install/configure that CLI, run its auth/login flow, verify `<name> --version`, then rerun. If the user intentionally wants solo VERIFY, they may rerun with `--no-pair`.
3. On success -> proceed with the original engine value.

Never prompt the user mid-pipeline. Missing engines for explicit routes are BLOCKED states, not silent fallbacks. Missing OTHER engines for automatic escalations are reported solo-skips, not fallbacks — the auto route was never selected.

Per-skill defaults: `/devlyn:resolve` uses Claude for PLAN/IMPLEMENT when the orchestrator has Claude Code's native Agent primitive; Codex CLI and oh-my-pi orchestrators use their own fresh worker as the default route (Codex child process, omp native `task`) so the pipeline still has structural phase isolation. VERIFY may invoke the OTHER engine when its pair-JUDGE trigger fires. `/devlyn:ideate` defaults to Claude; `--engine` selects the elicitation/normalization adapter, not an automatic cross-model challenge phase. Any future ideate read-only critique must follow `_shared/codex-config.md` isolation rules. Each SKILL.md flag block is source of truth for that skill's default.

## What a skill must report after a BLOCKED engine check

When an engine required by the selected route or conditional pair trigger is absent, the final user-facing report/summary shows the requested route, the missing engine, and setup steps:

```
Engine: claude + codex pair required
Verdict: BLOCKED:codex-unavailable
Setup: install/configure Codex CLI; run the current Codex auth/login flow; verify `codex --version`; rerun. Use `--no-pair` only for an intentional solo VERIFY run.
```

Do not report a downgraded successful run when a required engine is missing.

## Canonical cross-engine invocations

After the availability check passes: a Claude-side orchestrator spawning a Codex judge/worker uses `config/skills/_shared/codex-config.md` (monitored wrapper, canonical flag set); a non-Claude orchestrator spawning a Claude judge uses `_shared/adapters/claude.md` `## Invocation` (headless `claude -p`, locked-down allowlist, hermetic settings).
