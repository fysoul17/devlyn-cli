# Work packet I2-cross-surface-dependencies

Generated 2026-09-24 against main @466aa25 by a read-only scoping agent, then checked by an adversarial verifier (verdict: **READY_WITH_FIXES**). **Verifier corrections below override the packet body where they conflict.** Line numbers drift: re-check every location against the session's base SHA before editing. Registration: [0221](../../../iterations/0221-subtraction-direction.md).

**Used in:** Session 5: PR-A (add intent, no default change). Session 8: PR-B (intent default at the next major; resolve/ideate become GUIDANCE-ONLY stubs for one major, not executing aliases — 0221 §3/§8). Session 9: PR-C (remove stubs after one major).

## 0221 overrides (authoritative; they replace conflicting body text)

- **Old names are GUIDANCE-ONLY stubs, not executing aliases.** Wherever this packet says "alias" that invokes, maps to or runs `devlyn:intent`, read "guidance-only stub". The stub prints a one-line deprecation notice, the old→new command/flag mapping and the exact new command to run, then stops **without invoking intent** and without resuming an old `.devlyn/pipeline.state.json`. Removed flags still stop with `BLOCKED:removed-flag:<flag>`. Rationale: `resolve --spec` meant explicit full execution, and intent's adaptive execution must not silently replace it (0221 §3, §8).
- **ideate maps to `/devlyn:intent --plan-only`**, in the stub, the release notes and the README, so following the guidance never starts implementation (0221 §3 `--plan-only` contract).
- **PR-B ships at the next major** and only if Session 7 adopts intent. **PR-C** removes the stubs after one major.
- Keep the old `references/task-completion.md` path readable (a pointer) for one major, and document how to resume in-flight old-version runs with the old package version.

## Summary

This packet covers everything outside the resolve skill that depends on /devlyn:resolve or /devlyn:ideate: the installer and its per-agent skill directories, the managed CLAUDE.md and AGENTS.md text (the root files are the packaged templates, per bin/instructions.js:161), queue, engines, the ideate fold, README, templates, standards skills, lint pins, tests, CI and the tracked .agents mirror. The work is split into three PRs so each can run in a fresh session and ends as push + PR with no merge. PR-A only adds /devlyn:intent and changes no defaults. PR-B moves the defaults to intent and turns resolve and ideate into short alias skills that map old flags and stop visibly on removed ones. PR-C deletes the aliases and has the installer remove their directories. The alias period exists because Codex, omp/Pi and Grok skill directories are shared across all projects on the machine (bin/devlyn.js:65,74,97), while each project's AGENTS.md is refreshed only when the installer runs in that project (bin/instructions.js:162). Unrefreshed projects keep telling the model to run /devlyn:resolve and to read devlyn:resolve/references/task-completion.md. Overall the change is strongly net-negative: the ideate body goes (818 lines), lint Check 6f goes (396 lines), Check 6k and static-ab.sh go, and the managed text and README shrink. The only additions are two alias SKILL.md files of about 20 lines, one pointer file, and 2 DEPRECATED_DIRS entries.

## Items

### 0. PR-A / A1 — Install devlyn:intent into every target (additive; no default change).

**Change.** PR-A / A1 — Install devlyn:intent into every target (additive; no default change).

**Files / lines.** bin/devlyn.js:18 becomes ['devlyn:intent','devlyn:resolve','devlyn:ideate','devlyn:design-ui','devlyn:engines','devlyn:queue','_shared']. bin/devlyn.js:663 comment becomes 'Install DEVLYN_CORE_SKILLS into a CLI's'. bin/devlyn.js:725 changes the hardcoded list to `installed (${DEVLYN_CORE_SKILLS.join(' / ')})`, which removes the duplicated list. New directory config/skills/devlyn:intent/ comes from the kernel packet.

**Current behavior.** bin/devlyn.js:18 DEVLYN_CORE_SKILLS = ['devlyn:resolve','devlyn:ideate','devlyn:design-ui','devlyn:engines','devlyn:queue','_shared'] drives the Codex, omp/Pi and Grok installs (bin/devlyn.js:66,75,86,98). Claude core copies all of config/skills (bin/devlyn.js:799-811). The comment at :663 and the log line at :725 hardcode the skill list.

**Target behavior.** `npx devlyn-cli` and `agents <cli>` install devlyn:intent into .claude/skills, ~/.codex/skills, ~/.agents/skills and ~/.grok/skills next to the unchanged resolve and ideate. In PR-A, intent's frontmatter description must say it is used only on explicit invocation. Otherwise it competes with resolve's auto-trigger description at config/skills/devlyn:resolve/SKILL.md:3.

**Tests.** lint Check 5b (scripts/lint-skills.sh:286-380) installs into all four roots, and assertCompleteSkillInstall (bin/devlyn.js:392-409) fails visibly if intent is missing. lint Check 5 (lint-skills.sh:244-256) requires `name: devlyn:intent`. New model-free check: the installer smoke in the acceptance checks.

**Migration.** NONE. The next install adds a devlyn:intent directory to each selected root.

**Risk.** Codex rejects skill descriptions over 1024 chars (bin/devlyn.js:64); no lint enforces this. If intent calls _shared scripts, its SKILL.md must carry the literal `DEVLYN_SKILL_DIR="${CLAUDE_SKILL_DIR:-__DEVLYN_SKILL_DIR__}"` block, or stampInstalledSkillDir (bin/devlyn.js:437-462) cannot stamp it for Codex/omp/Pi/Grok.

**Net lines.** +0 (3 lines edited) plus the kernel packet's intent files

### 1. PR-A / A2 — Lint pins and the tracked .agents mirror for intent.

**Change.** PR-A / A2 — Lint pins and the tracked .agents mirror for intent.

**Files / lines.** scripts/lint-skills.sh: after :93, add intent's shipped files (e.g. devlyn:intent/SKILL.md plus its references; exact list from the kernel packet). scripts/lint-skills.sh:271: update the literal to the A1 array. Add .agents/skills/devlyn:intent/ as a byte copy of config/skills/devlyn:intent/.

**Current behavior.** critical_path_files (scripts/lint-skills.sh:58-104) lists resolve, ideate, queue and engines files. Check 5a pins the exact DEVLYN_CORE_SKILLS literal (lint-skills.sh:271). .agents/skills is a tracked byte-identical copy of config/skills: 59/59 files; `diff -rq config/skills .agents/skills` shows only __pycache__.

**Target behavior.** Check 6/6a parity covers intent in the source, installed and .agents mirrors.

**Tests.** Check 6 (lint-skills.sh:386-392) and 6a (:398-404). Refresh the repo's gitignored unstamped .claude/skills dump before running lint (see acceptance), or Check 6 reports drift.

**Migration.** NONE

**Risk.** Memory gotcha: the Codex sandbox cannot write .agents, so the orchestrator must do the mirror copy.

**Net lines.** +N lint lines (N = number of intent files), plus the mirror copy

### 2. PR-A / A3 — Native Windows real-CLI smoke asserts the new skill.

**Change.** PR-A / A3 — Native Windows real-CLI smoke asserts the new skill.

**Files / lines.** .github/workflows/portability.yml:191-193: resolve becomes intent (`skills / 'devlynintent'`, `'name: devlyn:intent'`, message text).

**Current behavior.** .github/workflows/portability.yml:191-193 asserts that the `devlynresolve` directory exists and contains `name: devlyn:resolve`.

**Target behavior.** The Windows CI proves the colon-aliased intent directory installs from the packed tarball.

**Tests.** The windows job in portability.yml.

**Migration.** NONE

**Risk.** Low.

**Net lines.** 0

### 3. PR-A / A4 — README lists the new installed skill.

**Change.** PR-A / A4 — README lists the new installed skill.

**Files / lines.** README.md:30 and README.md:42: add `devlyn:intent` (preview; explicit invocation).

**Current behavior.** README.md:30 lists the installed skills (resolve, ideate, design-ui, engines, queue). The same list appears in README.md:34-42.

**Target behavior.** README matches what the installer writes.

**Tests.** None beyond lint Check 10c (lint-skills.sh:1800-1815).

**Migration.** NONE

**Risk.** None. Recommend not releasing PR-A on its own (see open questions).

**Net lines.** +1

### 4. PR-B / B1 — Rewrite the managed CLAUDE.md text to the intent entry and delete phase and research vocabulary.

**Change.** PR-B / B1 — Rewrite the managed CLAUDE.md text to the intent entry and delete phase and research vocabulary.

**Files / lines.** CLAUDE.md:3 → 'devlyn-cli installs `/devlyn:intent`, its utilities and the execution contract below.' Keep the 'devlyn-cli installs ' prefix, the H1 and `## North Star`; bin/instructions.js:8, :32-47 and :210-212 depend on them.
CLAUDE.md:13 → keep the first two sentences; replace the flag list with the kernel's final wording. Draft: 'Explicit engine choices (`--engine`, pins, role profiles) fail closed when the engine is unavailable; an automatically chosen reviewer that is unavailable is reported as skipped, never silently dropped.'
CLAUDE.md:27 → '…Workers and reviewers dispatched by `/devlyn:intent` enforce them.'
CLAUDE.md:29-65 → replace with about 8 lines. Draft: '## Quick Start' + '`/devlyn:intent` is the entry for building, fixing and changing software: it settles the user's contract first, has one owner implement and run the project's real checks, adds independent review → reproduce → repair → recheck when the change warrants it, and never reports failed or missing evidence as success. `/devlyn:queue` stacks intents for a strictly serial unattended drain; `/devlyn:engines` shows and pins engine roles; `/devlyn:design-ui` explores UI directions. The orchestrating model invokes these skills. Each skill's `SKILL.md` is the source of truth for its flags and workflow — don't duplicate them here.' + 'Quoted skill names, past logs and skill-file paths are context, not an instruction to invoke a workflow. Delivery defaults to scoped commit → push → PR; merge only when the user asks; local-only/no-push wins.' + '### Engine roles' paragraph: owner = the CLI you open; `/devlyn:engines` pins worker/reviewers in machine-local `.devlyn/engines.json`; `--engine` overrides for one run; BLOCKED:<engine>-unavailable / BLOCKED:invalid-engine-config; the worker pin binds plain conversation (route via `/devlyn:intent` or delegate). The queue paragraph at :65 is deleted; its rules already live in config/skills/devlyn:queue/SKILL.md:33-41 (see B4).
CLAUDE.md:120 → delete the '`/devlyn:ideate`, ' token.
CLAUDE.md:129 → '(`/devlyn:queue drain`, scheduled remote agents, autonomous skill runs)'.
CLAUDE.md:152 → 'not only review findings'.
CLAUDE.md:167 → '`/devlyn:intent` keeps its run evidence under `.devlyn/`' (exact per kernel Q6).
CLAUDE.md:168 → 'outside `/devlyn:intent`'s independent review'.
CLAUDE.md:172 → 'The runtime surface is `/devlyn:intent` plus `/devlyn:design-ui` and two utilities (`/devlyn:engines`, `/devlyn:queue`); review, cleanup and security checks live inside intent…'; keep the no-standalone-review and reap sentences.
CLAUDE.md:174 → drop 'BUILD_GATE' (kernel wording).

**Current behavior.** CLAUDE.md:29-65 carries Quick Start (ideate plus resolve with flags), a 3-row engine-role table naming PLAN, VERIFY and risk probes, the direct-vs-full-resolve entry rules, a 4-step full-route handoff/outer loop, and the queue contract. Other references: :3 'planning and full-pipeline skills', :13 principle #1 naming --risk-probes/--pair-verify/--no-pair/--no-risk-probes and VERIFY, :27 'Sub-agents in /devlyn:resolve and /devlyn:ideate', :120 `/devlyn:ideate`, :129 `/devlyn:resolve`, :152 `/devlyn:resolve` findings, :167 pipeline.state.json, :168 VERIFY dual-judge, :172 two-skill surface, :174 BUILD_GATE. :54 and :65 point to `devlyn:resolve/references/task-completion.md` and a repo-only path, `config/skills/devlyn:resolve/references/outer-loop.md`, which does not exist in user projects (pre-existing defect).

**Target behavior.** Customer projects receive a short intent-first contract with no PLAN/VERIFY/risk-probe/solo-headroom vocabulary. This follows the recorded correction: installed CLAUDE.md/AGENTS.md must not carry internal research context.

**Tests.** lint Check 12 (lint-skills.sh:4014-4105): the :120/:129/:152 edits must be byte-identical in runtime-principles.md (B3). lint Check 6k (lint-skills.sh:1455-1484) pins 'PLAN is orchestrator-fixed…' in CLAUDE.md:43 and is deleted in B11. scripts/test-windows-portability.py:351, :394, :582 assert 'Default to direct execution when inspection makes' and move to a stable phrase of the new text (B12). The instruction migration tests at :358-446 and :562-645 must still pass. scripts/fixtures/instructions/*.md are frozen historical inputs: do not edit.

**Migration.** An existing project's managed block is replaced only when the installer is rerun in that project (bin/instructions.js:200-229). Edits inside the old block are preserved outside it through the historical paragraph keys in bin/instruction-templates.json. Those keys were verified fresh: AGENTS 217/217, CLAUDE 522/522. Projects that are not reinstalled keep the old /devlyn:resolve text, which the B6/B7 aliases serve.

**Risk.** Wording of :13 and the entry model depend on kernel decisions (open questions 1-2). Do not drop the fail-closed explicit-engine, no-silent-fallback, scope or delivery-ownership contracts while deleting phase vocabulary.

**Net lines.** ≈ -30 lines (≈ -7 KB)

### 5. PR-B / B2 — Rewrite the managed AGENTS.md text to match.

**Change.** PR-B / B2 — Rewrite the managed AGENTS.md text to match.

**Files / lines.** AGENTS.md:3 (same change as CLAUDE.md:3). AGENTS.md:13 (same as B1 :13). AGENTS.md:29-31: delete the code block. AGENTS.md:33-34: replace with one `/devlyn:intent` bullet plus queue/engines. AGENTS.md:39: compressed engine-roles line without PLAN/VERIFY and without the Codex resolve-mandatory clause. AGENTS.md:41-45: replace with the two B1 sentences (context-not-instruction; PR-only delivery). Keep the :1 H1 and `## North Star`.

**Current behavior.** AGENTS.md:29-31 has the diagram 'inspect intent -> direct work or full resolve -> ship'. :33-34 describe ideate and resolve; :39 has the engine-roles line, which includes 'If you are Codex orchestrating /devlyn:resolve, the phase machinery is mandatory…'; :41/:43 hold the entry rules; :45 the full-route handoff and queue. Also :3 'planning and full-pipeline skills' and the :13 principle #1 variant.

**Target behavior.** AGENTS.md stays symmetric with CLAUDE.md.

**Tests.** test-windows-portability.py:351/:394/:582 (B12). Check 6k is deleted (B11).

**Migration.** Same as B1. This matters most here: Codex/omp/Pi/Grok skill directories are global, so every project using those agents needs `npx devlyn-cli agents <cli>` rerun (release note).

**Risk.** Same as B1.

**Net lines.** ≈ -12 lines (≈ -5 KB)

### 6. PR-B / B3 — Mirror the principle edits into _shared/runtime-principles.md.

**Change.** PR-B / B3 — Mirror the principle edits into _shared/runtime-principles.md.

**Files / lines.** config/skills/_shared/runtime-principles.md:61, :70, :85: identical to the B1 edits. :3 → 'every worker/reviewer dispatched by `/devlyn:intent` must satisfy'. :97-98 → one consumer line for devlyn:intent/SKILL.md.

**Current behavior.** config/skills/_shared/runtime-principles.md:61, :70 and :85 are byte mirrors of CLAUDE.md:120, :129 and :152. :3 and the consumption block at :97-98 name resolve and ideate.

**Target behavior.** Check 12 parity holds.

**Tests.** lint Check 12.

**Migration.** NONE

**Risk.** Low.

**Net lines.** -1

### 7. PR-B / B4 — Point /devlyn:queue at intent and make queue SKILL.md the single owner of the queue contract.

**Change.** PR-B / B4 — Point /devlyn:queue at intent and make queue SKILL.md the single owner of the queue contract.

**Files / lines.** config/skills/devlyn:queue/SKILL.md:3 → 'spec → /devlyn:intent → verified done'.
:6 → 'Owns the intent-queue contract; project instructions only point here.' (CLAUDE.md:65 and AGENTS.md:45 are deleted in B1/B2. Their rules already sit in :33-41: go-ahead, assumption limits, [F] needs-review, commit order, delivery once, retained workspaces, drain report.)
:23-24 and :34 → name-based references to the installed `devlyn:intent` skill's outer-loop and task-completion references, at the location the kernel chooses (Q5).
:35 → '/devlyn:intent --spec <path>'.
:36 → keep terminal-claim-check.py only if the kernel keeps that predicate.
:37 → the kernel's terminal verdict set.
:38 → PR-only delivery wording (D2).
:41 → '/devlyn:intent'.

**Current behavior.** config/skills/devlyn:queue/SKILL.md:3 says 'spec → /devlyn:resolve'. :6 says it follows the contract held in CLAUDE.md/AGENTS.md. :24 reads `../devlyn:resolve/references/outer-loop.md`. :34 reads `../devlyn:resolve/references/task-completion.md`. :35 runs `/devlyn:resolve --spec`. :37 uses resolve verdict names (NEEDS_WORK, build-gate exhaustion, implement-empty). :41 says one `/devlyn:resolve` run at a time. The relative `../devlyn:…` paths do not exist on Windows, where the directory is `devlyn…` (pre-existing).

**Target behavior.** Drain runs each item through intent, serially. The docs/specs/queue.md file API is unchanged.

**Tests.** lint critical path keeps devlyn:queue/SKILL.md (lint-skills.sh:81). Mirror parity.

**Migration.** NONE for queue data: `- [ ]`/`[x]`/`[F]` and `(spec: <path>)` are unchanged. This depends on intent's --spec accepting the existing spec.md + spec.expected.json shape validated by `spec-verify-check.py --check/--check-expected`.

**Risk.** Unattended drains change engine behavior. Gate PR-B on the kernel's validation evidence.

**Net lines.** ≈ 0

### 8. PR-B / B5 — Point /devlyn:engines at intent. Schema is unchanged.

**Change.** PR-B / B5 — Point /devlyn:engines at intent. Schema is unchanged.

**Files / lines.** config/skills/devlyn:engines/SKILL.md:3 → 'for /devlyn:intent (worker / reviewers)'. :6 → 'exactly what `/devlyn:intent` reads before its first dispatch'. :33 → delete the PLAN clause (or use the kernel's owner-reasoning rule). Subcommands :31-39 and role-config.py are unchanged.

**Current behavior.** config/skills/devlyn:engines/SKILL.md:3 says 'devlyn pipeline (executor / pair judge)'. :6 says it writes what '/devlyn:resolve PHASE 0 reads'. :33 says 'PLAN is orchestrator-fixed and never follows the pin', which lint 6k pins.

**Target behavior.** Same subcommands and file. Descriptions no longer use phase names.

**Tests.** lint 6k is deleted (B11). Critical path lint-skills.sh:82 stays.

**Migration.** NONE: `.devlyn/engines.json` keys executor, pair_judge_priority and roles.{worker,primary_judge,pair_judge} keep their meaning. If intent drops primary_judge, role-config.py must reject it explicitly, never ignore it (kernel).

**Risk.** Role semantics are for the kernel to decide (open question 7).

**Net lines.** 0

### 9. PR-B / B6 — Fold ideate into intent: replace the ideate body with an alias.

**Change.** PR-B / B6 — Fold ideate into intent: replace the ideate body with an alias.

**Files / lines.** Delete config/skills/devlyn:ideate/references/** (7 files). spec-template.md is moved with `git mv` into intent if the kernel keeps writing specs (Q3). Replace config/skills/devlyn:ideate/SKILL.md with the alias: frontmatter `name: devlyn:ideate`, description 'Deprecated alias of /devlyn:intent; removed in the next major release. Use only when the user explicitly types /devlyn:ideate or $devlyn:ideate.' Body [0221 override: guidance-only]: say so in one line, print the argument mapping and the exact `/devlyn:intent …` command to run, then STOP; do not invoke intent. Mapping [0221 override: every ideate mapping targets `/devlyn:intent --plan-only`, so the printed command never proceeds to implementation]: idea text → `/devlyn:intent --plan-only "<idea>"`; --quick → `--plan-only --quick`; --from-spec <p> → `--plan-only --from-spec <p>`; --project → `--plan-only --project`; output-location flags keep their plan-only equivalents. Other flags stop with `BLOCKED:removed-flag:<flag>` and print the table. Mirror the same in .agents/skills/devlyn:ideate/.

**Current behavior.** config/skills/devlyn:ideate: SKILL.md (159 lines) with modes --quick, --from-spec, --project, --spec-dir, --spec-id, --in-place and --engine, plus references/elicitation.md, from-spec-mode.md, project-mode.md, spec-template.md and templates/{decision,roadmap,vision}.md (818 lines in total). Every announcement ends in '/devlyn:resolve --spec' (SKILL.md:115,149; elicitation.md:108; from-spec-mode.md:69; project-mode.md:66-67,87).

**Target behavior.** `/devlyn:ideate` still resolves in every agent and redirects visibly. There is no second spec-elicitation implementation.

**Tests.** lint critical_path_files: remove lint-skills.sh:75-79. lint Check 6f is deleted (B11). lint Check 10d loop at :1846 (B11).

**Migration.** The gitignored `.devlyn/ideate-draft.md` is harmlessly orphaned. Existing specs under docs/specs stay valid input for `intent --spec`.

**Risk.** Losing --project decomposition if intent does not replace it (Q3).

**Net lines.** ≈ -806 (plus the same in the mirror)

### 10. PR-B / B7 — Replace the resolve body with an alias and a task-completion pointer (boundary with the kernel packet, which deletes the resolve body and resolve-on

**Change.** PR-B / B7 — Replace the resolve body with an alias and a task-completion pointer (boundary with the kernel packet, which deletes the resolve body and resolve-only _shared scripts).

**Files / lines.** config/skills/devlyn:resolve/SKILL.md → alias of about 20 lines: `name: devlyn:resolve`, deprecated-alias description, one-line notice, then print the mapping and the exact `/devlyn:intent …` command and STOP [0221 override: guidance-only; never invoke intent]. Mapping table: goal → goal; --spec → --spec; --engine → --engine; rows for --goal-file, --verify-only, --role-config, --pair-verify and --no-pair per Q2. --bypass, --max-rounds, --perf, --risk-probes, --no-risk-probes and any unmapped flag stop with `BLOCKED:removed-flag:<flag>`. An existing `.devlyn/pipeline.state.json` from an earlier resolve run is reported and not resumed.
config/skills/devlyn:resolve/references/task-completion.md → one line: 'Moved: read references/task-completion.md in the installed devlyn:intent skill.' (or the kernel's location).
All other resolve references are deleted by the kernel packet. Mirror in .agents/skills/devlyn:resolve/.

**Current behavior.** config/skills/devlyn:resolve has 12 files, 1,613 lines and 161,727 bytes. The flags are those in _shared/resolve-bootstrap.py:22-25: --spec, --verify-only, --goal-file, --engine, --role-config, --max-rounds, --bypass build-gate|cleanup, --pair-verify, --no-pair, --risk-probes, --no-risk-probes, --perf. The 3.2.x managed text (CLAUDE.md:54, AGENTS.md:41) tells models to read `references/task-completion.md` in the installed devlyn:resolve directory.

**Target behavior.** Explicit resolve use is never silently re-semantic'd: mapped flags pass through with a notice, and removed flags fail visibly. This matches 0201's requirement not to silently change resolve semantics (autoresearch/iterations/0201-harness-transformation-plan.md:172-175).

**Tests.** lint critical_path_files: remove lint-skills.sh:80 and :83-93. lint Check 5b (lint-skills.sh:369-370) still finds the devlyn:resolve directory. test-windows-portability.py:320-327 asserts `name: devlyn:resolve` plus the stamped runtime_paths block in resolve SKILL.md. Either keep that block in the alias or switch the test's `name` to devlyn:queue in PR-B.

**Migration.** In-flight resolve runs cannot be resumed after upgrading (release note). Archived .devlyn/runs are untouched.

**Risk.** The alias is temporary surface. It must be deleted in PR-C, not kept.

**Net lines.** +~21 alias/pointer (the resolve body deletion of about -1,592 is counted by the kernel packet)

### 11. PR-B / B8 — Other shipped text that names resolve, ideate or phases.

**Change.** PR-B / B8 — Other shipped text that names resolve, ideate or phases.

**Files / lines.** config/templates/prompt-templates.md:26, :64 → `/devlyn:intent`. config/skills/code-health-standards/SKILL.md:11, config/skills/root-cause-analysis/SKILL.md:11 and :65, config/skills/ui-implementation-standards/SKILL.md:73 → `/devlyn:intent`. Skip these if the frontmatter-fix packet (D5) already deleted those Trigger/Routing lines. bin/devlyn.js:250 → 'powers /devlyn:intent browser checks (Chrome MCP → Playwright → curl fallback)' (only if the kernel keeps browser checks). bin/devlyn.js:858 → 'so devlyn runs don't prompt'. package.json:4 → drop 'with phase-gated pipelines'.

**Current behavior.** config/templates/prompt-templates.md:26 and :64 recommend `/devlyn:resolve` (installed to .claude/templates by bin/devlyn.js:805). Standards skills: code-health-standards/SKILL.md:11, root-cause-analysis/SKILL.md:11 and :65, ui-implementation-standards/SKILL.md:73. bin/devlyn.js:250 has the playwright description 'powers /devlyn:resolve BUILD_GATE browser tier'; :858 has the comment 'so resolve doesn't prompt'. package.json:4 has the description '…with phase-gated pipelines…'.

**Target behavior.** No shipped text points users at the deprecated entries.

**Tests.** lint Check 10c (lint-skills.sh:1800-1815). Stale-entry grep (acceptance).

**Migration.** NONE

**Risk.** Merge conflicts with the standards-frontmatter packet (D5).

**Net lines.** 0

### 12. PR-B / B9 — _shared text and user-visible strings that name resolve or ideate. The kernel packet owns these files; they are listed here so no reference is misse

**Change.** PR-B / B9 — _shared text and user-visible strings that name resolve or ideate. The kernel packet owns these files; they are listed here so no reference is missed.

**Files / lines.** The same lines, retargeted to devlyn:intent or deleted with the kernel's deletion of resolve-only scripts. At minimum, spec-verify-check.py:5323 must be retargeted by the end of PR-B unless the B7 alias maps --verify-only.

**Current behavior.** config/skills/_shared/engine-preflight.md:3,7,18,22,36; codex-config.md:25,35,79; adapters/omp.md:5,13; spec-verify-check.py:51,769 (docstrings) and :5323 (user-visible fix_hint naming `/devlyn:resolve --verify-only`); task-complete.py:5; archive_run.py:2,70; finish-gate.py:2; resolve-bootstrap.py:2 and :1030 (the self-test locates the sibling devlyn:resolve/references/state-schema.md); pair-plan-schema.md:3,12.

**Target behavior.** No _shared output tells a user to run /devlyn:resolve.

**Tests.** resolve-bootstrap.py --self-test (run by portability.yml:46, :197-199) fails once the resolve directory is gone. This is resolved by the kernel packet (see C7).

**Migration.** NONE

**Risk.** Cross-packet ordering: PR-B cannot pass CI until the kernel packet's resolve-pin and bootstrap changes land in the same PR or earlier.

**Net lines.** 0 (kernel)

### 13. PR-B / B10 — Rewrite README around intent.

**Change.** PR-B / B10 — Rewrite README around intent.

**Files / lines.** README.md:30, :34-42 → intent-first skill list and the $devlyn:intent (Codex/omp/Pi) and /devlyn:intent (Claude/Grok) forms. :44-61 → delete. :63-110 → short intent usage block with flags from the kernel. Delivery text becomes 'scoped commit → push → PR; merge on request' (D2). Delete :87-98 (D6). :112-114 → drain runs /devlyn:intent. :116-160 → pins/profile schema kept, phase names removed; the model example is left to D7. :228-247 → add a paragraph on upgrading to intent and rerunning `npx devlyn-cli agents <cli>` in each project. :255-256 'Now use' → `/devlyn:intent`, plus a row for `/devlyn:resolve` and `/devlyn:ideate` as deprecated aliases. :316 → intent browser checks. :329 → 'Git for the harness'. :332 → `devlynintent`. :354 → drop the skill-specific memory claim. :162-226 (benchmark) belongs to D4.

**Current behavior.** README.md:30 and :34-42 list the resolve/ideate surface. :44-61 is the ideate step. :63-110 covers resolve usage, the flag list at :84, the solo-headroom BLOCKED codes at :87-98, and delivery 'normal protected merge' at :100-110. :112-114 is queue (resolve outer loop). :116-160 is engines with PLAN/VERIFY/SURFACE_CLOSE vocabulary. :250-258 is the legacy map pointing to resolve/ideate. :316 names playwright for resolve BUILD_GATE. :329 says 'Git for the resolve harness'. :332 gives the Windows example `devlynresolve`. :354 claims '/devlyn:resolve recalls prior decisions', but a search of config/skills/devlyn:resolve for 'pyx|memory' found nothing.

**Target behavior.** README is accurate for the intent surface and the alias period.

**Tests.** lint Check 10c (README scan outside the legacy-surface-map block). lint Checks 1-4 and 9 still scan README.

**Migration.** NONE

**Risk.** The README flag table must exactly match the intent SKILL.md.

**Net lines.** ≈ -80

### 14. PR-B / B11 — Lint: delete the phrase pins for removed bodies, retarget the messages, and delete static-ab.sh.

**Change.** PR-B / B11 — Lint: delete the phrase pins for removed bodies, retarget the messages, and delete static-ab.sh.

**Files / lines.** scripts/lint-skills.sh:55-57: comment becomes '`/devlyn:intent` + utilities'.
Delete :896-1291 (Check 6f). Ideate blocks :898-940 and :970-1121 belong to this packet. The _shared pins at :941-969 and :1196-1239 move into Check 6d or are deleted by the kernel/research-vocabulary packet. The resolve pins at :1123-1195 and :1240-1291 go to the kernel.
Delete :1455-1484 (Check 6k).
:1789 → 'current devlyn:intent surface'. Delete :1807. :1811 → 'current intent surface'. :1846 → `for file in config/skills/devlyn:intent/SKILL.md` (or delete :1846-1851 if intent does not inject adapters).
The kernel must remove or retarget resolve pins in 6b (:466-482), 6c1 (:561), 6c2 (:626-656), 6d (:744-753, :845-879), 6e (:1496), 6g (:1293-1322), 6i (:1330-1331), 6i1 (:1353-1393), 6j (:1407-1438) and 10a0 (:1580-1595) in the same PR.
Delete scripts/static-ab.sh (100 lines) and the pointer sentence at scripts/skill-token-gauge.py:14.

**Current behavior.** Check 6f (scripts/lint-skills.sh:896-1291, 396 lines) grep-pins ideate and resolve doc phrases. Check 6k (:1455-1484) pins 'PLAN is orchestrator-fixed' in resolve, CLAUDE.md:43, AGENTS.md:39 and engines:33. :55-57 has the 2-skill comment. :1789 and :1811 have ok-messages naming ideate/resolve. :1807 greps scripts/static-ab.sh, whose file list at static-ab.sh:28-36 is resolve-only. The :1846 loop requires the adapter contract in the resolve and ideate SKILL.md.

**Target behavior.** Lint checks what is actually shipped. Nothing pins deleted prose.

**Tests.** `bash scripts/lint-skills.sh` passes. The behavioral self-tests (spec-verify-check.py --self-test in Check 6d, the installer smokes in 5b) remain.

**Migration.** NONE

**Risk.** Deleting 6f also drops the meta-pins on spec-verify-check self-test messages. Their keep-or-delete belongs to the research-vocabulary packet (D6).

**Net lines.** ≈ -540 (excluding kernel-owned pins)

### 15. PR-B / B12 — Test phrase assertions for the new managed text.

**Change.** PR-B / B12 — Test phrase assertions for the new managed text.

**Files / lines.** scripts/test-windows-portability.py:351, :394, :582 → one stable sentence from the new text, e.g. b'is the entry for building, fixing and changing software'. Keep :581. Do not edit scripts/fixtures/instructions/*.md (historical inputs, copied byte-checked by portability.yml:69-75).

**Current behavior.** scripts/test-windows-portability.py:351, :394 and :582 assert b'Default to direct execution when inspection makes' in the installed block. :581 asserts the older phrase is absent.

**Target behavior.** The migration tests prove that old blocks upgrade to the intent text.

**Tests.** `python3 scripts/test-windows-portability.py`

**Migration.** NONE

**Risk.** Low.

**Net lines.** 0

### 16. PR-B / B13 — Mirror sync. The instruction manifest is not hand-edited.

**Change.** PR-B / B13 — Mirror sync. The instruction manifest is not hand-edited.

**Files / lines.** .agents/skills/** = config/skills/** (aliases, deleted ideate references, queue/engines/_shared edits). bin/instruction-templates.json: no manual edit. Never edit the `versions` entries. The optional local refresh is `node scripts/update-instruction-templates.js` after committing the CLAUDE.md/AGENTS.md change.

**Current behavior.** .agents/skills mirrors config/skills byte for byte. bin/instruction-templates.json holds frozen legacy `versions` fingerprints (lines 1-80) plus paragraph keys that publish.yml:28-29 regenerates from first-parent history.

**Target behavior.** The mirror is identical, and existing 3.x instruction paragraphs remain recognized.

**Tests.** lint Check 6a. The acceptance diff command.

**Migration.** NONE

**Risk.** Codex cannot write .agents (memory gotcha); the orchestrator copies it.

**Net lines.** mirror only

### 17. PR-B / B14 — Release note of user-visible contract changes (GitHub Release body; no CHANGELOG file exists, verified with git ls-files).

**Change.** PR-B / B14 — Release note of user-visible contract changes (GitHub Release body; no CHANGELOG file exists, verified with git ls-files).

**Files / lines.** GitHub Release body at release time. README.md:228-247 (B10). No new files.

**Current behavior.** Release notes live in GitHub Releases (e.g. v3.2.0). README 'Migration from earlier versions' is at :228-247.

**Target behavior.** The release note states:
(1) New `/devlyn:intent` ($devlyn:intent) is the entry. `/devlyn:resolve` and `/devlyn:ideate` are guidance-only stubs (they print the new command and stop) for one major release [0221 override]. The ideate stub always points to `/devlyn:intent --plan-only …` (planning only, no implementation).
(2) Flag map. resolve: goal and --spec kept; --engine kept; --goal-file, --verify-only, --role-config, --pair-verify and --no-pair per the kernel; --bypass, --max-rounds, --perf, --risk-probes and --no-risk-probes removed (BLOCKED:removed-flag). ideate: --quick is now the default behavior; --from-spec → --spec; --project per decision; --spec-dir, --spec-id and --in-place removed.
(3) Removed BLOCKED codes: solo-headroom-hypothesis-required, solo-ceiling-avoidance-required, large-needs-ideation (D6).
(4) Delivery default is push + PR, with no automatic merge (D2).
(5) The engines.json schema and the docs/specs/queue.md format are unchanged.
(6) Rerun `npx devlyn-cli` / `npx devlyn-cli agents <cli>` in every project; Codex/omp/Pi/Grok skills are machine-global while AGENTS.md is per project.
(7) Finish or abandon in-flight resolve runs before upgrading.
(8) New installs no longer set CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING (D3, if it ships in the same release).

**Tests.** None (documentation).

**Migration.** Described in the note itself.

**Risk.** Per the recorded correction, do not claim existing projects migrate automatically: only reinstalled projects change.

**Net lines.** 0 repo lines

### 18. PR-C / C1 — Installer: stop shipping resolve and ideate and purge the installed copies.

**Change.** PR-C / C1 — Installer: stop shipping resolve and ideate and purge the installed copies.

**Files / lines.** bin/devlyn.js:18 → ['devlyn:intent','devlyn:design-ui','devlyn:engines','devlyn:queue','_shared']. bin/devlyn.js:176, after 'skills/devlyn:design-system', adds 'skills/devlyn:resolve' and 'skills/devlyn:ideate' with a one-line comment giving the removal version.

**Current behavior.** After PR-B the aliases are still in DEVLYN_CORE_SKILLS. cleanManagedSkillDirs (bin/devlyn.js:482-494) only removes target directories that still exist in source, so deleting the source alone would leave stale copies everywhere.

**Target behavior.** The next install deletes devlyn:resolve and devlyn:ideate (including U+F03A aliases, via skillPath) from .claude/skills, ~/.codex/skills, ~/.agents/skills and ~/.grok/skills (cleanupDeprecated, bin/devlyn.js:342-361, called at :678 and :814). User skills are untouched.

**Tests.** test-windows-portability.py:332 changes `old` from devlyn:auto-resolve to devlyn:resolve and devlyn:ideate; :338-340 asserts both are purged and user-skill/keep is preserved.

**Migration.** Installed resolve/ideate directories are removed on the next install. Projects whose AGENTS.md is not refreshed still mention /devlyn:resolve (release note: rerun the installer per project).

**Risk.** Codex treats a mention of a skill that no longer exists as plain text, so the model may improvise. Mitigate through the release note and reinstalling each project.

**Net lines.** +2

### 19. PR-C / C2 — Delete the alias directories in source and in the mirror.

**Change.** PR-C / C2 — Delete the alias directories in source and in the mirror.

**Files / lines.** git rm -r config/skills/devlyn:resolve config/skills/devlyn:ideate .agents/skills/devlyn:resolve .agents/skills/devlyn:ideate.

**Current behavior.** PR-B aliases exist at config/skills/devlyn:{resolve,ideate}/ and .agents/skills/devlyn:{resolve,ideate}/.

**Target behavior.** Intent is the only implementation.

**Tests.** lint Check 5 (glob over devlyn:*). Mirror diff.

**Migration.** See C1.

**Risk.** None once C1 lands in the same PR.

**Net lines.** ≈ -45

### 20. PR-C / C3 — Lint pins after removal, plus a permanent retired-entry guard.

**Change.** PR-C / C3 — Lint pins after removal, plus a permanent retired-entry guard.

**Files / lines.** scripts/lint-skills.sh:271 → the C1 array. :363-364 → devlyn:intent. :1803-1807 → extend the existing README and bin regexes with `(^|[[:space:](`'"])[/$]devlyn:(resolve|ideate)([^a-z-]|$)`. This does not match the 'skills/devlyn:resolve' entries in DEPRECATED_DIRS, and the README legacy-surface-map block stays exempt via the existing sed. Add CLAUDE.md, AGENTS.md and config/templates to the same scan.

**Current behavior.** lint-skills.sh:271 pins the PR-B array. :363-364 assert the devlyn:resolve directory exists in the incomplete-install smoke. Check 10c (:1800-1815) guards only auto-resolve-era names.

**Target behavior.** Removed entries cannot reappear in shipped copy.

**Tests.** `bash scripts/lint-skills.sh`

**Migration.** NONE

**Risk.** Watch for regex false positives on historical text. Keep the scan to shipped files only; autoresearch, docs/specs and benchmark are excluded.

**Net lines.** ≈ +3

### 21. PR-C / C4 — Portability tests use intent as the core-skill probe.

**Change.** PR-C / C4 — Portability tests use intent as the core-skill probe.

**Files / lines.** scripts/test-windows-portability.py:320, :325 → devlyn:intent (only if intent SKILL.md carries the runtime_paths stamp block; otherwise devlyn:queue). :723, :727, :731, :734 → devlyn:intent / devlynintent.

**Current behavior.** scripts/test-windows-portability.py:320 and :325 use devlyn:resolve as the installed-skill and stamp probe. :715-735 use `devlynresolve` for alias-ambiguity cases.

**Target behavior.** Tests exercise shipped skills only.

**Tests.** `python3 scripts/test-windows-portability.py`, plus the Windows CI job.

**Migration.** NONE

**Risk.** Low.

**Net lines.** 0

### 22. PR-C / C5 — README legacy map finalized.

**Change.** PR-C / C5 — README legacy map finalized.

**Files / lines.** README.md:255-257: resolve and ideate rows become 'removed in <version> → /devlyn:intent'. README.md:251: fix the 'three current commands' count sentence.

**Current behavior.** After PR-B, README.md:250-258 lists resolve and ideate as deprecated aliases.

**Target behavior.** The historical mapping stays discoverable.

**Tests.** lint 10c skips this block by design.

**Migration.** NONE

**Risk.** None.

**Net lines.** ≈ 0

### 23. PR-C / C6 — Stop hook installed into .claude/settings.json. Conditional on the kernel's decision about pipeline state (Q6).

**Change.** PR-C / C6 — Stop hook installed into .claude/settings.json. Conditional on the kernel's decision about pipeline state (Q6).

**Files / lines.** If intent keeps `.devlyn/pipeline.state.json`: no change, and do not rename resolve-stop-hook.py.
If the kernel deletes the hook script: in the same PR, replace bin/devlyn.js:897-922 with removal of only the exact owned hook object (command === stopHookCommand), and drop an entry only when its hooks array becomes empty. Also update :925 log text; scripts/test-windows-portability.py:265-266 (assert absence and that a pre-seeded user Stop hook survives); scripts/lint-skills.sh:73 (critical path); config/skills/_shared/archive_run.py:41 and :686 (kernel).

**Current behavior.** bin/devlyn.js:897-925 adds a Stop hook entry with the exact command `python3 "$CLAUDE_PROJECT_DIR/.claude/skills/_shared/resolve-stop-hook.py"` (:911). Verified in this session: `python3 <missing file>` exits 2. Claude Code treats exit 2 from a Stop hook as blocking, so deleting or renaming the script without migrating settings.json would block every Stop in upgraded projects.

**Target behavior.** Upgraded projects never call a missing hook script, and user hooks are preserved.

**Tests.** test_global_claude_settings_shared_with_project (test-windows-portability.py:252-268), updated. New model-free acceptance: a settings.json pre-seeded with the user's hook plus the devlyn hook keeps only the user's hook after install.

**Migration.** The next install removes the owned entry from `.claude/settings.json`. Projects that are not reinstalled keep both the old script and the old entry, so they stay consistent.

**Risk.** HIGH if the script is removed without this migration (Stop loop). Also, resolve-stop-hook.py self-test fixtures live under benchmark/ceiling/results (resolve-stop-hook.py:212-221), so D4 must account for them.

**Net lines.** ≈ -10 (conditional)

### 24. PR-C / C7 — CI steps that call resolve-only scripts. Conditional on the kernel.

**Change.** PR-C / C7 — CI steps that call resolve-only scripts. Conditional on the kernel.

**Files / lines.** .github/workflows/portability.yml:46 and :196-199: delete, or rename to the kernel's replacement self-test, in the same PR that deletes or renames resolve-bootstrap.py.

**Current behavior.** .github/workflows/portability.yml:46 (POSIX) and :196-199 (Windows) run `config/skills/_shared/resolve-bootstrap.py --self-test`. That self-test reads the sibling devlyn:resolve/references/state-schema.md (resolve-bootstrap.py:1030-1033).

**Target behavior.** CI never references a deleted script.

**Tests.** The portability workflow on the PR.

**Migration.** NONE

**Risk.** CI red if this is done in a different PR from the script deletion.

**Net lines.** ≈ -4 (conditional)

## Acceptance checks

- Each PR, before lint: `rsync -a --delete --exclude __pycache__ config/skills/ .claude/skills/` refreshes the repo's gitignored unstamped dump (lint Check 6 compares it byte for byte). Then `bash scripts/lint-skills.sh; echo rc=$?` → prints 'All checks passed.' and rc=0.
- Each PR: `python3 scripts/test-windows-portability.py` → OK. Each PR: `git diff --check` → no output.
- Each PR: `diff -r -x __pycache__ config/skills .agents/skills && echo MIRROR-OK` → MIRROR-OK.
- PR-A install smoke: `REPO=$(pwd); T=$(mktemp -d); mkdir -p "$T/home" "$T/proj"; (cd "$T/proj" && HOME="$T/home" node "$REPO/bin/devlyn.js" -y >/dev/null && HOME="$T/home" node "$REPO/bin/devlyn.js" agents all >/dev/null); for d in "$T/proj/.claude/skills" "$T/home/.codex/skills" "$T/home/.agents/skills" "$T/home/.grok/skills"; do grep -qx 'name: devlyn:intent' "$d/devlyn:intent/SKILL.md" && test -f "$d/devlyn:resolve/SKILL.md" || echo "FAIL $d"; done` → no FAIL lines.
- Pack contents: `npm pack --dry-run --json 2>/dev/null | python3 -c "import json,sys; f=[x['path'] for x in json.load(sys.stdin)[0]['files']]; print(any(p.startswith('config/skills/devlyn:intent/') for p in f), sorted(p for p in f if p.startswith(('config/skills/devlyn:resolve/','config/skills/devlyn:ideate/'))))"`. Expected: PR-A → True plus the full resolve/ideate lists. PR-B → True plus only the two alias SKILL.md files and devlyn:resolve/references/task-completion.md. PR-C → True and [].
- PR-B upgrade from the last release: `REPO=$(pwd); T=$(mktemp -d); mkdir -p "$T/old" "$T/home" "$T/proj"; git archive v3.2.1 | tar -x -C "$T/old"; (cd "$T/proj" && HOME="$T/home" node "$T/old/bin/devlyn.js" -y && HOME="$T/home" node "$T/old/bin/devlyn.js" agents all && HOME="$T/home" node "$REPO/bin/devlyn.js" -y && HOME="$T/home" node "$REPO/bin/devlyn.js" agents all) >/dev/null; grep -c 'devlyn:instructions:begin' "$T/proj/CLAUDE.md" "$T/proj/AGENTS.md"; grep -nE '[/$]devlyn:(resolve|ideate)' "$T/proj/CLAUDE.md" "$T/proj/AGENTS.md" || echo NO-OLD-ENTRY; grep -l 'devlyn:intent' "$T/home/.codex/skills/devlyn:resolve/SKILL.md" "$T/home/.codex/skills/devlyn:ideate/SKILL.md"` → each file shows count 1, then NO-OLD-ENTRY, and both alias paths are printed.
- PR-B stale-entry grep: `git grep -nE '[/$]devlyn:(resolve|ideate)' -- CLAUDE.md AGENTS.md config/templates 'config/skills/devlyn:queue' 'config/skills/devlyn:engines' config/skills/_shared/runtime-principles.md config/skills/code-health-standards config/skills/root-cause-analysis config/skills/ui-implementation-standards || echo CLEAN` → CLEAN.
- PR-B alias size: `wc -l config/skills/devlyn:resolve/SKILL.md config/skills/devlyn:ideate/SKILL.md` → each ≤ 30. `find config/skills/devlyn:resolve config/skills/devlyn:ideate -type f | sort` → only SKILL.md files plus devlyn:resolve/references/task-completion.md.
- PR-C purge from v3.2.1: repeat the PR-B upgrade command, then `for d in "$T/proj/.claude/skills" "$T/home/.codex/skills" "$T/home/.agents/skills" "$T/home/.grok/skills"; do test ! -e "$d/devlyn:resolve" -a ! -e "$d/devlyn:ideate" -a -f "$d/devlyn:intent/SKILL.md" || echo "FAIL $d"; done` → no FAIL lines.
- PR-C, only if C6 removes the hook: before installing, seed `$T/proj/.claude/settings.json` with the old devlyn Stop entry plus a user entry `{"hooks":[{"type":"command","command":"echo user"}]}`. After install run `python3 -c "import json,sys; s=json.load(open(sys.argv[1])); c=[h['command'] for e in s['hooks']['Stop'] for h in e['hooks']]; assert c==['echo user'], c" "$T/proj/.claude/settings.json"` → exit 0.
- Instruction manifest freshness (read-only): `node -e "const {execFileSync:x}=require('child_process');const {instructionParagraphs:p}=require('./bin/instructions');const m=require('./bin/instruction-templates.json');for(const n of ['AGENTS.md','CLAUDE.md']){const k=new Set();for(const c of x('git',['log','--first-parent','--format=%H','HEAD','--',n],{encoding:'utf8'}).trim().split('\n'))for(const q of p(x('git',['show',c+':'+n],{encoding:'utf8'})))k.add(q.key);console.log(n,[...k].filter(y=>!m.paragraphs[n].includes(y)).length)}"` → prints 0 for both files after the post-commit refresh. Verified 0/0 on main 466aa25 today.

## Open questions

- 1. Entry model (astra discussion): does ordinary conversation load the /devlyn:intent skill for every implementation request, or do CLAUDE.md and AGENTS.md carry the 4-responsibility kernel inline, with the skill reserved for explicit, --spec and queue use? This decides the final B1/B2 text and the phrase that B12 asserts.
- 2. The intent flag set: which resolve flags survive (--verify-only, --goal-file, --role-config, --pair-verify/--no-pair), and what the removed-flag error code is called. This fixes the alias mapping, the CLAUDE.md:13 principle-1 wording and the release note.
- 3. Ideate fold: is --project decomposition replaced by writing docs/specs/queue.md entries, or dropped? Where does spec-template.md live? Who flips spec `status: planned→done`? Today resolve CLEANUP does it (spec-template.md:12).
- 4. Keep /devlyn:queue as a separate utility (recommended: distinct verbs, file API unchanged, only 41 lines) or fold it into /devlyn:intent?
- 5. After resolve is removed, where do task-completion.md and outer-loop.md live (recommended: devlyn:intent/references), and does the 3-iteration spec-amendment outer loop survive?
- 6. Does intent keep .devlyn/pipeline.state.json and therefore resolve-stop-hook.py? This decides C6. If the hook stays, do not rename the file.
- 7. engines.json roles under intent: keep worker, primary_judge and pair_judge unchanged (recommended, so users need no migration), or retire primary_judge with an explicit error?
- 8. Semver and alias length: PR-B = 4.0.0 and PR-C = 5.0.0, or removal folded into the next planned major? The alias must survive at least one released version. Version bumps stay in user-authorized release commits, not in these PRs.
- 9. Should PR-A be released alone (for example 3.3.0 preview) or merged unreleased until PR-B? Recommended: unreleased, so users never get two overlapping entries.
- Dependencies on other packets. Kernel packet: the intent SKILL, deletion of the resolve body and resolve-only _shared scripts, the resolve lint pins listed in B11, and resolve-bootstrap/CI. Delivery default PR-only: task-complete.py/task-completion.md, README:100-110, queue:38. Adaptive-thinking removal: bin/devlyn.js:932-935 and :943, test-windows-portability.py:241-262. Benchmark move out of npm: bin/devlyn.js:1025-1033, 1053-1215 and 1237-1274, README:162-226, the benchmark entries in package.json `files`, lint Checks 13-15, the resolve-stop-hook self-test fixtures. Standards frontmatter fix: overlaps B8. Research-vocabulary removal: README:87-98, the free-form BLOCKED codes, the spec-verify-check solo-headroom pins. Model roster (opus-5-5 / sonnet-5 / gpt-6-astra / gpt-6-sol / grok-4.7): the README:130-140 example. adapters/claude.md declares effort support only for claude-fable-5-1 (pinned by lint-skills.sh:229), so an example giving claude-opus-5-5 an explicit effort would fail with BLOCKED:unsupported-role-option.
- Pre-existing issues noted, not fixed: queue SKILL.md:24/:34 uses `../devlyn:resolve/...` paths that do not exist on Windows (directory is devlynresolve). CLAUDE.md:65 and AGENTS.md:45 cite the repo-only path config/skills/devlyn:resolve/references/outer-loop.md. README:354 claims resolve recalls pyx memory, but nothing in resolve implements it. The standards skills route to deleted skills (/devlyn:clean, /devlyn:review, /devlyn:team-review, /devlyn:implement-ui). The package.json, .gitignore, .npmignore and lint exclusions for devlyn:ideate-workspace become dead once ideate is gone: follow-up only.

## Verifier corrections (authoritative over the body)

- **CORRECTED** — A1 tests: lint Check 5 (lint-skills.sh:244-256) requires `name: devlyn:intent`
  - Check 5 (:246-256) only checks that some `^name:` line exists in the first 20 lines of each devlyn:*/SKILL.md. It never checks the value. The exact-name proof is the installer smoke's `grep -qx 'name: devlyn:intent'`.
- **CORRECTED** — A3: portability.yml:191-193 asserts the `devlynresolve` directory; change to `skills / 'devlynintent'`
  - The lines are right, but the source literal is `skills / 'devlynresolve'` (the U+F03A escape), not `devlynresolve`. The replacement must be `'devlynintent'`, or it asserts a directory the installer never creates. Also rename the `resolve` variable and fix the :193 message. The same literal problem applies to C4 (:723/:727/:731/:734) and B10 (README:332 contains the text `devlynresolve`).
- **CORRECTED** — README: :30 and :34-42 skill lists, :44-61 ideate, :63-110 resolve, :84 flags, :87-98 solo-headroom codes, :100-110 delivery, :112-114 queue, :116-160 engines, :162-226 benchmark, :250-258 legacy map, :316, :329, :332, :354
  - Mostly exact. The engines section is :116-159 and '### Benchmark score runs' starts at :160, not :162. The legacy map spans :250-259. For C5, the resolve row is :255 and the ideate row is :256 (:257 is design-ui).
- **CORRECTED** — README:354: a search of config/skills/devlyn:resolve for 'pyx|memory' found nothing
  - `grep -rniE 'pyx|memory'` finds one unrelated hit (references/phases/probe-derive.md:117 'memory/telemetry services'). The conclusion stands: resolve implements no pyx-memory recall.
- **CORRECTED** — B1: keep the 'devlyn-cli installs ' prefix, H1 and `## North Star` because bin/instructions.js:8, :32-47 and :210-212 depend on them
  - The conclusion to keep them is right, but the cites are partly wrong. :210-212 is the managed-marker branch and does not reference those strings. The real dependencies are: :8 LEGACY regex; :33 and :135-136 H1 regex; :231-237 `## North Star` preamble/body split. Also test-windows-portability.py:587-621 (test_instruction_custom_content_survives_legacy_and_edited_managed_blocks) requires both new templates to keep a `## Quick Start` heading, a line starting `2. **No overengineering**`, `## Core principles`, `1. **No workaround**`, and at least one LEGACY-matching paragraph.
- **CORRECTED** — Acceptance: manifest freshness prints 0 for both files 'after the post-commit refresh', while B13 says bin/instruction-templates.json gets no manual edit
  - These conflict. After the new CLAUDE.md/AGENTS.md is committed, the check prints non-zero unless scripts/update-instruction-templates.js rewrites bin/instruction-templates.json. The packet must say whether that regenerated file is committed. The check is also unnecessary for PR-B: customInstructions already treats the current template's paragraph keys as known (instructions.js:124-127), and publish.yml refreshes history at release.
- **CORRECTED** — B5: engines SKILL.md :3, :6, :33 carry pipeline/PHASE/PLAN wording; lint 6k pins :33
  - Those lines are right, but the edit list is incomplete. :34 says 'at VERIFY/risk-probe time' and :39 says 'never launch a pipeline from this skill'; both are phase vocabulary the target behavior says to remove.
- **REFUTED** — B6: ideate is 818 lines in total (SKILL.md 159 + 7 reference files); net ≈ -806
  - `wc -l` gives 738 in total: SKILL.md 159, elicitation 143, from-spec-mode 76, spec-template 123, project-mode 95, templates 44+50+48. Net is about -718, or about -595 if spec-template.md is moved with git mv. The 7-file count and the announcement lines (SKILL.md:115,149; elicitation:108; from-spec:69; project-mode:66-67,87) are correct.
- **CORRECTED** — B7: resolve has 12 files, 1,613 lines, 161,727 bytes; flags at resolve-bootstrap.py:22-25
  - At 466aa25 it is 12 files, 1,587 lines and 161,135 bytes. The flag set at :22-25 is exact.
- **CORRECTED** — B9/C7: resolve-bootstrap --self-test (portability.yml:46, :197-199) fails once the resolve directory is gone, fixed in PR-C
  - The self-test asserts devlyn:resolve/references/state-schema.md exists (resolve-bootstrap.py:1030-1034). B7 already deletes that file in PR-B, since only SKILL.md and task-completion.md remain. So CI breaks in PR-B, not PR-C. The Windows step is at portability.yml:198-199. C7 must move into PR-B or the kernel PR.
- **CORRECTED** — C6: Stop hook command at bin/devlyn.js:911 (block :897-925); python3 on a missing file exits 2; archive_run.py:41/:686, lint :73, test :265-266, stop-hook fixtures :212-221
  - Every fact checks out (I confirmed rc=2). The PR placement is wrong. If the kernel deletes resolve-stop-hook.py alongside the PR-B resolve-body deletion, this settings migration has to ship in that same PR; putting it in PR-C would leave a released window where upgraded projects hit exit-2 Stop blocks.
- **CORRECTED** — B11: the full list of kernel-owned resolve pins outside 6f/6k is 6b :466-482, 6c1 :561, 6c2 :626-656, 6d :744-753 and :845-879, 6e :1496, 6g, 6i, 6i1, 6j, 10a0
  - The list is incomplete. 6d :826 pins `required_risk_probe_requirements` in config/skills/devlyn:ideate/references/spec-template.md, which B6 deletes or moves, so lint breaks in PR-B. 6d :884-885 and :891-892 pin resolve probe-derive.md and SKILL.md.
- **CORRECTED** — B10/B11: README rewrite is covered by deleting 6f pins (README :87-98); benchmark README pins belong to D4
  - Check 10e line lint-skills.sh:3290 pins README.md:85 ('`--pair-verify` and `--no-pair` are mutually exclusive'). That line sits inside B10's :63-110 rewrite, outside the D4 benchmark range. PR-B lint fails unless :3290 is deleted in PR-B or D4 lands first.
- **CORRECTED** — C3: lint-skills.sh:363-364 assert the devlyn:resolve directory exists in the incomplete-install smoke
  - The asserts are at :369-370 (B7 cites this correctly). :363-364 are the installer invocation lines. The proposed C3 regex contains `'` and must be escaped (`'\''`) inside the existing single-quoted grep -nE. The B10 migration paragraph at README :228-247 sits outside the legacy-surface-map block, so it must not name `/devlyn:resolve` or `/devlyn:ideate`, or C3 lint flags it.
- **CORRECTED** — PR ordering vs D4: the benchmark move is only a general dependency
  - The shipped runner benchmark/auto-resolve/scripts/run-fixture.sh:416-417 (npm files include benchmark/auto-resolve/scripts/**, package.json:72) invokes `/devlyn:ideate --quick` and `/devlyn:resolve --spec`. It works through the PR-B aliases but `npx devlyn-cli benchmark` breaks in PR-C, so D4 must land before PR-C.

## Missed references found by the verifier

- scripts/lint-skills.sh:826 — Check 6d pins config/skills/devlyn:ideate/references/spec-template.md (breaks when B6 deletes or moves it)
- scripts/lint-skills.sh:884-885, :891-892 — Check 6d resolve pins (probe-derive.md, SKILL.md) missing from B11's kernel list
- scripts/lint-skills.sh:3290 — Check 10e pins README.md:85 ('`--pair-verify` and `--no-pair` are mutually exclusive'), inside the B10 rewrite range
- scripts/test-windows-portability.py:707 — glob('devlyn*resolve') in test_incomplete_source_has_no_marker; StopIteration in PR-C
- scripts/test-windows-portability.py:587-621 — requires both new templates to keep `## Quick Start`, a line starting `2. **No overengineering**`, `## Core principles`, and a LEGACY-matching paragraph (bin/instructions.js:8)
- bin/instructions.js:33, :135-136, :231-237 — the actual H1 and North Star dependencies (not :210-212)
- config/skills/devlyn:engines/SKILL.md:34 ('at VERIFY/risk-probe time') and :39 ('never launch a pipeline')
- CLAUDE.md:172 final clause 'resolve never delegates to it'
- AGENTS.md:110 — docs/VISION.md, docs/ROADMAP.md, docs/roadmap/** are ideate --project outputs; depends on Q3
- .github/workflows/portability.yml:198-199 — Windows bootstrap self-test; must change in PR-B or the kernel PR, since state-schema.md is deleted there (resolve-bootstrap.py:1030-1034)
- .github/workflows/portability.yml:191 — literal is 'devlynresolve'; the replacement needs 'devlynintent'
- benchmark/auto-resolve/scripts/run-fixture.sh:416-417 — shipped benchmark invokes /devlyn:ideate --quick and /devlyn:resolve --spec; D4 must land before PR-C
- benchmark/auto-resolve/measure-static.py:7 — docstring points to scripts/static-ab.sh, which B11 deletes
- bin/devlyn.js:469 — UNSHIPPED_SKILL_DIRS 'devlyn:ideate-workspace', missing from the dead-entry follow-up list

## Acceptance checks the verifier could not run as written

- `python3 scripts/test-windows-portability.py` — not run here (it packs and npm-installs into a TemporaryDirectory and runs long). It can run locally in principle, but the Windows-specific cases only run in the GitHub windows job.
- Instruction manifest freshness 'after the post-commit refresh': this needs scripts/update-instruction-templates.js, which rewrites bin/instruction-templates.json, contradicting B13's 'no manual edit'. Without the refresh it prints non-zero once the new template is committed. The packet must say whether the regenerated file is committed, or drop the check.
- `bash scripts/lint-skills.sh` → rc=0 in PR-B cannot pass as written: Check 10e :3290 (README.md:85) and Check 6d :826 (ideate spec-template) are not handled in the packet.
- PR-B/PR-C upgrade and purge smokes (git archive v3.2.1 → install old → install new) can only run once those PRs exist. The v3.2.1 tag is present, so they are runnable then.
- The windows CI job assertions (A3/C7) can only run on GitHub Actions.
- The B14 GitHub Release body has no repository check.
- `rsync -a --delete ... config/skills/ .claude/skills/` deletes any optional skills installed into the dev's .claude/skills dump. It is harmless in this checkout, which holds only core skills, but note it for other working copies.
- Verified and runnable: the pack dry-run check (current output False plus 20 resolve/ideate files, with npm cache redirected to a scratch dir), the mirror diff (MIRROR-OK today), and the manifest freshness check (0/0 at 466aa25).
