# Work packet T1a-small-cleanups

Generated 2026-09-24 against main @466aa25 by a read-only scoping agent, then checked by an adversarial verifier (verdict: **READY_WITH_FIXES**). **Verifier corrections below override the packet body where they conflict.** Line numbers drift: re-check every location against the session's base SHA before editing. Registration: [0221](../../../iterations/0221-subtraction-direction.md).

**Used in:** Session 1 (all items). Also in Session 1: move the four standards skills to optional-skills/ after the frontmatter fix (0221 §5).

## 0221 overrides (authoritative; they replace conflicting body text)

- **(e) Move the four standards skills to `optional-skills/` after the frontmatter fix.** Use `git mv config/skills/<name> optional-skills/<name>` for code-health-standards, code-review-standards, root-cause-analysis and ui-implementation-standards. Delete the tracked mirror copies `.agents/skills/<name>/`. `.agents/skills` mirrors only `config/skills`; confirm this with `ls .agents/skills` before deleting. Register each skill in `OPTIONAL_ADDONS` (bin/devlyn.js ~227) with the existing `type: 'local'` shape, so the installer offers it as an opt-in. Add the four names to the installer's deprecated/moved list (bin/devlyn.js ~129 and ~168 show the iter-0034 precedent) so upgrades remove the old default copies from `.claude/skills`. Update README "Auto-Activated Skills" (~263-272) to "Optional skills". Lint Check 5 must cover `optional-skills/*/SKILL.md` too.
- **The acceptance checks that name `config/skills/<standards>` or `.agents/skills/<standards>` now use `optional-skills/<standards>` only.** The frontmatter check becomes: `for n in (...): s=pathlib.Path('optional-skills',n,'SKILL.md').read_text(); ...`. Add two checks: `test ! -e config/skills/code-health-standards && test ! -e .agents/skills/code-health-standards` (repeat for all four), and an installer smoke in a temp HOME showing the default install no longer copies them while the opt-in path does.

## Summary

This packet is one PR against the research checkout ~/.local/share/nx01/core-continuation-20260912 (main @466aa25). It makes four cleanups to the installed product and uses no model runs. (a) The four standards skills get the YAML frontmatter every loader expects, and their stale Trigger and Routing sections are deleted. Right now Codex skips them: ~/.codex/logs_2.sqlite has about 1,100 rows reading "failed to load skill …/code-health-standards/SKILL.md: missing YAML frontmatter delimited by ---". Those rows cover ~/.codex/skills, ~/.agents/skills and this repo's tracked .agents/skills. Claude Code falls back to the H1 heading as the description. (b) The generic sentence "Read `_shared/runtime-principles.md`. " is deleted from 5 resolve phase bodies. This is exactly the iter-0099 arm K change: I confirmed it by hashing the C tree at b152feb with that sentence and its trailing space removed, which matches the K manifest in ~/.local/share/nx01/iter0099/receipts for all 5 files. (c) _shared/pair-plan-schema.md moves out of the shipped skill kernel and goes next to the only scripts that cite it, in benchmark/auto-resolve/. (d) New installs stop getting CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING=1 written into ~/.claude/settings.json, and values users already have are kept. Claude Code 2.1.281 only honors this setting when the model name contains opus-4-6 or sonnet-4-6. Delivery is a push to branch candidate/installed-product-cleanups plus an open PR; nothing is merged automatically.

## Items

### 0. (a) Add YAML frontmatter to the 4 standards skills. Delete their `## Trigger` sections, which the frontmatter description replaces, and their `## Routing` secti

**Change.** (a) Add YAML frontmatter to the 4 standards skills. Delete their `## Trigger` sections, which the frontmatter description replaces, and their `## Routing` sections, which point at commands that no longer exist: /devlyn:clean, /devlyn:review, /devlyn:team-review, /devlyn:implement-ui (README.md legacy-surface-map lists them as retired), plus a stale claim that the /devlyn:resolve pair judge is conditional. Widen lint Check 5 so it would have caught this defect, which has been present since 16b19e5 (v0.2.0). Insert this block before line 1 of each file, exactly as shown (PyYAML safe_load checked: each name matches its directory and each description is 293–464 characters, under Codex's 1024 limit):
---
name: code-health-standards
description: Maintainability standards for code you write or change — prevent dead code and orphaned references, justify every new dependency, keep functions, files, nesting and parameter counts within complexity thresholds, follow the established naming conventions, and keep debug logging, commented-out code, swallowed errors and hardcoded secrets out of production code. Use when writing, refactoring or deleting code, adding a dependency, or creating new files or modules.
---
---
name: code-review-standards
description: Severity framework (CRITICAL security, HIGH code quality, MEDIUM best practice, LOW cleanup) and approval criteria for judging a code change. Use when reviewing, auditing or validating a diff, pull request or just-finished implementation, or when deciding whether a change is ready to approve.
---
---
name: root-cause-analysis
description: Evidence-first debugging method — trace a symptom through successive why-steps to the actionable root cause, cite file:line for every claim, and fix the cause instead of masking the symptom. Use when diagnosing a bug, error, failing test, stack trace or unexpected behavior, or when asked why something happens.
---
---
name: ui-implementation-standards
description: Quality bar for building or changing user interfaces — design-system token fidelity, WCAG 2.1 AA accessibility, loading/empty/error/success/disabled state coverage, purposeful animation, and mobile-first responsive layout. Use when implementing or modifying UI components, pages or styles, or when turning a design or design system into code.
---
Lint Check 5: change the glob `config/skills/devlyn:*/SKILL.md` to `config/skills/*/SKILL.md`, add `|| ! head -20 "$skill" | grep -q '^description:'` to the condition, and change the section title and ok/bad messages to 'name: and description:'. Keep the descriptions free of apostrophes: bin/devlyn.js getDescription at :246 cuts the text at the first quote character.

**Files / lines.** config/skills/code-health-standards/SKILL.md: insert frontmatter before :1, delete :5-12 (Trigger) and :70-74 (blank line plus Routing through EOF). config/skills/code-review-standards/SKILL.md: insert before :1, delete :5-11 and :60-64. config/skills/root-cause-analysis/SKILL.md: insert before :1, delete :5-12 and :62-65. config/skills/ui-implementation-standards/SKILL.md: insert before :1, delete :5-12 and :69-74. Tracked mirror: .agents/skills/{same four}/SKILL.md must match the source byte for byte (currently identical, diff -q clean; not part of critical_path_files, so no lint enforces this). scripts/lint-skills.sh:6 (header comment: 'Missing `name:`/`description:` in skill frontmatter') and :241-256 (Check 5). NO change needed (verified): bin/devlyn.js — standards reach only project .claude/skills via copyRecursive(CONFIG_SOURCE, targetDir) at :805; CLI targets install DEVLYN_CORE_SKILLS only (:18, :66, :75, :86, :98; git log -S'code-health' -- bin/devlyn.js has no hits, so the installer never shipped them to Codex). README.md:263-272 becomes accurate as written. package.json files[] ships 'config' wholesale. The CLAUDE.md/AGENTS.md managed text and bin/instruction-templates.json have no references (grep). .github/workflows/portability.yml already runs lint-skills.sh.

**Current behavior.** The four SKILL.md files start with '# <Title>' and have no frontmatter. Claude Code falls back to the H1 heading: this session's skill list shows 'code-health-standards: Code Health Standards', so auto-activation has nothing useful to match on. Codex 0.156.1 skips all four with 'missing YAML frontmatter delimited by ---'. Grok 1.0.41 discovers skills in .claude/.codex/.agents dirs and its binary contains 'missing frontmatter delimiters' and 'Description is required'. README.md:263-272 advertises them as 'Auto-Activated Skills'. Lint Check 5 (scripts/lint-skills.sh:241-256) only globs devlyn:* skills and only checks for name:.

**Target behavior.** All four skills parse under the Codex, Grok, omp/pi and Claude loaders, with a when-to-use description, and no longer point at retired commands. Lint fails if any shipped skill lacks name: or description:.

**Tests.** Existing: lint Check 5 (widened), Check 5b isolated installer smoke (:286-381, unaffected), Check 6/6a parity (standards not listed; unaffected). New model-free checks: a YAML parse check over both trees, a grep that no retired command names remain, and `diff -r -x __pycache__ config/skills .agents/skills` is empty (see acceptance_checks).

**Migration.** The next `npx devlyn-cli` run refreshes the project .claude/skills copies: cleanManagedSkillDirs at bin/devlyn.js:481-495 removes every source-named dir and recopies it. Stale copies in ~/.codex/skills and ~/.agents/skills on research machines were written by benchmark/probes/scripts/run-compliance-cell.sh:41-60 sync_global_skills, not by the installer. They stay broken until the next sync; the installer never managed them.

**Risk.** Low. The descriptions are new always-loaded text in the skill catalog of every Claude session in an installed project, and they may change when these skills auto-activate. That behavior change is the purpose of the fix. The skill bodies below the deleted sections are byte-identical. If a skill appears in multiple directories, Codex prefers one copy but still tries to load the others; that is harmless once all copies are valid.

**Net lines.** About -35 per tree (+16 frontmatter, -51 Trigger/Routing) × 2 trees (config + .agents) = -70; lint Check 5 about +1. Total about -69.

### 1. (b) In each of the 5 phase bodies, delete exactly the bytes "Read `_shared/runtime-principles.md`. " (sentence plus trailing space) and nothing else. This is th

**Change.** (b) In each of the 5 phase bodies, delete exactly the bytes "Read `_shared/runtime-principles.md`. " (sentence plus trailing space) and nothing else. This is the hash-verified iter-0099 arm K transform: sha256 of the b152feb C bodies with that string removed equals the K manifest (manifest-arm-eef557.json) for implement/build-gate/cleanup/verify/probe-derive. Keep the inlined excerpt bullets in implement.md:36-39 (the Codex excerpt) and plan.md:34-39 as they are. Also delete the two words ' or reference' at config/skills/_shared/runtime-principles.md:97 ('Phase prompt bodies inline or reference the operational excerpt…'). This change makes that claim false, so it is an orphan to clean up.

**Files / lines.** config/skills/devlyn:resolve/references/phases/implement.md:34 (the line becomes 'Codex-routed phases receive the inlined excerpt:', exactly as in the K arm); build-gate.md:74; cleanup.md:32; verify.md:314; probe-derive.md:274. Tracked mirror: the same 5 paths under .agents/skills/devlyn:resolve/references/phases/ (enforced by lint Check 6a via critical_path_files at scripts/lint-skills.sh:88-93). config/skills/_shared/runtime-principles.md:97 and .agents/skills/_shared/runtime-principles.md:97 (critical path :104). Gitignored local .claude/skills mirror: a fresh worktree has none, so Check 6 skips it. If a .claude/skills mirror exists, copy the 6 files into it; do NOT run the installer against the real HOME. NO change: no lint pin asserts the sentence (lint mentions runtime-principles only at :104 and in Check 12 :4004-4090, which covers CLAUDE.md↔runtime-principles section markers outside :97); no script hashes phase bodies (phase-prompt-render.py hashes rendered output at run time only); devlyn:resolve/SKILL.md:26-28 (the 'loaded by file or inline' wording is still true: Claude loads it from session CLAUDE.md); devlyn:ideate/SKILL.md:27 (outside arm K); surface-close.md:32-34.

**Current behavior.** implement.md:34, build-gate.md:74, cleanup.md:32, verify.md:314 and probe-derive.md:274 each tell the worker to reread runtime-principles.md, about 14.5 KB. iter-0099 measured it as mostly dead text: 0 reads in 12 opus-4-8 pipeline runs and 4 in 12 on opus-5. With the sentence removed (arm K), results were no worse on all four model/window combinations (autoresearch/iterations/0099-context-placement-ckf.md:268-299, 385-393; docs/specs/queue.md:171-174 recommends deleting it for all engines, with no engine-conditional logic).

**Target behavior.** Phase prompts no longer point workers at an extra ~14.5 KB file. The phase-specific discipline lines and the inlined excerpts stay. runtime-principles.md stays the Check 12 mirror of CLAUDE.md and the ideate contract source.

**Tests.** Existing: lint Check 6a parity for all 6 files; Check 12 unaffected. New model-free checks: grep finds no 'Read `_shared/runtime-principles.md`' in devlyn:resolve in either tree, and a byte-exact check that each new phase body equals the origin/main body with that one string removed (see acceptance_checks).

**Migration.** Installed skills refresh on the next install: the _shared and devlyn:resolve dirs are replaced wholesale (bin/devlyn.js:481-495 for Claude, :687-690 for the other CLIs). Nothing for users to do.

**Risk.** Low to medium. It is a prompt wording change on shared bodies, so Codex and Grok routes also lose the generic read directive; no Claude-only path exists without new conditional code. arm K only covered Claude. Codex keeps the implement.md bullets and AGENTS.md:47-103 (Subtractive-First, Goal-Locked, Evidence sections). Safety evidence comes from arm K being no worse than control; no benefit beyond the removed load is claimed.

**Net lines.** 0 lines. Deletes 5 sentences × 2 trees and 2 words × 2 trees.

### 2. (c) Run `git mv config/skills/_shared/pair-plan-schema.md benchmark/auto-resolve/pair-plan-schema.md` (byte-identical, R100). Run `git rm .agents/skills/_shared

**Change.** (c) Run `git mv config/skills/_shared/pair-plan-schema.md benchmark/auto-resolve/pair-plan-schema.md` (byte-identical, R100). Run `git rm .agents/skills/_shared/pair-plan-schema.md`. Delete the critical-path lint entry. Update the two docstrings that cite the full old path.

**Files / lines.** config/skills/_shared/pair-plan-schema.md → benchmark/auto-resolve/pair-plan-schema.md (rename). .agents/skills/_shared/pair-plan-schema.md (delete). scripts/lint-skills.sh:103 (delete the '_shared/pair-plan-schema.md' line from critical_path_files; otherwise Check 6a fails with 'missing .agents critical-path file'). benchmark/auto-resolve/scripts/pair-plan-idgen.py:20 and benchmark/auto-resolve/scripts/pair-plan-lint.py:19 (path 'config/skills/_shared/pair-plan-schema.md' → 'benchmark/auto-resolve/pair-plan-schema.md'). Leave as-is: pair-plan-lint.py:4 and :235 and oracle-test-fidelity.py:30, which name the file without a path; lint Check 13 (:4102-4160), which runs idgen/lint but never reads the schema; historical mentions in autoresearch/iterations/*, autoresearch/DECISIONS.md and tracked benchmark/ceiling/results/** artifacts. NO change: package.json files[] (the new path is outside the explicit benchmark/auto-resolve *.md allowlist, so it stops shipping); bin/devlyn.js (there is no per-file list; _shared is copied wholesale); autoresearch/scripts/pair-plan-preflight.sh (it calls the scripts, not the schema).

**Current behavior.** This 298-line archive schema (its own header at :3 calls it iter-0022 design archive for the deleted /devlyn:auto-resolve) ships in the npm package through files[] 'config' and installs into every CLI's _shared. No runtime skill references it (git grep: live references are only lint and 3 benchmark scripts).

**Target behavior.** The installed skill kernel no longer carries a research archive, and the schema lives next to pair-plan-idgen.py and pair-plan-lint.py.

**Tests.** Existing: lint Check 6/6a (with :103 removed), Check 13 idgen/lint determinism and NaN rejection. New model-free checks: the file is absent from both skill trees, git reports R100, npm pack --dry-run lists no pair-plan-schema, and git grep finds no live 'config/skills/_shared/pair-plan-schema' reference.

**Migration.** The next install removes the file from installed _shared dirs, because the whole dir is replaced at bin/devlyn.js:481-495 and :687-690. Contributors find it next to its tools.

**Risk.** Very low. No runtime reader. Possible textual conflict with the benchmark-packaging packet if it moves benchmark/auto-resolve/scripts; the schema just moves along with them.

**Net lines.** About -299: the .agents copy (-298) and the lint entry (-1). The rename and docstring edits are 0.

### 3. (d) Stop writing CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING into the global settings file, and never delete an existing value. Replace bin/devlyn.js:928-944 with the

**Change.** (d) Stop writing CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING into the global settings file, and never delete an existing value. Replace bin/devlyn.js:928-944 with the smaller block below. With a single key left, the globalSettingsChanged flag is no longer needed:
  // Configure global Claude Code settings (~/.claude/settings.json)
  // Project settings may refer to this same file; merge the latest bytes.
  const globalSettings = readGlobalSettings();
  if (!globalSettings.env.ENABLE_PROMPT_CACHING_1H) {
    globalSettings.env.ENABLE_PROMPT_CACHING_1H = 'true';
    if (!fs.existsSync(globalClaudeDir)) fs.mkdirSync(globalClaudeDir, { recursive: true });
    fs.writeFileSync(globalSettingsPath, JSON.stringify(globalSettings, null, 2) + '\n');
    log('  → ~/.claude/settings.json (enabled 1h prompt caching)', 'dim');
  }
Keep readGlobalSettings and the early preflight call at :770-794, because the installer still writes this file. Update the tests as described in the tests field.

**Files / lines.** bin/devlyn.js:928-944 (block replacement; the log text is at :943). scripts/test-windows-portability.py:245-246: the expected base env becomes {'ENABLE_PROMPT_CACHING_1H': 'true', **value.get('env', {})}. The first subTest's exact-equality assertion then proves new installs do not write the key; the second subTest at :241, with a pre-existing value '0', proves an existing value is left untouched. Keep :241 as is. scripts/test-windows-portability.py:261: remove the `'CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING': '1',` entry from the asserted dict. Other occurrences, all historical and unchanged: autoresearch/iterations/0017-*.md:32 and 0120-*.md:75. README, CLAUDE.md, AGENTS.md and instruction-templates.json have none (grep). Lint Check 5b (:286-381) asserts only project-level env keys and is unaffected. CI (.github/workflows/portability.yml) runs this test file against the packed artifact on POSIX and Windows; the workflow itself needs no change.

**Current behavior.** installClaudeCore writes env.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING='1' (:932-935; added in ef4ca27, 2026-04-14, whose commit message gives no reason) and env.ENABLE_PROMPT_CACHING_1H='true' (:936-939; 2bd0c4a, 2026-04-15) into ~/.claude/settings.json when they are missing, then logs 'disabled adaptive thinking, enabled 1h prompt caching' (:943). Those two keys are all the global block writes. Separately, the project .claude/settings.json block (:836-926) writes env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS='1' (:888-891), raises env.BASH_MAX_TIMEOUT_MS to at least '3600000' (:892-896), adds 7 permissions.allow entries (:874-887) and adds the resolve-stop-hook.py Stop hook (:898-922). This packet leaves those alone. Evidence that the setting does nothing here: the Claude Code 2.1.281 binary contains `let s=a.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING&&(r.includes("opus-4-6")||r.includes("sonnet-4-6"))`, so it has no effect on claude-opus-5-5, claude-sonnet-5 or fable. ENABLE_PROMPT_CACHING_1H is still used by 2.1.281: it forces the 1h cache TTL, reason 'enable_1h_env', including for subagents and helpers that otherwise default to 5 minutes. It is kept.

**Target behavior.** A new install adds only ENABLE_PROMPT_CACHING_1H to global settings (if missing), user values are preserved, and a reinstall leaves the file byte-identical.

**Tests.** Update scripts/test-windows-portability.py PackageTests.test_global_claude_settings_valid_merge_and_reinstall (:236-250) and test_global_claude_settings_shared_with_project (:252-268). New model-free check: install into a temporary HOME (see acceptance_checks); a fresh HOME must not get the key, and a HOME whose settings already contain '1' must keep it.

**Migration.** Existing ~/.claude/settings.json files keep CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING if present, and the installer never removes it. New installs no longer get it. The PR body should tell users they can delete it by hand: it only affects Opus 4.6 and Sonnet 4.6 per the official model-config docs and the 2.1.281 code. Do not add a README note.

**Risk.** Low. For users still on Opus 4.6 or Sonnet 4.6 who relied on devlyn's injected default, new machines will now use adaptive thinking; that is the CLI default and was an approved decision. Idempotence holds: when caching is already set, nothing is written.

**Net lines.** bin -7, test -2. About -9.

## Acceptance checks

- cd ~/.local/share/nx01/core-continuation-20260912 && git fetch origin && git worktree add -b candidate/installed-product-cleanups ../installed-product-cleanups origin/main   # fresh worktree: no gitignored .claude/skills, so lint Check 6 skips it
- bash scripts/lint-skills.sh; echo rc=$?   # expect rc=0 (widened Check 5, Check 6a parity without pair-plan-schema, Check 5b installer smoke, Check 12, Check 13)
- python3 -c "import yaml,pathlib,sys
for t in ('optional-skills',):  # 0221 override: standards live in optional-skills only
  for n in ('code-health-standards','code-review-standards','root-cause-analysis','ui-implementation-standards'):
    s=pathlib.Path(t,n,'SKILL.md').read_text(); assert s.startswith('---\n'),(t,n); d=yaml.safe_load(s.split('---\n')[1]); assert d['name']==n and 0<len(d['description'])<=1024,(t,n)
print('frontmatter ok')"
- ! grep -rnE '/devlyn:(clean|review|team-review|implement-ui)' config/skills/code-health-standards config/skills/code-review-standards config/skills/root-cause-analysis config/skills/ui-implementation-standards
- diff -r -x __pycache__ config/skills .agents/skills && echo mirror-clean
- ! grep -rn 'Read `_shared/runtime-principles.md`' config/skills/devlyn:resolve .agents/skills/devlyn:resolve
- for f in implement build-gate cleanup verify probe-derive; do p=config/skills/devlyn:resolve/references/phases/$f.md; python3 -c "import subprocess,sys; o=subprocess.check_output(['git','show','origin/main:'+sys.argv[1]]); n=open(sys.argv[1],'rb').read(); s=b'Read \x60_shared/runtime-principles.md\x60. '; assert o.count(s)==1 and o.replace(s,b'',1)==n, sys.argv[1]; print('K-exact', sys.argv[1])" "$p"; done
- grep -c 'Codex-routed phases receive the inlined excerpt:' config/skills/devlyn:resolve/references/phases/implement.md   # expect 1; the bullets at :35-38 still present
- test ! -e config/skills/_shared/pair-plan-schema.md && test ! -e .agents/skills/_shared/pair-plan-schema.md && git diff -M --name-status origin/main -- config/skills/_shared/pair-plan-schema.md benchmark/auto-resolve/pair-plan-schema.md | grep -P '^R100\tconfig/skills/_shared/pair-plan-schema.md\tbenchmark/auto-resolve/pair-plan-schema.md$'
- ! git grep -n 'config/skills/_shared/pair-plan-schema' -- ':!autoresearch/iterations' ':!autoresearch/DECISIONS.md' ':!benchmark/ceiling/results' ':!benchmark/auto-resolve/results'
- npm pack --dry-run --json 2>/dev/null | python3 -c "import json,sys; f=[x['path'] for x in json.load(sys.stdin)[0]['files']]; assert not any('pair-plan-schema' in p for p in f); assert all('config/skills/%s/SKILL.md'%n in f for n in ('code-health-standards','code-review-standards','root-cause-analysis','ui-implementation-standards')); print('package ok')"
- ! grep -n CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING bin/devlyn.js
- R=$PWD; T=$(mktemp -d); mkdir -p $T/fresh/home $T/fresh/proj $T/legacy/home/.claude $T/legacy/proj; printf '{"env":{"CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING":"1"}}\n' > $T/legacy/home/.claude/settings.json; (cd $T/fresh/proj && HOME=$T/fresh/home node $R/bin/devlyn.js -y >/dev/null) && (cd $T/legacy/proj && HOME=$T/legacy/home node $R/bin/devlyn.js -y >/dev/null) && python3 -c "import json,sys; f=json.load(open(sys.argv[1]))['env']; l=json.load(open(sys.argv[2]))['env']; assert 'CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING' not in f and f['ENABLE_PROMPT_CACHING_1H']=='true'; assert l['CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING']=='1' and l['ENABLE_PROMPT_CACHING_1H']=='true'; print('global env ok')" $T/fresh/home/.claude/settings.json $T/legacy/home/.claude/settings.json; rm -rf $T
- python3 scripts/test-windows-portability.py PackageTests.test_global_claude_settings_valid_merge_and_reinstall PackageTests.test_global_claude_settings_shared_with_project PackageTests.test_pack_install_reinstall_optional_stamps   # expect OK
- git diff --check origin/main && git diff --stat origin/main   # expect net-negative lines
- git commit -m 'fix: repair standards skill frontmatter and trim installed runtime surface' && git push -u origin candidate/installed-product-cleanups && gh pr create --base main --head candidate/installed-product-cleanups --fill   # PR body lists (a)-(d), the iter-0099 K hash evidence, the 2.1.281 adaptive-thinking gate evidence, and the manual-removal note for existing CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING values
- gh pr view candidate/installed-product-cleanups --json state,mergedAt --jq '.state+" "+(.mergedAt//"unmerged")'   # expect 'OPEN unmerged': delivery stops at PR, no auto-merge
- gh pr checks candidate/installed-product-cleanups --watch   # POSIX lint/pack/portability and Windows native jobs green
- Post-merge observation (optional, no model call needed to read): after the next Codex session in a repo with the refreshed .agents mirror, `python3 -c "import sqlite3,os;c=sqlite3.connect('file:'+os.path.expanduser('~/.codex/logs_2.sqlite')+'?mode=ro',uri=True);print(c.execute(\"select count(*) from logs where ts>strftime('%s','now','-1 day') and feedback_log_body like '%standards/SKILL.md: missing YAML frontmatter%'\").fetchone())"` shows no new rows for repo-local .agents paths

## Dependencies

- No hard blockers. It needs Node 24 and npm for `npm pack` and the portability test, and python3 with PyYAML for the frontmatter check (available locally).
- Merge order with the /devlyn:intent replacement packet: if that packet lands first and deletes config/skills/devlyn:resolve/references/phases/*.md, drop item (b) because it becomes moot. If this packet lands first, intent inherits the deletion. Removing the Routing sections in item (a) also means the standards skills no longer name /devlyn:resolve, so the rename does not have to touch them.
- Benchmark-packaging packet (moving the suite out of the npm package): possible textual conflict on benchmark/auto-resolve/scripts/pair-plan-idgen.py:20 and pair-plan-lint.py:19. Whichever lands second moves benchmark/auto-resolve/pair-plan-schema.md along with those scripts.
- Work only in the real research checkout ~/.local/share/nx01/core-continuation-20260912, not ~/Documents/GitHub/devlyn-cli. Do not run the installer against the real HOME: it writes ~/.claude/settings.json. Use a temporary HOME as in the acceptance checks.

## Open questions

- Standards skills: the 0221 design (FINAL-design.md:73) left open whether to stop shipping them at all. The approved decision is to fix them. I also delete their Trigger and Routing sections: the new descriptions replace Trigger, and Routing names retired commands. Say so if you want the body left byte-identical except for the frontmatter; the frontmatter alone fixes loading.
- implement.md:34: the hash-verified K transform leaves the lead-in 'Codex-routed phases receive the inlined excerpt:', although every engine receives the bullets. Deleting that lead-in would be an untested wording change, so the packet keeps the measured K bytes.
- The reread sentence lives in shared canonical phase bodies. Removing it only 'on the Claude path' would need new engine-conditional render code, which iter-0099 priced as a cost. The packet deletes it for all engines, as docs/specs/queue.md:171-174 and 0099 finding 1 recommend. Codex keeps the implement.md excerpt bullets and AGENTS.md:47-103. Confirm that Codex losing the generic read directive is acceptable (arm K measured only Claude).
- runtime-principles.md:97: deleting ' or reference' is a two-word doc-truth fix in a file that ideate still reads through devlyn:ideate/SKILL.md:27. It is included because this change otherwise makes the sentence false; it is easy to drop.
- ENABLE_PROMPT_CACHING_1H='true' is still written to user-global settings. Claude Code 2.1.281 still reads it and it changes the subagent/helper TTL. Whether a project installer should write any user-global setting is a separate A2 decision and out of scope here.
- Out of scope, noted only: scripts/static-ab.sh:27 still counts runtime-principles.md in the resolve load set. devlyn:ideate/SKILL.md:27 keeps its own reread. Stale standards copies in ~/.codex/skills and ~/.agents/skills come from run-compliance-cell.sh:41-60 and are fixed only by the next sync. The standards bodies disagree with each other on file-length thresholds: code-health says >500 lines, code-review says >800.

## Verifier corrections (authoritative over the body)

- **CORRECTED** — bin/devlyn.js getDescription at :246 cuts the text at the first quote character.
  - getDescription is at bin/devlyn.js:257; the description regex `description:\s*["']?([^"'\n]+)` is at :269. The behavior is as described, and the result is also truncated to 70 chars. Its only callers are listContents :306/:322 (the `list` output). No test asserts that output.
- **CORRECTED** — Lint Check 5 is at scripts/lint-skills.sh:241-256 and only globs devlyn:* and name:. Header :6 reads 'Missing `name:`/`description:` in skill frontmatter'.
  - Check 5 spans :241-255 (comment :241-243, section :244, glob :246, name grep :248, bad :249, ok :254); :256 is blank. The header currently says '#   2. Missing `name:` in skill frontmatter (Anthropic spec violation).' The packet's quote is the target text, not the current text. The packet also misses the Check 5 comment at :242 ('# 5. Every devlyn:* skill has `name:` in frontmatter.'), which needs updating too.
- **CORRECTED** — The frontmatter defect has been present since 16b19e5 (v0.2.0).
  - code-review-standards, root-cause-analysis and ui-implementation-standards were added without frontmatter in 9308971 (2026-02-14, v0.1.0). Only code-health-standards dates from 16b19e5 (2026-03-02, v0.2.0). git log -S'name: code-review-standards' has no hits, so no version ever had frontmatter.
- **CORRECTED** — This is 'exactly the iter-0099 arm K change'. With it removed, results were 'no worse on all four model/window combinations'.
  - The transform is identical, but the bytes are not the measured bytes. implement, build-gate, cleanup, verify and plan changed after b152feb (git diff --stat b152feb HEAD: verify.md 216 lines, build-gate 42, cleanup 16, implement 6). Only probe-derive and surface-close still equal the measured tree. 'No worse' overstates the result: K passed non-inferiority within band, but on opus-4-8 pipeline K=6 violations vs C=5 (0099:302-307). Only opus-4-8 and opus-5 were measured. None of the current models (opus-5-5, sonnet-5, gpt-6-astra/sol, grok-4.7) were.
- **CORRECTED** — Risk mitigation: Codex keeps the implement.md bullets and AGENTS.md:47-103.
  - This holds only for workspace-write Codex IMPLEMENT. config/skills/_shared/codex-config.md:55 and codex-monitored.sh:151-159 run bounded judge and probe calls (Codex VERIFY pair judge, risk-probe derivation) with CODEX_MONITORED_ISOLATED=1 (--ignore-user-config --ignore-rules), 'so user config, AGENTS.md, hooks, and project rules cannot add hidden context'. On those routes, the one-line phase discipline is the only principles text left. Separately, probe-derive.md:24-28 already forbids reading `.claude/skills`/`.codex/skills` harness docs, which contradicts the :274 reread. That supports deleting it there.
- **CORRECTED** — devlyn:resolve/SKILL.md:26-28 ('loaded by file or inline') is still true after the change.
  - The block is at SKILL.md:26-28 and reads 'Every phase applies ... loaded by file or inline; Codex routes receive it inline.' For Claude it stays roughly true through the installed CLAUDE.md sections (CLAUDE.md:68-157, parity via Check 12). For isolated Codex VERIFY and probe-derive it is false: they get no inline excerpt and no AGENTS.md. For VERIFY this was already inaccurate before the packet. The packet should acknowledge it rather than call the sentence true.
- **CORRECTED** — The implement.md excerpt bullets stay at :35-38 (acceptance-check comment) / :36-39 (files_lines).
  - The bullets are at implement.md:36-39; :35 is blank. The deletion is within line 34, so the numbering does not shift. Fix the acceptance-check comment.
- **CORRECTED** — Target behavior: lint fails if any shipped skill lacks name: or description:.
  - package.json files[] also ships optional-skills/, and the widened glob config/skills/*/SKILL.md does not cover those 11 SKILL.md files. All 11 pass today. Either add optional-skills/*/SKILL.md to the glob or narrow the claim to config/skills. The widened check also does not verify the leading '---' delimiter, which is the literal Codex error, though the name:/description: grep would have caught this defect.
- **CORRECTED** — Dependencies: Node 24 and npm are needed, and PyYAML is available locally.
  - PyYAML 6.0.3 and Python 3.14.6 are installed. Node 24 is not: the PATH default is nvm v20.19.0, nvm also has v22.23.2, and /opt/homebrew/bin/node is v25.4.0. Only CI (portability.yml :37/:115) pins Node 24. package.json has no engines field, so the local checks can run on v20/v25, but Node-24 evidence comes only from the PR's CI.
- **CORRECTED** — Acceptance: the pair-plan rename check uses `... | grep -P '^R100\t...'`.
  - On macOS /usr/bin/grep (BSD), -P fails with 'invalid option -- P' (rc=2), so the check falsely fails in a plain terminal. It passes only inside a Claude Code shell, where grep is wrapped to ugrep. Use `grep -E` with a $'...\t...' literal, or python.
- **CORRECTED** — Post-merge observation: the sqlite query shows no new standards frontmatter rows for repo-local .agents paths.
  - The LIKE pattern '%standards/SKILL.md: missing YAML frontmatter%' misses root-cause-analysis. The query also never filters by path, so the stale ~/.codex/skills and ~/.agents/skills copies (which the packet says stay broken) and other repos' project .agents copies will keep adding rows. Right now it returns 9 rows in the last day. Filter on the repo's .agents path and match all four names. Generating new rows also requires a Codex session.

## Missed references found by the verifier

- scripts/lint-skills.sh:242 — Check 5 comment '# 5. Every devlyn:* skill has `name:` in frontmatter.' must change along with :244/:249/:254 and header :6
- benchmark/README.md:16-21 (the 'Which lane' rule: Skill prompts / runtime-principles → Lane B, 'wording is behavior') and benchmark/instruction-sensitivity/README.md:9-17 (run Lane B for any references/phases/*.md, runtime-principles.md or SKILL.md body change). The packet says it uses no model runs but never addresses this repo rule. It should state that arm K (Claude-only, older bodies) is the evidence for (b), and that the Trigger/Routing deletions fall under the 'pure factual fixes' exemption while the new always-loaded descriptions do not
- config/skills/_shared/codex-config.md:55 + config/skills/_shared/codex-monitored.sh:151-159 — isolated Codex judge/probe calls run with --ignore-rules/--ignore-user-config, so AGENTS.md:47-103 is not a mitigation for Codex VERIFY or probe-derive. Correct the item (b) risk text and open question 3
- config/skills/devlyn:resolve/references/phases/probe-derive.md:24-28 — forbidden_input already bars reading `.claude/skills`/`.codex/skills` harness docs, which contradicts the :274 reread sentence. Cite it as supporting evidence for deleting it there
- config/skills/devlyn:resolve/SKILL.md:27 (and .agents mirror) — 'Codex routes receive it inline' is false for isolated Codex VERIFY/probe-derive after the change. The packet's 'NO change: still true' needs to be corrected, or the sentence adjusted (it was already inaccurate for VERIFY)
- optional-skills/*/SKILL.md (11 files, shipped via package.json files[] 'optional-skills') — outside the widened Check 5 glob, although target_behavior says 'any shipped skill'
- Project-level .agents/skills copies of the four standards skills in other user repos (~/Documents/GitHub/{agent-forge,ai-rag-hub,ian-on-cheil-v1,moonmaker-engine}/.agents/skills, ~/Documents/GitHub/jikji/skills) — they appear in the Codex error log, the installer does not manage them, and the migration section omits them
- autoresearch/iterations/0120-model-adaptation-direction.md:75 — recorded 'no installer/global-setting change is justified'. The PR body should say the approved user decision supersedes it, rather than leave an unacknowledged contradiction
- Open PR #73 (fix/installer-menu-redraw-20260921) touches bin/devlyn.js (+18/-91) and README.md — possible textual conflict; add it to dependencies
- /Users/aipalm/.local/share/nx01/0221-direction-design/FINAL-design.md:66 says to delete the sentence on the Claude path only and keep Codex inline rules. The packet deletes it for all engines (surfaced as open question 3, but the design line should be cited)
- config/skills/devlyn:resolve/references/phases/implement.md:36-39 — the acceptance-check comment should say :36-39, not :35-38

## Acceptance checks the verifier could not run as written

- The acceptance check `git diff -M --name-status ... | grep -P '^R100\t...'` fails under macOS /usr/bin/grep (BSD: 'invalid option -- P'). It works only inside a Claude Code shell, where grep is aliased to ugrep.
- The post-merge sqlite observation cannot produce 'no new rows' as written. Its pattern misses root-cause-analysis, and it does not filter by path, so stale ~/.codex/skills, ~/.agents/skills and other repos' copies keep producing rows. It also needs a live Codex session (a model CLI run) to generate new log rows.
- Running the portability tests (npm pack, test-windows-portability.py) locally 'on Node 24' is not possible: the machine has only Node v20.19.0 (PATH default), v22.23.2 and v25.4.0. Only the PR's CI provides Node 24.
- `gh pr checks --watch` and the `gh pr view` OPEN-unmerged check run only after the push/PR step. They are delivery checks, not pre-commit verification.
