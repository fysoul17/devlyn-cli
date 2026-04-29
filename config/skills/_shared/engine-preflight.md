# Shared — `--engine` Pre-flight

Used by `devlyn:auto-resolve`, `devlyn:ideate`, `devlyn:preflight`. One shared availability rule so every skill routes identically.

## Rule

Each skill resolves the effective engine from its own SKILL.md default plus any explicit `--engine` flag passed by the user. This pre-flight runs **only when the resolved engine is `auto` or `codex`** — when the resolved engine is `claude` (whether by skill default or explicit flag), the Codex check is skipped entirely.

When the resolved engine is `auto` or `codex`, on entry (before spawning any phase that could route to Codex):

1. Check if the Codex CLI is installed: `command -v codex >/dev/null 2>&1` (or equivalent bash test).
2. On failure → silently set `engine = "claude"` for the remainder of this run AND log `engine downgraded: codex-unavailable` into the skill's final summary/report header.
3. On success → proceed with the original engine value.

Never prompt the user. Never abort the run on missing CLI.

Per-skill defaults: `devlyn:auto-resolve` defaults to `claude` (post iter-0020 close-out — pair-mode below quality floor); `devlyn:ideate`, `devlyn:preflight`, `devlyn:team-resolve`, and `devlyn:team-review` default to `auto`. Each skill's SKILL.md flag block is the source of truth for that skill's default.

## Why this is the one permitted silent fallback

`CLAUDE.md` sets the no-silent-fallback rule for this repo. This downgrade is documented there as the single explicit exception because the hands-free contract — skills the user walks away from — would otherwise fail every run whenever the Codex CLI is absent. The user-visible behavior is identical to an explicit `--engine claude` invocation, and the banner in the final report removes the silence. Any other silent fallback in skills code is a bug.

## What a skill must log after downgrade

When the resolved engine was `auto` / `codex` and the Codex CLI was absent, the final user-facing report/summary shows both the requested and effective mode:

```
Engine: claude (downgraded from auto — codex-unavailable)
```

If no downgrade happened (either Codex was available, or the resolved engine was already `claude`), omit the parenthetical. That single line is the contract — the user can always see why Codex did or did not participate.

## Canonical Codex invocation

See `config/skills/_shared/codex-config.md` for the canonical wrapper invocation and flag set skills should use after the availability check passes.
