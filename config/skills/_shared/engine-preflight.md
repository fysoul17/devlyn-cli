# Shared — `--engine` Pre-flight

Used by `devlyn:auto-resolve`, `devlyn:ideate`, `devlyn:preflight`. One shared availability rule so every skill routes identically.

## Rule

If the caller did NOT pass `--engine claude` explicitly, the engine is `auto` by default. On entry (before spawning any phase that could route to Codex):

1. Check if the Codex CLI is installed: `command -v codex >/dev/null 2>&1` (or equivalent bash test).
2. On failure → silently set `engine = "claude"` for the remainder of this run AND log `engine downgraded: codex-unavailable` into the skill's final summary/report header.
3. On success → proceed with the original engine value.

Never prompt the user. Never abort the run on missing CLI.

## Why this is the one permitted silent fallback

`CLAUDE.md` sets the no-silent-fallback rule for this repo. This downgrade is documented there as the single explicit exception because the hands-free contract — auto-resolve, autofix preflight, ideate flows the user walks away from — would otherwise fail every run whenever the Codex CLI is absent. The user-visible behavior is identical to an explicit `--engine claude` invocation, and the banner in the final report removes the silence. Any other silent fallback in skills code is a bug.

## What a skill must log after downgrade

In the final user-facing report/summary, the engine line shows both the requested and effective mode:

```
Engine: claude (downgraded from auto — codex-unavailable)
```

If no downgrade happened, omit the parenthetical. That single line is the contract — the user can always see why Codex did or did not participate.

## Canonical Codex invocation

See `config/skills/_shared/codex-config.md` for the canonical wrapper invocation and flag set skills should use after the availability check passes.
