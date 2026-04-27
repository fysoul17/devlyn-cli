# 0011 — Lint Check 10 tighten + priming-token scrub

**Status**: SHIPPED
**Started**: 2026-04-27
**Decided**: 2026-04-27 (same-day, no benchmark — surgical hardening with falsification canary)

## Hypothesis

iter-0010 shipped wrapper-form skill prompts and lint Check 10 as a static gate against the iter-0008 byte-watchdog starvation profile. Two residual gaps survive:

1. **Check 10 evasion shapes.** The pattern `codex exec (-|resume[[:space:]]|\\$)` only matches `codex exec` followed by a flag (`-`), the `resume ` keyword, or a line-continuation backslash. It misses:
   - `codex exec "<prompt>"` — quoted prompt with no leading flag.
   - `codex exec $VAR` — variable expansion.
   - `codex exec prompt-arg` — bare literal token.
   Any of these would re-introduce the iter-0008 risk surface.
2. **Priming-token leakage in prompt-facing docs.** Codex iter-0010 R2 lesson #17: descriptive phrases that name `codex exec` (even backtick-closed) prime the orchestrator's prior toward emitting the raw shape. iter-0010 scrubbed three sites in team-resolve / team-review SKILL.md but left residual mentions in `engine-routing.md`, `_shared/codex-config.md`, and `_shared/engine-preflight.md`.

iter-0011 closes both gaps. No mechanism change.

## Mechanism

Why-chain (extending iter-0010 at #48):

49. Why does Check 10 need broader coverage? → Codex cross-check identified `codex exec "<prompt>"` (quoted-string evasion) as a viable orchestrator emission shape that the current pattern misses. The pattern is shape-based, not exhaustive — extending it to invocation-class is cheap and removes the evasion vector.
50. Why is `codex exec[[:space:]]+\S` the right discriminator? → invocation always has whitespace + non-whitespace after `exec` (flag `-`, resume keyword, line-continuation `\`, quote `"`, variable `$`, bare token); descriptive prose closes the inline-code with a backtick immediately after `exec` (no whitespace). The discriminator splits the two classes cleanly.
51. Why scrub priming tokens that aren't invocation-shaped? → iter-0010 R2 documented that even descriptive `codex exec` mentions in prompt-facing docs leak the token into the orchestrator's prior. Removing them where meaning survives reduces the prior weight without changing what the docs communicate.
52. Why keep the token in `codex-config.md:34`? → That line *expresses the rule* ("Raw `codex exec ...` invocations are forbidden"). Removing the token would make the rule unreadable. Rule-expression mentions are necessary; descriptive mentions aren't.
53. Root: the static gate now binds invocation-class (not just specific shapes), and prompt-facing docs no longer prime invocation-class on their own.

## Predicted change

Static-only (no benchmark gate, mechanism unchanged from iter-0009):

- **Lint Check 10 PASSES** with the broader pattern across all 4 standalone Codex-using skills + auto-resolve.
- **Falsification canary catches all 6 invocation shapes** (single-line flag, resume, multi-line continuation, quoted prompt, variable expansion, literal token) and 0 false-positives on backtick-closed descriptive prose.
- **Mirror parity Check 6 PASSES** after surgical sync of edited files to `.claude/skills/`.
- **Wrapper canary unchanged** — pipe-stdout exits 64 with iter-0009 R2 banner, file-stdout exits 0 with `[codex-monitored] start:` on stderr.

## Diff plan

Five edits — pure text rewrites, no new files, no new abstractions.

1. **`scripts/lint-skills.sh`** (EDIT). Check 10 pattern `codex exec (-|resume[[:space:]]|\\$)` → `codex exec[[:space:]]+\S`. Comment block updated to enumerate all 6 invocation shapes (3 originals + 3 added: quoted prompt, variable expansion, literal token).
2. **`config/skills/devlyn:auto-resolve/references/engine-routing.md`** (EDIT, 2 sites). Line 5: `the local `codex exec` CLI` → `the wrapper at `_shared/codex-monitored.sh``. Line 7: `passes args through to `codex exec`` → `passes args through verbatim to the underlying CLI`.
3. **`config/skills/_shared/codex-config.md`** (EDIT, 4 sites). Line 3: `Skills shell out to the local `codex exec` CLI` → `Skills shell out via the wrapper`. Line 7 (two mentions): wrapper passthrough rephrased without `codex exec`. Line 38: `Before the first `codex exec` call` → `Before the first Codex call`. Line 48: `The `codex exec` CLI is the primary` → `The local Codex CLI (fronted by `codex-monitored.sh`) is the primary`. Line 34 unchanged (rule expression).
4. **`config/skills/_shared/engine-preflight.md`** (EDIT, 1 site). Line 31: `the exact `codex exec` flag set` → `the canonical wrapper invocation and flag set`.
5. **Mirror sync** of the 3 edited files into `.claude/skills/` (surgical `cp`, since Check 6 mirror parity covers `engine-routing.md` and `codex-config.md`).

NOT in this diff:

- **Shim distribution to user installs.** Still deferred; Codex concurred that it's speculative defense without observed production regression. Cheaper hardening (this iter) closes the most likely leak vector first.
- **iter-0012 timed_out derivation fix** and **iter-0013 F1 starvation diagnostic** queued next per HANDOFF (numbers shift up by 1 from prior queue).

## Falsification gate result (2026-04-27)

All gates passed.

### Check 10 evasion canary (synthetic SKILL.md with all 6 shapes + 2 descriptive)

```
config/skills/canary-skill/SKILL.md:5:    codex exec "do the thing"           ← caught
config/skills/canary-skill/SKILL.md:9:    codex exec $PROMPT                   ← caught
config/skills/canary-skill/SKILL.md:13:    codex exec prompt-arg               ← caught
config/skills/canary-skill/SKILL.md:17:    codex exec -C /repo                 ← caught (regression check)
config/skills/canary-skill/SKILL.md:21:    codex exec resume --last            ← caught (regression check)
config/skills/canary-skill/SKILL.md:25:    codex exec \                        ← caught (regression check)
```
6/6 invocation shapes caught. 0/2 false-positives on backtick-closed descriptive prose (`` `codex exec` ``).

### Static gate (lint-skills.sh, all 10 checks)

`All checks passed.`

### Wrapper canary

- **A. pipe-stdout** (`bash codex-monitored.sh 2>err | cat >/dev/null`, with `set -o pipefail`) → exit 64, stderr first line `[codex-monitored] error: stdout is a pipe.`. ✓
- **B. file-stdout** (`bash codex-monitored.sh --version >out 2>err`) → exit 0, stderr first line `[codex-monitored] start: ts=... heartbeat=30s bin=codex`. ✓

## Codex collaboration

- **R0 (decision)**: presented Option A (shim distribution) / B (timed_out derivation) / C (F1 starvation) plus my independent take that A is speculative defense per Karpathy #2 (Simplicity First). Codex concurred: defer A, ordered B → C, but flagged a real risk class — runtime emission drift (`codex exec "<prompt>"` evasion shape). Proposed Option D = cheap hardening (lint tighten + priming scrub) as preemptive close.
- This iteration is Option D. iter-0012 / iter-0013 queue follows.

## Lessons

- **Shape-based lint patterns must cover the invocation *class*, not just the shapes seen in prior iterations.** `codex exec[[:space:]]+\S` is class-level (any whitespace then non-whitespace after `exec`). The earlier `(-|resume[[:space:]]|\\$)` enumeration was tied to the iter-0008 / iter-0010 R2 evidence and would re-leak with the next novel shape.
- **Priming-token scrubbing in prompt-facing docs is part of the gate**, not just lint. iter-0010 scrubbed SKILL.md mentions but left them in shared references that skills also read. Both classes prime the orchestrator equally.
- **Cheap hardening before designed defense.** A had design surface (npm post-install vs. doctor activate, fail-open vs. fail-closed, settings.json merge semantics); D is a 5-edit text pass with a falsification canary. When two options each close a regression vector, prefer the cheaper one and defer the costly one until evidence demands it.
