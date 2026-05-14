# Shared — Engine Pre-flight

Used by `/devlyn:resolve` and `/devlyn:ideate`. One shared availability rule so every skill routes identically.

## Rule

Each skill resolves the effective engine from its own SKILL.md default plus any explicit `--engine` flag passed by the user. `/devlyn:resolve` also computes conditional pair/risk-probe requirements before the phase that needs the OTHER engine.

When a run or phase requires Codex, before spawning that phase:

1. Check if the Codex CLI is installed: `command -v codex >/dev/null 2>&1` (or equivalent bash test).
2. On failure -> set the current phase/run verdict to `BLOCKED:codex-unavailable`, preserve the failed check evidence, and show setup guidance: install/configure the Codex CLI, run the current Codex auth/login flow, verify `codex --version`, then rerun. If the user intentionally wants solo VERIFY, they may rerun with `--no-pair`.
3. On success -> proceed with the original engine value.

When a run or phase requires Claude, before spawning that phase:

1. Confirm the runtime can spawn Claude agents. Where the CLI is the launcher, `command -v claude >/dev/null 2>&1` is the equivalent check.
2. On failure -> set the current phase/run verdict to `BLOCKED:claude-unavailable` and show setup guidance: install/configure Claude Code, verify `claude --version` where available, then rerun.
3. On success -> proceed.

Never prompt the user mid-pipeline. Missing required engines are explicit BLOCKED states, not silent fallbacks.

Per-skill defaults: `/devlyn:resolve` uses Claude for PLAN/IMPLEMENT; VERIFY may invoke the OTHER engine when its pair-JUDGE trigger fires. `/devlyn:ideate` defaults to Claude; `--engine` selects the elicitation/normalization adapter, not an automatic cross-model challenge phase. Any future ideate read-only critique must follow `_shared/codex-config.md` isolation rules. Each SKILL.md flag block is source of truth for that skill's default.

## What a skill must report after a BLOCKED engine check

When an engine required by the selected route or conditional pair trigger is absent, the final user-facing report/summary shows the requested route, the missing engine, and setup steps:

```
Engine: claude + codex pair required
Verdict: BLOCKED:codex-unavailable
Setup: install/configure Codex CLI; run the current Codex auth/login flow; verify `codex --version`; rerun. Use `--no-pair` only for an intentional solo VERIFY run.
```

Do not report a downgraded successful run when a required engine is missing.

## Canonical Codex invocation

See `config/skills/_shared/codex-config.md` for the canonical wrapper invocation and flag set skills should use after the availability check passes.
