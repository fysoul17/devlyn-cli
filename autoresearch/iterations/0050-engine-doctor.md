# iter-0050 — engine doctor: detect installed engines, show pairing picture, recommend

**Status**: SHIPPED. Extends `/devlyn:engines`' no-arg output; no new skill, no
new subcommand. 2-round Codex convergence, no unresolved deltas. Live-verified
on this machine (claude+codex+omp detected, correct role table, correct
recommendation branch when simulated down to 1/0 adapter-valid engines,
fail-closed bogus-pin path unchanged). Also empirically resolved an open
question flagged in iter-0046 about Codex's real skill-loader precedence (see
below) — not this iteration's ask, but cheap to answer while building the
detection logic.

**Trigger**: user direction 2026-07-04 — the harness is heading toward hybrid
multi-engine collaboration (codex, vLLM-hosted Gemma, GLM, ...); users should
be told what's available and what's missing, not just how to pin what they
already know is there.

## Problem (evidence)

`/devlyn:engines`' no-arg output only listed adapters and probed availability
in prose (`config/skills/devlyn:engines/SKILL.md`, old steps 2-3): "List
adapters: every `<name>.md` in the installed `_shared/adapters/`... Probe each
with its availability check." It never told a user what's *missing*, never
covered local-inference backends (ollama/vLLM), and re-described the same
detection work the new doctor needed — a genuine duplication once the new
behavior existed, not just an opportunity.

`bin/devlyn.js`'s `CLI_TARGETS[*].detect()` — the only existing "detection"
logic in the repo — turned out to answer a different question than "is this
CLI installed": all three (codex/omp/pi) check for **project-scoped marker
files** (`AGENTS.md`, `.codex`, `.omp`, `.agents`, `.pi`) in `process.cwd()`,
used to pre-check the installer's multi-select ("is this project already
configured for CLI X"). None do a `command -v` binary check. Reusing
`detect()` as-is for the doctor would have been wrong — a project with a
committed `AGENTS.md` but no codex binary would read as "detected."

## Design (2-round Codex convergence, `model_reasoning_effort=high` then
`medium`, read-only sandbox, `CODEX_MONITORED_ISOLATED=1`)

**Round 1** (107s, high effort): presented the above finding plus a proposed
design (no-arg growth not a subcommand; bash script not Python; static
6-target catalog; `pi` flagged as adapter-less/binary-unverified; recommend-if-
`<2` rule citing iter-0045). Codex converged with 3 named deltas:

1. **Split `installed` into `binary`/`server` for local backends** — a
   reachable server with no local CLI, or a CLI with no running server, are
   both meaningful and collapsing them loses information.
2. **Keep `pi` out of the role-engine table** — show it as an
   informational-only row whose eligibility columns (not row grouping) carry
   the "not routable" contract, so the doctor never implies
   `/devlyn:engines executor pi` is close to working.
3. **Recommendations must only target adapter-valid/routable engines** —
   never suggest installing Ollama/vLLM to "fix" a diversity gap, since
   neither has a `--engine` route yet.

Codex also used a live web search mid-round to verify the Ollama/vLLM install
hints were current official commands rather than trusting training-data
memory — directly satisfying this repo's "no guesswork" rule for the one part
of the design (external install commands) I couldn't verify by running a
local tool.

**Round 2** (12s, medium effort, sign-off only): presented the synthesis —
all 3 deltas adopted, plus one further consolidation (merge what would have
been 3 separate detection tables into one 7-column table, since a compact
single table still satisfies "role table → detection table → recommendation
lines"). Codex's exact close: *"Final named delta: none... a good filename,
and replacing SKILL.md steps 2+3 prose with an invocation of that
Bash-3.2-safe script is the right consolidation."*

### Shipped shape

- **Placement**: no-arg growth, not a `doctor` subcommand. Criterion (both
  rounds): a bare `/devlyn:engines` already promises "status + how to
  choose"; a subcommand is a flag surface with no evidenced second use case
  (CLAUDE.md's own bar — "two real users with genuinely conflicting needs").
- **Script**: new `config/skills/_shared/engine-doctor.sh` — bash, not
  Python, because the work is `command -v` + two short-timeout `curl` probes
  + printing a static table, not JSON/markdown structural parsing (that's
  `spec-verify-check.py`'s job, a different problem shape). Written
  macOS-Bash-3.2-safe (no associative arrays, no `mapfile`) and verified to
  actually run under `/bin/bash` (system default, v3.2.57), not just whatever
  `$SHELL` resolves to in this session.
- **Catalog** (parallel indexed arrays, 6 static rows): `claude`, `codex`,
  `omp` (`cli-engine`, `command -v` probe, `_shared/adapters/<name>.md`
  check), `pi` (`orchestrator-only`, binary column reports `unknown` — no
  verified CLI binary name anywhere in this repo, so no fabricated
  `command -v pi`), `ollama`/`vllm` (`local-backend`, binary **and** server
  columns — server = short-timeout `curl --connect-timeout 1 --max-time 2`
  against `localhost:11434/api/version` / `localhost:8000/v1/models`).
- **`pin_eligible`** = `binary=yes && adapter=yes`. This alone makes `pi`
  (adapter=no) and the local backends (adapter=no, no `--engine` route yet)
  correctly ineligible without any special-casing — the eligibility columns
  carry the contract, exactly as Codex's delta 2 asked.
- **Recommendation**: counts `pin_eligible` rows among the 3 `cli-engine`
  targets. `<2` → print install hints for the missing ones, citing iter-0045
  narrowly ("different model tiers hit different failure-mode blind spots,"
  not "any second model helps") plus the mechanical fact that VERIFY
  pair-judge/risk-probe routes can never fire with fewer than 2. `≥2` →
  one-line diversity confirmation. Read-only; never writes
  `.devlyn/engines.json`, never installs anything, never touches the existing
  `executor`/`pair`/`clear` subcommand fail-closed validation.
- **Install hints** — cited only where independently verified this session,
  not memory: `codex` → `npm install -g @openai/codex` (confirmed via
  `npm ls -g` on this machine), `omp` → `brew install can1357/tap/omp`
  (confirmed via `brew info omp`), `claude` → reuses README.md's existing
  `docs.anthropic.com/en/docs/claude-code` link (already-committed content,
  not new), `ollama` → `curl -fsSL https://ollama.com/install.sh | sh`
  (Codex's live web search this round), `vllm` → points at the vLLM install
  docs page Codex verified live rather than a bare `pip install vllm` (its
  docs are hardware-specific), `pi` → no hint at all, explicit "no verified
  install source" note.

### Subtractive-first accounting

Old steps 2-3's hand-described "list adapters, probe availability" prose is
deleted outright, replaced by one shell-out whose output serves both the
existing role table's "Available engines" column **and** the new detection
table — one script call replaces two hand-described steps instead of adding a
third alongside them. Net SKILL.md diff is still a token increase (below);
citation is the explicit user request for new user-visible behavior (the
detected/recommendation surface), which this repo's subtractive-first clause
accepts as sufficient without a prior-failure-mode citation.

## Significant finding: Codex's skill-loader precedence (iter-0046 open question, resolved)

iter-0046 flagged, but did not resolve, a real ambiguity: a live pipeline run
showed Codex resolving a skill from `~/.agents/skills/` when
`bin/devlyn.js:33-36`'s own comment claims "Codex auto-loads skills from
`~/.codex/skills/` (user-global)." This iteration's detection work made it
cheap to settle empirically, so it did:

1. Placed a marker skill (unique name, valid frontmatter) **only** in
   `~/.codex/skills/zzz-loader-test-codexdir/`. Ran
   `codex exec` (via `codex-monitored.sh -s read-only -c model_reasoning_effort=low`,
   `CODEX_MONITORED_ISOLATED=1`) asking it to name any skill containing the
   marker substring, forbidding shell/file access so the answer could only
   come from already-loaded skill context. It correctly named the marker.
   Its own stderr logged skill-load attempts against **three** directories
   every session: `~/.codex/skills/*`, `~/.agents/skills/*`, and
   `<project-root>/.agents/skills/*`.
2. Moved the marker to **only** `~/.agents/skills/` (removed from
   `~/.codex/skills/`), reran the identical prompt. Codex named it again.
3. Deleted both marker artifacts; machine restored to its pre-test state
   (verified via `ls` showing neither directory contains a `zzz-*` entry).

**Conclusion**: Codex's skill loader is a **union of all three directories**,
scanned every session — not an either/or precedence dispute.
`bin/devlyn.js:33-36`'s comment is not wrong, just incomplete: Codex also
scans both `.agents/skills` locations (home + project), which the installer's
own comments document as the omp/Pi convention. Practical implication, flagged
not fixed here (out of this iteration's scope — the installer is deliberately
untouched): if a machine has both Codex and omp/Pi installed, Codex sees
devlyn skills from **both** its own `~/.codex/skills/` copy (installer writes
here) and the shared `~/.agents/skills/` copy (installer writes here for
omp/Pi) every session. If those two copies ever drift out of sync — exactly
the failure mode iter-0046 hit with a stale `~/.codex/skills/` — Codex's
behavior for the same-named skill becomes last-scan-order-dependent. A
same-content guarantee across the three directories (or an installer check
that flags drift) is a real candidate for a future iteration; not sized or
scoped here.

## Live verification (this machine)

Ran `bash config/skills/_shared/engine-doctor.sh` directly, then the full
skill headlessly via `claude -p --model sonnet --permission-mode
bypassPermissions "/devlyn:engines"` (bypass needed only because headless
`-p` runs deny Bash by default with no prompt path; the script itself is
read-only).

**Real detection** (claude 2.1.201, codex-cli 0.141.0, omp 15.11.0 all
installed; pi/ollama not installed; nothing on `localhost:11434` or
`localhost:8000`):

```
target   kind              binary   server adapter  pin_eligible note
claude   cli-engine        yes      n/a    yes      yes          -
codex    cli-engine        yes      n/a    yes      yes          -
omp      cli-engine        yes      n/a    yes      yes          -
pi       orchestrator-only unknown  n/a    no       no           informational only; not a routable role engine — no verified CLI binary or adapter
ollama   local-backend     no       no     no       no           no --engine route yet (tracked: iter-0051); curl -fsSL https://ollama.com/install.sh | sh
vllm     local-backend     no       no     no       no           no --engine route yet (tracked: iter-0051); see https://docs.vllm.ai/en/latest/getting_started/installation.html

Pair-judge diversity: 3 adapter-valid engines available.
```

The headless `/devlyn:engines` run reproduced this exactly, plus the correct
role table (`claude ✓ codex ✓ omp ✓`) and usage lines.

**Recommendation-branch tests** (PATH stripped to simulate fewer installed
engines, no binaries touched — `env PATH=... bash engine-doctor.sh`):

- PATH limited to `/opt/homebrew/bin` (omp only): `pin_eligible_count=1` →
  correct recommendation text naming `claude` and `codex` with their install
  hints.
- PATH limited to core system dirs (none): `pin_eligible_count=0` → same
  recommendation shape naming all 3.

**Fail-closed regression** (must be unaffected by this change — confirmed via
`git diff` that the `## Subcommands` section is byte-identical, then a live
check): `claude -p --model sonnet --permission-mode bypassPermissions
"/devlyn:engines executor totally-bogus-engine-name"` → exit 1, refused with
"has no `_shared/adapters/<name>.md`," listed valid names
(`claude`, `codex`, `omp`), and confirmed no `.devlyn/engines.json` was
written.

## Token delta (`scripts/skill-token-gauge.py`, tok≈chars/4)

| File | Before | After | Δ |
|---|---|---|---|
| `devlyn:engines/SKILL.md` | 539 | 800 | +261 |
| Grand total | 138929 | 139190 | +261 |

`engine-doctor.sh` itself does not count toward cold-start cost — it's
invoked, not loaded into context; its output is dynamic per-session text, not
skill-body prose. Pure addition on the SKILL.md side, justified per the
repo's own subtractive-first exception: explicit user request for new
user-visible behavior is a sufficient citation, and the old prose it replaced
(steps 2-3) is deleted outright rather than left alongside the new behavior.

## Principles check

- **Pre-flight 0 / user direction**: yes — explicit trigger (harness heading
  toward hybrid multi-engine collaboration), not a score-chasing addition.
- **#1 No overengineering**: no new skill, no new subcommand (both rounds
  converged on this); one script, one static catalog, one call site.
- **#2 No guesswork**: `bin/devlyn.js` detect()'s real purpose was verified
  by reading the code, not assumed; `pi`'s binary name was left `unknown`
  rather than fabricated; install hints for codex/omp were confirmed via
  `npm ls -g`/`brew info` on this machine; ollama/vllm hints were Codex's
  live web-search verification, not training-data recall; the loader
  precedence question was closed with a reversible, cleaned-up empirical
  test, not inference from old transcripts.
- **#3 No workaround**: doctor never auto-installs, auto-repins, or converts
  a missing-engine state into a silent default — matches
  `_shared/engine-preflight.md`'s existing fail-closed contract, live-verified
  unchanged.
- **#4 Worldclass / #7 Production ready**: bogus-pin fail-closed path
  live-tested post-change, not just code-diffed; local-backend probes are
  timeout-bounded (`--connect-timeout 1 --max-time 2`) so a hung server can
  never stall the skill.
- **#5 Best practice**: reused the existing `DEVLYN_SKILL_DIR`/
  `DEVLYN_SHARED_DIR` resolution boilerplate verbatim from
  `devlyn:resolve`/`devlyn:ideate` rather than inventing new plumbing.
- **Goal-locked**: did not touch `bin/devlyn.js`, the installer, or
  `_shared/engine-preflight.md`'s validation logic — all named as
  read-only-unless-essential in the brief and left alone; the skill-drift
  finding (Codex's 3-dir union) is recorded as a flagged follow-up, not
  silently fixed inside this iteration.

## Artifacts

- New: `config/skills/_shared/engine-doctor.sh` (+ byte-identical mirrors in
  `.agents/skills/_shared/` and `.claude/skills/_shared/`).
- Changed: `config/skills/devlyn:engines/SKILL.md` (+ same mirrors).
- Design rounds: this file (Codex transcripts summarized above; full session
  output not separately archived — reproducible via the same
  `codex-monitored.sh -s read-only -c model_reasoning_effort=high|medium
  CODEX_MONITORED_ISOLATED=1` invocation shape documented in
  `_shared/codex-config.md`).
- `bash scripts/lint-skills.sh`: all checks pass, including
  Check 10a1 (shared helper paths resolve from the invoked skill — no
  project-relative `.claude/skills/_shared` paths).
