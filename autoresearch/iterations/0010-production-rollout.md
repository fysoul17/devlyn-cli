# 0010 — Production rollout (wrapper-form to standalone skills)

**Status**: SHIPPED
**Started**: 2026-04-27
**Decided**: 2026-04-27 (same-day, no benchmark — surgical text rollout with static gate + canary)

## Hypothesis

iter-0009 SHIPPED the wrapper + PATH shim and proved the mechanism works on auto-resolve (F2 BUILD ran 399.9s through the wrapper without watchdog kill; F6 +60-point recovery from iter-0008 collapse). But the user-facing chain `/devlyn:ideate → /devlyn:auto-resolve → /devlyn:preflight` includes two long Codex calls outside auto-resolve — ideate CHALLENGE (~10 min critic pass on `--engine auto`) and preflight CODE AUDIT (~5–10 min auditor pass on `--engine auto`) — both of which still emit raw `codex exec` from inline SKILL.md examples. Same byte-watchdog starvation profile as iter-0008.

iter-0010 closes that production gap by rewriting every inline `codex exec` invocation in the four standalone Codex-using skills (ideate, preflight, team-resolve, team-review) to wrapper-form. Plus phrase-level priming text Codex Round 1 caught (`reads stdout of each \`codex exec\` invocation` etc.). Plus a doc bug Codex Round 1 caught (canonical said heartbeat-on-stdout, wrapper writes stderr).

**Out of scope** (intentionally deferred — see Codex Round 1 ship-blocker below): shipping `scripts/codex-shim/codex` to user installs.

## Mechanism

Why-chain (extending iter-0009 at #43):

44. Why does the chain still risk iter-0008 starvation despite iter-0009? → iter-0009 only hardened auto-resolve. ideate/preflight/team-* SKILL.md files still contained raw `codex exec ... -C ... -s read-only ...` invocation examples; orchestrators reading those skills would emit raw shape on first attempt. The wrapper doesn't help text the orchestrator never sees; PATH shim is benchmark-only.
45. Why is the textual rewrite sufficient (no new mechanism)? → iter-0009 already proved that when the SKILL.md says wrapper-form, the orchestrator emits wrapper-form (F2 BUILD ran 399.9s wrapper-shaped). The orchestrator follows skill-prompt invocation patterns when the text is clean. iter-0010 makes every Codex-using skill prompt clean.
46. Why is a static lint check the right gate, not a benchmark run? → iter-0009 proved the mechanism. iter-0010 changes only text (no mechanism change), and lint Check 10 verifies the text is clean across all 4 skills. Running F4 again would re-test what's already proven on F2/F6. Skip.
47. Why drop shim-shipping to user installs? → Codex Round 1 caught: the shim hard-fails exit 127 without `CODEX_REAL_BIN` + `CODEX_MONITORED_PATH` envs (shim lines 59–63, 68–72). The benchmark wires those via `run-fixture.sh:90–118` using a project-scoped `.claude/settings.json env.PATH` override (necessary because zsh shell-snapshot resets parent PATH inside Bash dispatches). Production user installs have none of that scaffolding; shipping the shim without it would brick `codex` invocations entirely. Wrapper-form text in skill prompts is the primary defense post-iter-0010 — shim was the secondary safety net needed only when raw `codex exec` text could leak through (which iter-0010 lint Check 10 prevents).
48. Root: orchestrator-codex-shape correctness now depends on no skill prompt containing a raw `codex exec` invocation pattern; lint enforces this statically; shim deferred to a future iteration once activation path is solved.

## Predicted change

iter-0010 has no benchmark gate (mechanism unchanged from iter-0009). Predictions are static-only:

- **Lint Check 10 PASSES** — zero raw `codex exec` invocation patterns anywhere in `config/skills/**` outside the canonical `_shared/codex-config.md` and `_shared/codex-monitored.sh` itself. Pattern catches single-line (`codex exec -`), resume form (`codex exec resume `), and multi-line continuation (`codex exec \` at EOL).
- **Mirror parity Check 6 PASSES** — the 3 newly-added files (codex-critic-template.md, team-resolve/SKILL.md, team-review/SKILL.md) sync to `.claude/skills/` cleanly.
- **Wrapper canary PASSES** — pipe-stdout invocation exits 64 with the iter-0009 R2 clear message; file-stdout invocation reaches `[codex-monitored] start` line on stderr and codex spawns successfully.
- **No regression in auto-resolve** — auto-resolve files unchanged; F2/F6/F4 expected behavior unchanged from iter-0009.

## Diff plan

Seven edits — pure text rewrites + lint extension. No new files, no new abstractions.

1. **`config/skills/devlyn:ideate/SKILL.md`** (EDIT, 2 sites). Line 245 (CHALLENGE Codex critic, read-only) and line 300 (`--engine codex` full pipeline, workspace-write + `resume --last`) rewritten to wrapper-form. The wrapper passes args verbatim, so `bash codex-monitored.sh resume --last` produces `codex exec resume --last` — semantics unchanged (Codex Round 2 verified).
2. **`config/skills/devlyn:ideate/references/codex-critic-template.md`** (EDIT, 1 site). Line 5 template description rewritten to wrapper-form.
3. **`config/skills/devlyn:preflight/SKILL.md`** (EDIT, 1 site). Line 117 CODE AUDIT auditor invocation rewritten to wrapper-form.
4. **`config/skills/devlyn:team-resolve/SKILL.md`** (EDIT, 4 sites). Code-block invocation (line 140), and 3 phrase-priming descriptions (lines 147, 151, 157 — including the two Codex Round 1 caught at line 147 plus two more I purged for consistency).
5. **`config/skills/devlyn:team-review/SKILL.md`** (EDIT, 4 sites). Same pattern as team-resolve.
6. **`config/skills/_shared/codex-config.md`** (EDIT, 1 site). Line 54 doc bug fix: heartbeat-on-stdout → heartbeat-on-stderr (Codex Round 1 caught — wrapper writes stderr at line 92, doc said stdout).
7. **`scripts/lint-skills.sh`** (EDIT). Mirror parity Check 6 extended to include the 3 newly-edited files. New Check 10: forbid raw `codex exec` invocation pattern in skill prompts. Pattern (post Codex Round 2 multiline fix): `codex exec (-|resume[[:space:]]|\\$)` — catches single-line flag forms, resume form, and backslash-continuation multi-line shapes. Excludes `_shared/codex-config.md` (canonical may discuss the rule itself) and workspace/archive snapshots.

NOT in this diff (deliberately deferred):

- **Shim shipping to user installs.** Codex Round 1 ship-blocker: shim hard-fails 127 without env wiring. Defer to a future iteration that designs installer-managed activation (project-scoped `.claude/settings.json env.PATH` write, or equivalent).
- **`bash -lc 'codex exec ...'` and other indirected forms.** With wrapper-form being the only invocation pattern in skill prompts, these don't arise. Shim remains the safety net for the benchmark variant arm where text-prior is unreliable.
- **F4 / chain smoke runs.** No mechanism change; iter-0009 evidence on F2/F6 covers the orchestrator-emits-wrapper-form claim. Static gate + wrapper canary suffice.

## Falsification gate result (2026-04-27)

All gates passed.

### Static gate (lint-skills.sh, all 10 checks)

```
=== Check 1: No mcp__codex-cli__ outside _shared / archive === ✓
=== Check 2: No 'Requires Codex MCP' prose === ✓
=== Check 3: No hardcoded pre-5.5 model strings === ✓
=== Check 4: No stale 'Claude Opus 4.6' in routing table === ✓
=== Check 5: devlyn:* SKILL.md has name: field === ✓
=== Check 6: Source ↔ installed mirror parity (critical path) === ✓ (extended scope)
=== Check 7: Findings-producing standalones declare JSONL sidecar === ✓
=== Check 8: CRITIC security is native (no stale Dual references) === ✓
=== Check 9: Downgrade string uses 'codex-unavailable' === ✓
=== Check 10: No raw codex exec invocation in skill prompts === ✓ (NEW, wrapper-form everywhere)
All checks passed.
```

### Wrapper canary

| Test | Expected | Observed |
|---|---|---|
| `bash codex-monitored.sh ... | cat` (pipe-stdout) | exit 64 + clear iter-0009-R2 message | exit 64, full message printed (heredoc rendered correctly in interactive shell) |
| `bash codex-monitored.sh dummy > file 2> err` (file-stdout) | exit ≥0, `[codex-monitored] start` on stderr, codex spawns | exit 0, `[codex-monitored] start: ts=2026-04-27T04:54:08Z heartbeat=30s bin=codex` on stderr, codex pid printed, codex banner appeared |

Pattern coverage test for Check 10 (manual stdin test):

| Input | Expected | Observed |
|---|---|---|
| `codex exec -C foo` | match | match |
| `codex exec --full-auto` | match | match |
| `codex exec resume --last` | match | match |
| `codex exec \` (EOL) | match | match |
| `codex exec verbatim — flag semantics` | NO match | NO match |
| `to \`codex exec\`` | NO match | NO match |

### What was NOT run (and why)

- **F4 codex-routed BUILD** — auto-resolve files unchanged in iter-0010; iter-0009 already proved orchestrator-emits-wrapper-form on F2/F6 when SKILL.md text is clean. Re-running F4 would re-prove what's already proven.
- **End-to-end chain smoke (ideate → auto-resolve → preflight)** — covered by static gate (lint Check 10 verifies all 4 skills emit wrapper-form), and the orchestrator-follows-text-prior mechanism is iter-0009-established. Codex Round 2 noted "skipping F4 is reasonable since auto-resolve files weren't touched."
- **Standalone-skill smoke (team-resolve / team-review)** — Codex Round 2 suggested adding one cheap smoke; deferred because the rewrites are mechanical text replacements that lint Check 10 catches at build time.

## Codex collaboration log

- **iter-0010 R1** (design check, before any edits): A vs B for shim distribution, load-bearing edits, hidden risks. Codex returned PASS WITH MINOR FIXES with one ship-blocker: shim hard-fails exit 127 without `CODEX_REAL_BIN` + `CODEX_MONITORED_PATH` envs. Plus 2 phrase-priming sites I missed (team-resolve:147, team-review:88). Plus heartbeat-on-stderr doc bug at canonical:54. Resulting scope change: drop shim shipping from iter-0010, defer to a future iter; surface to user transparently per `feedback_user_directions_vs_debate.md`.
- **iter-0010 R2** (pre-commit check, after edits): full diff review + falsification gate plan critique. Codex returned PASS WITH MINOR FIXES with two real findings:
  1. **Medium**: lint Check 10 pattern `codex exec (-|--|resume[[:space:]])` had a blind spot for multiline `codex exec \` (backslash-continuation EOL). Tightened to `codex exec (-|resume[[:space:]]|\\$)` — single-char `-` already catches both `-` and `--`, and `\\$` catches the multi-line shape. Verified with stdin pattern test on all 4 invocation shapes.
  2. **Low**: 3 remaining descriptive `codex exec` mentions in prompt bodies ("passes args through to `codex exec` verbatim"). Rephrased to "passes args through verbatim" — eliminates priming surface, info available via canonical link.

## Decisions / lessons

1. **Static gate suffices when mechanism is unchanged.** iter-0010 changed only text in skill prompts; iter-0009 already established the mechanism (orchestrator-follows-skill-prompt-text). Lint Check 10 + canary is the right gate; F4/chain-smoke would re-prove what's proven. Goal-driven execution per Karpathy 4: iter-0010's success criterion is "no raw codex exec text in any skill orchestrator reads" — verifiable statically.
2. **Pattern-priming applies even to descriptive text.** Codex Round 2 had me rephrase 3 lines that contained `codex exec` only in prose ("passes args through to `codex exec` verbatim"). The rule isn't "no invocation pattern in prompts" — it's "no `codex exec` token at all in prompts the orchestrator reads beyond canonical reference docs." Cheap to apply, removes prior leak.
3. **Shim shipping needs separate iteration.** The benchmark's PATH-injection scaffolding (zsh shell-snapshot defeat via `.claude/settings.json env.PATH`) doesn't translate to user installs by default. Designing installer-managed activation that's both robust and non-intrusive is its own design problem — queued, not solved by iter-0010. Don't ship the half-solution.
4. **Lint patterns must cover all syntactic shapes the orchestrator can emit.** Codex Round 2's blind spot finding (multi-line `codex exec \`) was load-bearing — the team-resolve and team-review code blocks were exactly that shape pre-iter-0010. A lint that misses the multi-line shape would have allowed regression on the very edits we just made.
5. **Karpathy 3 (surgical changes) protects the iteration.** Earlier autoresearch HANDOFF predicted iter-0010 "ship the shim too." Codex caught the shim was ship-blocking. Scoping iter-0010 to the load-bearing wrapper rewrites + critical fixes (heartbeat doc, phrase priming) and deferring shim shipping to a future iter is exactly the surgical principle. Touch only what the goal requires.
6. **`bash codex-monitored.sh resume --last` works without special-casing.** Wrapper line 114 (`"$CODEX_BIN" exec "$@" < /dev/null &`) produces `codex exec resume --last` which the codex CLI accepts. No wrapper change needed for the ideate `--engine codex` continuity case.

## Suite status

iter-0010 did not run a full benchmark suite. Effective suite state remains iter-0009: F2 + F6 healthy, F1 still hits separate non-codex starvation (iter-0012 candidate), F4/F5/F9 status unchanged from baseline. The next full-suite re-run is queued for whichever iteration ships next that touches the auto-resolve hot path.
