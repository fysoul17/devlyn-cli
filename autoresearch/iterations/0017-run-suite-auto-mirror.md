# iter-0017 — run-suite.sh auto-mirror config/skills/ → .claude/skills/

**Status**: SHIPPED 2026-04-27.
**Risk**: low (single-file additive change, falsified locally, no model invocations consumed).
**Cost**: ~5 min, $0.

## Pain

`autoresearch/HANDOFF.md` Critical-gotcha block warns: variant arm reads
`$REPO_ROOT/.claude/skills/`, but iteration commits land in `config/skills/`.
After every checkout/revert that touches a managed skill, the suite required a
manual `node bin/devlyn.js -y` or surgical `cp` to sync the trees. Forgetting
silently runs the benchmark against stale skills — "passed lint, ran clean,
results meaningless." Long-standing iter-0007 candidate, renumbered to iter-0017
post iter-0014.

## Hypothesis

If `run-suite.sh` mirrors `config/skills/` → `.claude/skills/` at the top of
every invocation (with `cleanManagedSkillDirs` semantics: replace each
managed-skill directory wholesale, leave user-installed skills untouched, skip
the four `UNSHIPPED_SKILL_DIRS` workspaces), the sync gap closes without any
behavior change to the harness itself.

## Mechanism (decided after Codex GPT-5.5 R0 review)

Three candidates considered:

- **M1** — shell out to `node bin/devlyn.js -y`. Single source of truth, but
  the installer also writes `CLAUDE.md` to `process.cwd()`, mutates project
  `.gitignore`, project `.claude/settings.json` (permissions + `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`),
  global `~/.claude/settings.json` (`CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING`,
  `ENABLE_PROMPT_CACHING_1H`), runs `cleanupDeprecated`, and triggers
  `installAgentsForAllDetected` for every detected non-Claude CLI in cwd. Far
  too broad for a benchmark prelude. Rejected.
- **M2** — inline shell mirror in `run-suite.sh`: per-managed-skill `rm -rf` +
  `cp -R` with a hardcoded `UNSHIPPED_SKILL_DIRS` list. Predictable, no global
  state mutation. Bounded duplication risk (4 entries; comment points at
  `bin/devlyn.js:299`).
- **M3** — `rsync --delete --exclude=...`. Codex flagged macOS rsync version
  variance and `--delete` semantics fiddle. Rejected.

**Picked**: M2.

Codex's specific calls beyond M2 selection:
1. **Unconditional**, not gated by mtime — checkout/revert/clock-skew defeats
   timestamp comparisons.
2. **Run before test-repo `npm install` and any arm**.
3. **Skip only `--judge-only`** (no model invocations, no skill changes
   possible). **Run in `--dry-run`** so suite-setup verification covers the
   mirror path.
4. **Atomic per-skill swap**: `cp -R` to `.claude/skills/.<name>.staging`,
   then `rm -rf .claude/skills/<name>` and `mv` the staging dir into place.
   Mid-mirror Ctrl-C leaves only hidden staging dirs (cleaned by next run's
   `rm -rf "$staging"`); the live skill is never half-populated for more than
   a single `mv` call.
5. **Print a one-line stamp** for log auditability:
   `[suite] mirrored N committed skill(s): config/skills/ -> .claude/skills/`
6. **Reject a shared exclusion file under `config/skills/`** — the file would
   itself get copied. Inline + comment beats out-of-tree metadata for 4 stable
   strings.

## Diff

Single edit: `benchmark/auto-resolve/scripts/run-suite.sh`, +33 lines, no other
files changed.

Insertion point: between the run banner (echoes RUN_ID, mode) and the prereq
checks (verify `claude` / `codex` / `python3` on PATH). This places the mirror
output adjacent to the banner block in suite logs and runs before any work that
could read stale skills.

## Falsification gate

Local verification, no model spend:

1. `diff -rq config/skills/ .claude/skills/` silent before.
2. Inject marker `<!-- iter0017-canary-... -->` into
   `config/skills/devlyn:auto-resolve/SKILL.md`.
3. Inject drift `<!-- DRIFT NOT FROM CONFIG -->` into
   `.claude/skills/devlyn:auto-resolve/SKILL.md` (simulates pre-iter-0017
   forgotten-mirror state).
4. `bash benchmark/auto-resolve/scripts/run-suite.sh --dry-run F1` →
   `[suite] mirrored 26 committed skill(s)` printed; no model invoked.
5. Marker propagated to `.claude` (count=1 ✓).
6. Drift line absent in `.claude` (count=0 ✓).
7. UNSHIPPED workspace dirs absent in `.claude/skills/` ✓.
8. Fake user-installed skill (`.claude/skills/fake-user-skill/`) created
   pre-mirror, mirror executed, fake skill content + path preserved ✓.
9. Post-state diff silent ✓.
10. `bash scripts/lint-skills.sh` → all 10 checks pass ✓.

## Decisions / lessons added

- **Installer ≠ mirror.** Reusing `bin/devlyn.js -y` for "just sync skills"
  would have entangled benchmark setup with project config, gitignore, CLAUDE.md
  copy, agent-pack installation, and global settings tweaks. The benchmark
  needs only the skills-tree subset; M2 isolates that subset.
- **Atomicity from staging + mv.** A hidden `.<name>.staging` per skill,
  followed by `rm + mv`, gives a swap window measured in milliseconds and an
  abort residue (lone `.staging` dir) that the next run idempotently clears.
- **Inline UNSHIPPED list** is acceptable here because the list is small (4
  entries), each entry matches the package.json `files[]` exclusion list, and
  the in-code comment points at `bin/devlyn.js:299` so a future
  workspace addition will surface in both files together at review time.
- **iter-0016 (full-suite verification) is now safer to run** — the auto-mirror
  removes one of the two mechanisms that produced silent stale-skill runs.
  (The other — manual `cp` overwriting `.claude/skills/` mid-session — is now
  also self-healed at next `run-suite.sh` invocation.)

## Files touched

- `benchmark/auto-resolve/scripts/run-suite.sh` (+33 lines)
- `autoresearch/iterations/0017-run-suite-auto-mirror.md` (new)
- `autoresearch/HANDOFF.md` (update)

## Codex collaboration

R0 (model `gpt-5.5`, reasoning `xhigh`, 84s, 41,071 tokens). Verdict: M2;
unconditional execution; skip only `--judge-only`; staging-dir swap for
atomicity; inline list. All recommendations adopted verbatim — no pushback to
surface.
