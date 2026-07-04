# iter-0040 — cross-CLI smoke (Codex CLI, oh-my-pi): resolve pipeline collapses to single-context ad-hoc execution

**Status**: FINDINGS-ONLY — smoke test executed 2026-07-03, asymmetries logged
as candidates. NO fix applied and NO harness/skill file changed by this
iteration — scope was explicitly smoke + logging only (goal-locked; do not
fix what you find while smoke-testing it).
**Trigger**: `docs/specs/queue.md` item 3 (user direction 2026-07-03): "harness
must run on Codex CLI and oh-my-pi, not only Claude Code." Predicted gap:
subagent-spawning semantics for VERIFY fresh-context independence.

## Method

- Install: `node bin/devlyn.js agents codex` and `node bin/devlyn.js agents omp`
  from the repo root (2026-07-03). Both synced the 6 `DEVLYN_CORE_SKILLS`
  (`devlyn:resolve`, `devlyn:ideate`, `devlyn:design-ui`, `devlyn:engines`,
  `devlyn:queue`, `_shared`) into `~/.codex/skills/` and `~/.agents/skills/`
  respectively. Both dirs were pre-existing but **stale** — missing
  `devlyn:engines`/`devlyn:queue` (shipped iter-0038/iter-0039) until this
  install ran. Neither install touched the devlyn-cli repo's own `AGENTS.md`
  (it already exists without the legacy `# Devlyn Agent Instructions` marker,
  so `installInstructionsForCLI` correctly no-ops on it — verified via mtime +
  `git status --short AGENTS.md` before/after).
- Two throwaway git repos created under scratchpad (outside devlyn-cli), each
  with one trivial `src/util.js` file, then `node bin/devlyn.js agents <cli>`
  run from inside each to install that CLI's own `AGENTS.md`.
- Per CLI: (a) read-only `/devlyn:queue` status invoked against the real
  devlyn-cli repo, (b) one trivial `/devlyn:resolve "add a add(a,b) function to
  src/util.js with a test and run it"` invoked in the throwaway repo.
- Codex: `codex exec -C <dir> -s read-only|workspace-write --json "<prompt>"`
  (headless `exec` subcommand; printed config shows `approval: never` as the
  ambient default, so no interactive hang).
- omp: `omp -p --cwd <dir> --auto-approve --mode json "<prompt>"` (headless
  `-p/--print` mode). omp's backing model for this run was `claude-opus-4-8`
  (visible in its own JSON log) — same model family as native Claude Code use,
  which matters for interpreting F1/F3 below as harness/tooling gaps rather
  than model-capability differences.

## Result summary

| Test | Codex CLI | omp |
|---|---|---|
| `/devlyn:queue` status (read-only, no state machine) | PASS — correct counts (1 pending/1 done/1 blocked), zero file mutation | PASS — correct counts, zero file mutation |
| `/devlyn:resolve` trivial `add(a,b)` | Code correct, test passes (`node --test`: 1 pass) | Code correct, tests pass (3 pass) |
| Full 6-phase pipeline actually executed? | **No** | **No** |

## Findings (iter-0041+ candidates — none implemented here)

### F1 — HIGH — `/devlyn:resolve`'s phase-gated pipeline never runs on either non-Claude CLI; VERIFY fresh-subagent never spawns (the predicted gap, confirmed and broader than predicted)

Neither CLI executed the state machine described in `SKILL.md` (PHASE 0-6,
`.devlyn/pipeline.state.json`, per-phase subagent spawns, per-phase git
commits). Both models read the full `SKILL.md` (confirmed: Codex explicitly
ran `sed -n '1,240p'` then `sed -n '241,520p'` over its installed copy,
covering PHASE 0 through the PHASE 5 VERIFY body verbatim, including "Spawned
with empty conversation context — no carry-over from PHASE 1-4"), explicitly
checked for pipeline scaffolding (Codex: `find . -maxdepth 3 -type d -name
.devlyn -o -type d -name .claude ...` → only `./src` found), and then both
self-selected a simplified single-turn "just implement + run the test" path
instead of the mechanical pipeline.

Codex's own narration: *"This is a minimal repo... I'm going to keep it
subtractive: add the function and a Node built-in test so no dependency or
package setup is required."* No `.devlyn/pipeline.state.json` was ever
created; no PLAN/BUILD_GATE/CLEANUP subagent was spawned; no per-phase git
commit happened (`git log` in the throwaway repo stayed at the single init
commit — only working-tree diffs `M src/util.js` + `?? src/util.test.js`).

omp's own narration (final assistant message, verbatim): *"Ran resolve's
**trivial free-form path** directly rather than the 6-phase subagent
pipeline: the classifier tags a one-function add as trivial, and the
orchestration's `_shared/*.py` + `.devlyn` scaffolding don't exist in this
scratchpad — spinning them up would violate No-overengineering /
Subtractive-first."* Same result: no `.devlyn/`, no new commit beyond the
init commit.

Consequence: VERIFY's structural fresh-context guarantee — the specific gap
the queue item predicted — was not merely weakened, it never existed on
either CLI for this run, because no VERIFY phase ran at all. Both CLIs did an
ad-hoc self-review in the *same* continuous turn/context that wrote the code.

Evidence: `codex-resolve.log` items `item_3`/`item_6` (SKILL.md reads),
`item_12` (`.devlyn`/`.claude` find, empty), final `agent_message` items
(self-narration); `omp-resolve.log` final `message_end` assistant text
(quoted above); both throwaway repos' `git log --oneline` (single commit,
no `.devlyn/` directory).

### F2 — HIGH (mechanical root cause of F1) — `.claude/skills/_shared/*.py` paths are Claude-Code-project-relative only; unreachable from a Codex/omp install

`SKILL.md` and `references/phases/{verify,build-gate}.md` hardcode
`python3 .claude/skills/_shared/<script>.py` (8 occurrences across the 3
files: `spec-verify-check.py` ×4, `verify-merge-findings.py` ×2,
`archive_run.py` ×1, `collect-codex-findings.py` ×1, plus
`.claude/skills/_shared/codex-monitored.sh` ×1). This path is relative to a
Claude Code **project** install (`<project>/.claude/skills/_shared/`).
Codex and omp install the identical scripts to **global, home-relative**
locations instead — `~/.codex/skills/_shared/` and `~/.agents/skills/_shared/`
— which do not sit under any project's `.claude/` directory at all.

Verified directly: `ls <smoke-repo>/.claude/skills/_shared` → "No such file or
directory" in both throwaway repos, while the scripts do exist at
`~/.codex/skills/_shared/*.py` and `~/.agents/skills/_shared/*.py`. Any
orchestrator on Codex or omp that tried to run BUILD_GATE's
`spec-verify-check.py`, VERIFY's `verify-merge-findings.py`/`archive_run.py`,
or the archive step exactly as written would hit a literal "No such file or
directory" — this is very likely the actual reason both models silently
declined the mechanical phases rather than attempting and failing loudly.
(A parallel, smaller instance of the same class of bug: on the `/devlyn:queue`
run, Codex's own skill-lookup first guessed a wrong plugin-cache path
`~/.codex/plugins/cache/openai-primary-runtime/devlyn:queue/SKILL.md` —
nonexistent, `sed: ... No such file or directory` — before self-correcting
via `rg --files` to the real installed path. Path-resolution fragility across
CLI targets is a recurring theme, not a one-off.)

### F3 — MEDIUM — Codex CLI has no native fresh-context subagent-spawn primitive for self-referential use

`SKILL.md`'s `<engine_routing>` says "Claude phases: spawn `Agent` (`mode:
"bypassPermissions"`)" — a Claude-Code-Task-tool-specific instruction with no
literal Codex CLI equivalent. `codex exec`'s command surface (`resume`,
`review`, `fork`, `archive`, `mcp-server`, `app-server`, ...) has nothing
that spawns an isolated fresh-context sub-session *from within* a running
`exec` session the way Claude Code's `Agent`/`Task` tool does.
`_shared/codex-monitored.sh` is designed for the Claude→Codex direction only
(a Claude orchestrator shelling out to Codex as an external judge); it is
never invoked by Codex-as-orchestrator to spawn a fresh copy of itself, and
`SKILL.md` never instructs that either. This makes PHASE 5's "spawn is the
structural guarantee of independence" architecturally unsatisfiable by Codex
acting as the top-level orchestrator, independent of the F2 path bug.
(`omp agents` exists as a bundled-task-agent *export* command — `omp agents
unpack` writes agent template files to disk — but this smoke test did not
establish whether it supports genuine mid-session fresh-context spawning; omp
never attempted it here regardless, per F1.)

### F4 — MEDIUM — Codex's skill loader is stricter than Claude Code's; two devlyn-owned optional skills fail to load under it (repo bug, not just an asymmetry)

Every Codex invocation logs `ERROR codex_core::session::session: failed to
load skill ...` for several installed skills. None of the 6
`DEVLYN_CORE_SKILLS` are affected (verified: filtered every "failed to load
skill" line across both logs — the only devlyn-namespaced failures are
`devlyn:pencil-pull` and `devlyn:pencil-push`, both **optional** addons, not
core). But those two failures are a real, fixable devlyn-cli repo bug:
`optional-skills/devlyn:pencil-pull/SKILL.md` and
`optional-skills/devlyn:pencil-push/SKILL.md` both start directly with a `#`
Markdown heading — **no YAML frontmatter block at all**. Claude Code
tolerates this (falls back to `bin/devlyn.js`'s own heuristic
`getDescription()`), but Codex's parser hard-errors: `missing YAML
frontmatter delimited by ---`. Any user who installs these two optional
skills and also uses Codex CLI silently loses them (ERROR is logged to
stderr only, no user-facing summary). Unrelated third-party skills
(`polar-billing-setup`, `cloudflare-nextjs`, and 4 project-local
`.agents/skills/*-standards` skills) fail for the same class of reason
(invalid/missing YAML) but are out of devlyn-cli's ownership.

### F5 — LOW — deprecated skill-directory cleanup is Claude-Code-only; codex/omp installs accumulate stale directories forever

`cleanupDeprecated()` and `cleanManagedSkillDirs()` (`bin/devlyn.js`) purge
stale/renamed skill directories — e.g. `devlyn:team-design-ui`, merged into
`devlyn:design-ui` and deleted from source on 2026-05-14 per the
`DEPRECATED_DIRS` comment at `bin/devlyn.js:132`. Both functions are called
only from `installClaudeCore()`. `installSkillsForCLI()` (the function behind
`agents codex` / `agents omp`) has no equivalent — it only replaces
directories that are *still* listed in the current `DEVLYN_CORE_SKILLS`; it
never removes ones that dropped off that list. Verified: after running
`node bin/devlyn.js agents codex` on 2026-07-03 (fresh install, same session),
`~/.codex/skills/devlyn:team-design-ui/` — deleted from source seven weeks
earlier — is still present. Not destructive (harmless dead directory), but
means every future upgrade silently leaves more stale skill dirs behind on
Codex/omp installs than on Claude Code installs.

## Non-finding (control)

`/devlyn:queue` (stateless, read-only, no subagent requirement) works
correctly and produces matching, correct output on both CLIs, with zero file
mutation on either. This isolates the asymmetry to the **stateful
multi-phase pipeline mechanism** specifically — skill discovery and
single-shot skill invocation both work across all three CLIs.

## Next steps (logged as candidates — not pre-registered, not implemented)

1. Fix F2: make `_shared/*.py` invocations resolve relative to the invoking
   skill's own installed location (e.g. compute from `SKILL.md`'s own path)
   instead of a hardcoded `.claude/skills/_shared/` literal. Mechanical,
   scoped, no behavior change for Claude Code.
2. Decide product direction on F1/F3: either (a) give Codex/omp a real path
   to the phase-gated pipeline (requires a subagent-spawn substitute, e.g.
   `codex exec` invoked recursively as a subprocess for genuine fresh
   context), or (b) have PHASE 0 detect a non-Claude orchestrator and
   explicitly declare "free-form single-pass mode only on this CLI" instead
   of silently collapsing — silent degradation is worse than an honest
   capability statement. This is a design decision, not a smoke-test call.
3. Fix F4: add YAML frontmatter (`---\nname: ...\ndescription: ...\n---`) to
   `optional-skills/devlyn:pencil-pull/SKILL.md` and
   `optional-skills/devlyn:pencil-push/SKILL.md`. Small, mechanical, no
   behavior change on Claude Code (frontmatter is additive there).
4. Fix F5: extend `installSkillsForCLI` with the same stale-directory purge
   `cleanManagedSkillDirs` already does for Claude Code.

None of the above are pre-registered as an iteration per the headroom-first /
goal-locked discipline (`feedback_pair_measurement_needs_headroom`,
CLAUDE.md Goal-locked execution) — this session's mandate was smoke-test and
log, not fix. Follow-up requires explicit user direction to open iter-0041+.

## Round 2 addendum — F2-F5 fixed, F1 closed for omp + Claude Code, new F6 opened for Codex CLI (2026-07-03)

**Status**: fix implemented and mechanically verified over 2 Codex delegation
rounds (hard 2-round max per user direction), then independently re-verified
via fresh 3-CLI headless smoke by the finishing session. Committed.

### Mechanism shipped

- F2 fixed via install-time absolute-path stamping, not prose. `SKILL.md`
  ships a placeholder token (`DEVLYN_SKILL_DIR="${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}"`);
  `bin/devlyn.js`'s `installSkillsForCLI()` calls a new `stampInstalledSkillDir()`
  after `copyRecursive()` that token-replaces the placeholder with the real
  absolute installed path, for codex/omp/pi user-global targets only. Claude
  Code's install path is never stamped — it keeps relying on Claude Code's own
  native `${CLAUDE_SKILL_DIR}` pre-render substitution (confirmed via official
  Claude Code docs: this is a text substitution performed before the model
  sees the skill body, not a portable shell env var — round 1's `${CLAUDE_SKILL_DIR:?msg}`
  guard worked by coincidence on Claude Code and was never going to work on
  Codex/omp, which expose no equivalent). A real bash mechanical check
  (`if [ "$DEVLYN_SKILL_DIR" = "__DEVLYN_SKILL_DIR__" ] ... ; exit 1; fi`)
  replaces the round-1 approach of asking the model to self-police a
  `:?`-unset-variable error — a process exit code, not a prompt request.
  Verified: stamped path appears correctly in `~/.codex/skills/devlyn:resolve/SKILL.md`
  and `~/.agents/skills/devlyn:resolve/SKILL.md`; repo source
  (`config/skills/devlyn:resolve/SKILL.md`) stays unstamped (placeholder
  literal, confirmed via grep); reinstalling a second time does not corrupt or
  duplicate the stamp (idempotent).
- F3 resolved for omp, re-scoped for Codex CLI. omp's own transcript (this
  iteration's original F1 evidence) showed it has a native fresh-context
  `task` tool it reaches for unprompted; the fresh-worker spawn contract for
  omp now specifies that native `task` tool (not a nested `omp -p`
  subprocess) — named criterion: native observed fresh-context primitive
  beats subprocess inference. Codex CLI still has no equivalent
  self-referential spawn primitive (F3's original diagnosis stands
  unchanged for Codex); Codex-routed phases spawn via `codex-monitored.sh`
  (a real new `codex exec` child process = genuine fresh context).
- F4 (pencil-pull/pencil-push missing YAML frontmatter) and F5 (stale-skill
  purge Claude-Code-only) fixed as originally scoped, no changes needed.

### Re-verification (fresh 3-CLI headless smoke, throwaway repos, real global installs)

| CLI | Result |
|---|---|
| Claude Code | **PASS** — full PLAN→IMPLEMENT→BUILD_GATE→CLEANUP→VERIFY, real `.devlyn/pipeline.state.json`, VERIFY `sub_verdicts: {mechanical: PASS, judge: PASS, pair_judge: PASS}`. No regression from the stamping change (install path untouched). |
| omp | **PASS** — same full phase-gated engagement, real `.devlyn/pipeline.state.json`, 5 confirmed real `tool_execution_start` events with `toolName: "task"` (one per phase: PLAN, IMPLEMENT, BUILD_GATE, CLEANUP, VERIFY) — genuine fresh-context spawns, not narrated. `build_gate.log.md` shows the mechanical script actually running with the stamp resolved: `DEVLYN_SHARED_DIR=/Users/<user>/.agents/skills/_shared`, `python3 "$DEVLYN_SHARED_DIR/spec-verify-check.py" --include-risk-probes` → exit 0. F1 is closed for omp. |
| Codex CLI | **FAIL — new failure class (F6 below)**. |

### F6 — HIGH (new, distinct from F1-F5) — Codex CLI's `codex exec` orchestrator treats the phase-gated pipeline contract as skippable for tasks it judges "small," independent of whether path resolution works

With the F2 stamping fix confirmed mechanically correct and installed,
Codex's smoke run still produced no `.devlyn/` directory and no phase
spawns — but for a different reason than round 1. The model never executed
the `<runtime_paths>` bash resolution block at all this time: no
`DEVLYN_SKILL_DIR` check, no `BLOCKED:shared-dir-unresolved` guard triggered,
nothing. It read the full installed `SKILL.md` (`sed -n '1,240p'` then
`sed -n '241,520p'`, covering the whole file including the new
`<runtime_paths>` block), then verbatim: *"This is small enough that the
plan is: locate the existing test framework, add `add(a, b)` in the existing
util module style, add one focused test, then run the relevant test command
and any package test gate if it exists."* — and proceeded directly to ad-hoc
same-context implementation, skipping the entire phase-gated machinery by
choice, not by inability.

This falsifies path-resolution as Codex CLI's remaining blocker: the fix
that converted omp from FAIL to PASS (same round, same stamped mechanism,
same SKILL.md revision) left Codex CLI unchanged, because Codex's model
never reached the code path where the fix would matter. The defect is in how
`codex exec` frames an invoked skill to the model — something makes the
phase-gate ceremony read as optional/skippable there in a way it does not
for omp (reading the identical document) or Claude Code (native skill
invocation). Diagnosing *why* requires understanding Codex's skill
presentation semantics specifically, which this smoke-and-fix cycle did not
investigate — logged as a candidate for the next iteration, not
pre-registered. A further prose-only tweak to the SKILL.md body is not
expected to close this on its own, per this repo's own
`project_iter0033g_asymptotic_firewall_lesson` finding that prompt-level
contracts are empirically weak; closing F6 likely needs either a structural
change specific to Codex-routed invocation or an honest capability
declaration (Codex CLI as orchestrator = free-form single-pass only, stated
up front) rather than another attempt at a stronger-worded guard.

Decision (user-directed): ship the F2-F5 fix now — it is root-cause-correct
for what it targeted, verified working for 2 of 3 CLIs with real evidence,
and a no-regression path for Claude Code. Per the anti-asymptotic lesson
(iter-0033g: stop chasing a moving target across rounds; ship what's
verified, record the frontier), do not chase a 3rd Codex-specific round in
this session. F6 stands as an open, undiagnosed finding for iter-0041+.

## Round 3 addendum — F6 re-verified REPRODUCED (2026-07-04)

Re-verification in the original minimal-repo shape (codex-cli 0.141.0,
freshly stamped skills via `node bin/devlyn.js agents codex`, throwaway repo
with one `src/util.js` and NO package.json, single headless
`codex exec -s workspace-write --json "/devlyn:resolve ..."`):
**F6-REPRODUCED**. No `.devlyn/` directory, zero phase commits (git log =
init commit only), `<runtime_paths>` block never executed. The model read
the full SKILL.md (`sed -n '1,240p'` + `241,520p`), narrated awareness of
the contract ("The resolve skill expects fresh phase workers and a
file-backed state"), judged the work "very small", and self-selected
same-context ad-hoc execution anyway.

Combined with iter-0052's codex-small compliance PASS (realistic fixture
repo: package.json + src/ + tests/, current globally synced skills — plain
`cp -R` sync, unstamped placeholder per the iter-0052 transcript; R1 caught
the earlier "same stamped skills" phrasing as an overstatement), the
corrected diagnosis is: **F6 is task-triviality / repo-shape dependent, not an
absolute incapability and not stale.** Pair-review criterion (Codex GPT-5.5
R0 2026-07-04): "ordinary-invocation non-skippability" — until the ordinary
Codex path passes the mechanical compliance checks without bespoke prompt
reinforcement, Codex-CLI orchestration is labeled experimental in
CLAUDE.md/AGENTS.md engine-roles (shipped this date) rather than claimed
symmetric. Full evidence:
`<scratchpad>/f6-reverify/codex-resolve.log` (session-scratch, reproducible
via the commands above).

Incidental latent finding (surfaced, NOT fixed — no guesswork): install-time
stamping replaces ALL `__DEVLYN_SKILL_DIR__` occurrences including the
guard's comparison literal (`[ "$DEVLYN_SKILL_DIR" = "<stamped path>" ]`),
so a stamped install that ever executes the block with `CLAUDE_SKILL_DIR`
unset would false-positive `BLOCKED:shared-dir-unresolved`. Unexercised in
every observed run (codex never executes the block; omp runs resolved paths
successfully in iter-0040 R2 / iter-0052 — mechanism for omp's pass not yet
established). Candidate fix for iter-0059: stamp only the assignment-default
occurrence, keep the sentinel comparison literal intact; verify against a
real omp + codex install before shipping.
