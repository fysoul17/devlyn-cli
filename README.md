<div align="center">

<br />

<picture>
  <img alt="DEVLYN" src="assets/logo.svg" width="540" />
</picture>

### Context, Harness & Loop Engineering Toolkit for AI Coding Agents

**Engineering principles for every coding agent, and a loop designer that turns one intent into tasks agents drain without you.**

[![npm version](https://img.shields.io/npm/v/devlyn-cli.svg)](https://www.npmjs.com/package/devlyn-cli)
[![npm downloads](https://img.shields.io/npm/dw/devlyn-cli.svg)](https://www.npmjs.com/package/devlyn-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-blueviolet)](https://docs.anthropic.com/en/docs/claude-code)

If devlyn-cli saved you time, [give it a star](https://github.com/fysoul17/devlyn-cli) — it helps others find it too.

</div>

---

## Install

```bash
npx devlyn-cli
```

That's it. The installer asks:

1. **What** — `Codex · omp · Pi · Grok` (checked) and `Claude Code` (checked when this project already has a devlyn Claude install). Space toggles, Enter confirms.
2. **Where** — `This project` (default) or `Global — every project on this machine`.
3. **Optional skills & packs** — none checked; see [Optional Add-ons](#optional-add-ons) below. MCP servers are offered only with Claude Code.

In a project, Codex, omp, Pi and Grok load the skills from `.agents/skills/`; Claude Code loads only `.claude/skills/`. The installer never writes `CLAUDE.md` or `AGENTS.md`: those files stay yours. Global installs skills only: `~/.agents/skills/` (omp, Pi, Grok) and `~/.codex/skills/` (Codex), plus `~/.claude/skills/` for Claude Code. Every target gets the `devlyn-ideate` skill and the `devlyn-engines` utility. In Codex / omp / Pi, invoke them as skills (`$devlyn-ideate`); in Claude Code and Grok they're slash commands (`/devlyn-ideate`). Rerunning refreshes skills. See [Migration from earlier versions](#migration-from-earlier-versions) for projects that carry an earlier copy of the principles.

Without prompts, `npx devlyn-cli -y` installs `.agents/skills/` plus every target this project already has; add `--claude` for Claude Code. With `--global` it installs for every project on this machine, plus `~/.claude/skills/` with `--claude` or when it already has a devlyn install. The installer leaves Git to you: it prints no commit guidance after a project install or update. When Git ignores some, but not all, files of an installed skill folder, it prints one line with their count and an example ignore rule.

`npx devlyn-cli update` — Update every devlyn install already here (this project and your global skill folders) to this version; installs nothing new.

---

## How It Works — Principles and Loops

The Devlyn defaults carry the North Star, seven principles (no workaround, no overengineering, no guesswork, worldclass, best practice, optimized, production ready) and three discipline rules, plus short pointers to the skills. Each session gets them from the release, through the Devlyn app or `devlyn run`, so projects hold no copy and a new release reaches every project at once. A session started any other way, as with a plain `npx devlyn-cli` install, gets the skills but not the defaults; ideate still reads its installed copy for the loops it plans and drains. Agents do the work directly under them; for work that splits into tasks, ideate designs a loop and drains it:

```
intent  →  direct work under the Devlyn defaults, or an ideate loop  →  ship
```

Non-Claude agents (Codex / omp / Pi / Grok): the default choice installs the skills for them. In Codex / omp / Pi, use `$devlyn-ideate`; in Grok, use `/devlyn-ideate`, the same slash-command form as Claude Code. A drain from any CLI other than Claude Code or Codex needs [a pinned executor](#executor--devlyn-engines).

### Terminal sessions — `devlyn run`

`devlyn run claude`, `devlyn run codex` or `devlyn run omp` starts the engine in this terminal on macOS or Linux (not Windows) with the same principles and skills the Devlyn app delivers, from the selected release. While the harness is on for the project, only engine arguments known not to change the session's freshness, directory or planned settings pass through, and any other stops the launch; with it off, every argument passes. See [docs/harness-run.md](docs/harness-run.md).

### Plan and drain loops — `/devlyn-ideate`

Give ideate an intent or a document. It writes a loop package — a meta-prompt plus self-contained task contracts with mechanical acceptance — and agents drain the tasks one by one without you.

| Command | What it does |
|---|---|
| `/devlyn-ideate plan <intent or document>` | Inspects the project, asks only what it must, and writes a validated package to `docs/specs/<loop-id>/`. Nothing is queued or run. |
| `/devlyn-ideate add <intent or package>` | Plans when needed, then queues the package's tasks in dependency order. It makes no commit on your branch: the package and its rows in `docs/specs/<loop-id>/queue.md` are held at `refs/devlyn/captures/<loop-id>` and your copies are removed. The first task's commit brings them into history, and the drain report's `Bring into` command brings the result into your branch. |
| `/devlyn-ideate status` | Pending, active, accepted and failed counts; the next runnable task; delivery and recovery blockers. |
| `/devlyn-ideate drain` | Runs the queue serially and hands-free. |

A bare intent is planned and, when your request authorizes the work, added and drained without another confirmation; no arguments shows status. Questions come only when the answer changes behavior, scope, data semantics, acceptance or delivery, each with a recommended answer; `--autonomous` plans without questions, recording ordinary low-consequence, reversible defaults within the request, including user-visible details; material ambiguity in intended outcomes, persistent data or state semantics, or public surface beyond the request stops planning with a concrete question. Each task runs in its own worktree with the executor pinned by `/devlyn-engines` (default: the CLI you opened; a CLI other than Claude Code or Codex needs a pin) under the Devlyn defaults and your project's CLAUDE.md/AGENTS.md. Tasks start from committed state, the branch you added the loop on or the remote base for `auto`/`pr`, so a task's worktree holds only what is committed there. A task would run without CLAUDE.md/AGENTS.md changes that exist only in this checkout, so add stops while they differ from HEAD, and drain waits while they differ from the task's start commit. It is marked `[x]` only when its declared checks pass on its committed source and its required reviews cover it: the checks run through the drain's runner (a wholly clean run the executor lists for that source is reused; the drain runs any other check itself), and review coverage is attested by records the executor submits; a failed task becomes `[F]` with its reason and blocks only its dependents. An interrupted drain resumes without repeating accepted work. `--local-only` (or `--no-push`) keeps delivery local: each accepted task stays on its `devlyn/<loop-id>/<task-id>` branch in a retained worktree, nothing is merged or pushed, and the drain report's `Bring into` command brings the result into your branch, stopping if your files cannot be preserved.

### Delivery

Direct work edits your current checkout; run parallel sessions in separate worktrees (for example `claude -w`). Completed, verified direct requests with changes, and
every drained task, are delivered by project policy from their own linked worktrees. A commit request stays local and a PR request stops at the PR; otherwise accepted tasks default to
scoped commit → push → PR → merge when the repository allows it (otherwise the PR waits for a person). After the
PR merges, the worktree and branch its session released are cleaned; anything in use is
kept. Set `git config --local devlyn.completionMode pr` to stop at the PR; `task-complete.py complete --mode auto|pr`
overrides one task. Local-only/no-push instructions take precedence: nothing is pushed or merged;
a direct task's commit is fast-forwarded into your branch when that is safe, and a drained task
stays on its task branch in its retained worktree. Existing
branches cannot be adopted. Direct tasks use their actual checks and root
acceptance. Pending checks or unsupported merge policy retain resources and
report a receipt-based resume command separately from product verification.
See [task completion](config/skills/_shared/task-completion.md)
for allocation, acceptance, writer cessation and recovery.

### Executor — `/devlyn-engines`

The orchestrator is the CLI you opened (Claude Code, Codex, omp, Pi or Grok); the contract is symmetric (`CLAUDE.md` ↔ `AGENTS.md`), so the loop's file artifacts carry over if you switch. The executor does the implementation work, direct or drained: the engine pinned in machine-local `.devlyn/engines.json`, else the CLI you opened. Only Claude and Codex can execute, so a drain from any other CLI needs `devlyn-engines executor <claude|codex>`.

`/devlyn-engines` with no arguments shows the executor and the engines detected on this machine; `executor <name>` pins one and `clear` removes the pin. A pin is a promise: an unavailable pinned engine stops dispatch with `BLOCKED:<engine>-unavailable`, and a name with no executor-eligible `_shared/adapters/<name>.adapter.md` stops with `BLOCKED:invalid-engine-config`. Adapters ship with devlyn-cli releases; a reinstall replaces `_shared`.

Unattended children disable owner-desktop and account drivers: every monitored
Codex child and every `claude` drain executor (including `.exe`/`.cmd`/`.bat`)
uses a launch-only policy. Wrapped Claude launches (such as `env … claude` or
`node …/claude-code/cli.js`) and ambiguous `node …/cli.js` wrappers are refused;
invoke Claude directly as argv[0]. A shell command or script that starts an engine
itself (for example `sh -c '…'`) is not inspected.
Other engines have no tool guard. Interactive sessions and user settings files stay
unchanged. Add your own server denies in `~/.devlyn/unattended-tools.json`, for
example `{"codex":["my-desktop"],"claude":["my.server"]}`; omitted keys mean no
extra denies, and an absent file means defaults only. Malformed files refuse
the launch. Codex only overrides names returned by its MCP list, verifies they
are disabled, and refuses denied names outside ASCII letters, digits, `_` and `-`.
Claude uses `--disallowedTools=mcp__<server>`: replace each character outside ASCII letters,
digits, `_` and `-` with `_` (`my.server` → `my_server`); `claude.ai ` names also
collapse and trim underscores, matching Claude's namespace normalization.
See [Claude's MCP permission rules](https://code.claude.com/docs/en/permissions#mcp).
Remote URLs are not denied by default, so workers keep remote memory MCP.
An account server you never list remains available.

### Migration from earlier versions

Reinstall with the new version to refresh skills for the selected targets. Install and
update leave `CLAUDE.md` and `AGENTS.md` byte-identical.

Earlier installs put the principles in those files, inside a checksum-marked block or as
a whole template. [Cleanup](docs/harness-cleanup.md) removes an intact copy, keeps the text
around it byte-for-byte and deletes a file that held only the copy; a `@AGENTS.md` import
left without its file is harmless. Exact pre-removal backups are saved in
`.devlyn/instructions/`; pre-existing symlinks or non-directory entries at `.devlyn/` or
`.devlyn/instructions/` stop the removal without touching the file.

A copy someone edited stays exactly as it is, as does any text Devlyn cannot prove it wrote:
a quoted example, or malformed or duplicate markers. Devlyn's defaults replace a remaining
block for each session.
Portability refreshes the offline fingerprints from Git history using
`node scripts/update-instruction-templates.js` before testing; publish ships that tested tarball.
Installation needs no Git or network.

Upgrading to 4.1.0: `npx devlyn-cli -y` in a 4.x project keeps its Claude Code install
current and adds `.agents/skills/`. Earlier releases put the Codex, omp, Pi
and Grok skills in `~/.codex/skills`, `~/.agents/skills` and `~/.grok/skills`; a project
install no longer refreshes them and names each one it finds. Refresh them with `--global`
or delete them; global installs and `update` clean Devlyn’s retired `~/.grok/skills` entries automatically.
`npx devlyn-cli agents` was removed.

<!-- legacy-surface-map:begin — retired command names below are documented as OLD, not current; lint Checks 5e and 10c skip this block -->
Upgrading to 4.2.0: `/devlyn-resolve` and the pipeline helpers only it used are retired;
no measured replacement ships in their place. Run the installer again where devlyn is
installed. It removes the `devlyn-resolve` folders (and pre-4.0.0 `devlyn:resolve` ones)
by their exact retired names, including edited copies and links (link targets stay intact). It
removes the Stop hook it added to `.claude/settings.json` while keeping your own hooks,
and names the other settings it once added for the pipeline
(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` and its `.devlyn` and git permissions) without
deleting them. `/devlyn-engines` keeps only the executor pin: `pair_judge_priority` and
`roles` in `.devlyn/engines.json` stay as written, select nothing, and `clear` removes them.
`task-complete.py` refuses acceptance that points at an archived resolve run
(`kind: pipeline`) before changing anything, and prints the command that finishes the run
with the release that produced it: `npm pack devlyn-cli@4.1.0`, extract the tarball, and run
`python3 package/config/skills/_shared/task-complete.py complete --receipt <receipt>
--acceptance <acceptance>` with your delivery flags. A PR/merge completion there binds the
acceptance before publishing, and a receipt it binds resumes delivery with the current
helper; with `--local-only` it ends as LOCAL_ONLY without binding, as 4.1.0 always did. To
keep using resolve itself, stay on `devlyn-cli@4.1.0`. The Claude target no longer installs
`.claude/templates`; a copy an earlier release installed stays yours.

Upgrading to 4.0.0: every devlyn skill is renamed to the Agent Skills standard
(`/devlyn:ideate` → `/devlyn-ideate`; the full list is in the table below). Run the
installer in each project that has devlyn (`npx devlyn-cli`, or `-y` with `--claude` and
`--global` as needed): each run removes the old folders
where it installs and keeps an optional skill you had under its new name. A 3.x installer run
afterwards brings the old `devlyn:*` folders back beside some new ones and drops opted-in
pencil skills; run the 4.x installer again to repair it, and re-add those pencil skills from
its menu. An agent setting that disables a
devlyn skill by its old name or path (for example Codex `[[skills.config]]` or omp
`disabledExtensions`) needs the new name. A project that committed the old `devlyn:*`
folders checks out on Windows once that re-sync is committed.

Earlier versions of devlyn-cli shipped 16+ slash commands. The iter-0034 Phase 4 cutover (2026-05-04) and the 2026-05-14 follow-up consolidated them, 4.0.0 renamed every devlyn skill to the Agent Skills naming standard (`devlyn-<name>`: lowercase, digits and hyphens, the same as its folder), and after 4.1.0 resolve and design-ui were retired and the queue moved into ideate. Install/update deletes exact retired Devlyn names in its scope; generic files and old instruction text are removed only with evidence matching shipped copies. Other skills, edited generic files, and your instruction text are preserved; instruction changes keep a recovery backup.

| Old command | Now use |
|---|---|
| `/devlyn:auto-resolve`, `/devlyn:preflight`, `/devlyn:evaluate`, `/devlyn:review`, `/devlyn:team-resolve`, `/devlyn:team-review`, `/devlyn:clean`, `/devlyn:update-docs`, `/devlyn:browser-validate`, `/devlyn:implement-ui` | Folded into resolve, now retired — work directly under the Devlyn defaults |
| `/devlyn:product-spec`, `/devlyn:feature-spec`, `/devlyn:recommend-features`, `/devlyn:discover-product` | `/devlyn-ideate` |
| `/devlyn:design-system` | Removed 2026-05-14 — no replacement |
| `/devlyn:ideate`, `/devlyn:engines`, `devlyn:pencil-pull`, `devlyn:pencil-push`, `devlyn:reap` (3.x and earlier) | `/devlyn-ideate`, `/devlyn-engines`, `devlyn-pencil-pull`, `devlyn-pencil-push`, `devlyn-reap` (4.0.0) |
| `/devlyn:resolve` (3.x and earlier), `/devlyn-resolve` (4.0.0–4.1.0) | Retired — work directly under the Devlyn defaults; `/devlyn-ideate` plans and drains multi-task work |
| `/devlyn:queue` (3.x and earlier), `/devlyn-queue` (4.0.0–4.1.0) | `/devlyn-ideate add`, `status` and `drain` |
| `/devlyn-ideate --quick`, `--from-spec`, `--project` (4.1.0 and earlier) | `/devlyn-ideate plan`; `--autonomous` replaces `--quick` |
| `/devlyn:team-design-ui`, `/devlyn:design-ui` (3.x and earlier), `/devlyn-design-ui` (4.0.0–4.1.0) | Retired — no replacement |
<!-- legacy-surface-map:end -->

---

## Optional Add-ons

Selected during install. Run `npx devlyn-cli` again to add more.

<details>
<summary><strong>Skills</strong> — copied into every skill root the install writes</summary>

| Skill | Description |
|---|---|
| `asset-creator` | AI pixel art game asset pipeline — generate, chroma-key, catalog |
| `cloudflare-nextjs-setup` | Cloudflare Workers + Next.js with OpenNext |
| `generate-skill` | Create Claude Code skills following Anthropic best practices |
| `prompt-engineering` | Claude prompt optimization |
| `better-auth-setup` | Better Auth + Hono + Drizzle + PostgreSQL |
| `polar-billing-setup` | Polar usage-based / metered billing — setup and silent $0-billing diagnosis |
| `pyx-scan` | Check if an AI agent skill is safe before installing |
| `dokkit` | Document template filling for DOCX/HWPX |
| `devlyn-pencil-pull` | Pull Pencil designs into code |
| `devlyn-pencil-push` | Push codebase UI to Pencil canvas |
| `devlyn-reap` | Safely reap orphaned MCP / codex / Superset child processes |
| `code-health-standards` | Maintainability standards — dead code, dependencies, complexity, naming |
| `code-review-standards` | Severity framework and approval criteria for reviews |
| `root-cause-analysis` | Evidence-first why-chain debugging |
| `ui-implementation-standards` | UI quality bar — design tokens, accessibility, state coverage, responsive layout |

</details>

<details>
<summary><strong>Community Packs</strong> — installed via <a href="https://github.com/anthropics/skills">skills CLI</a></summary>

| Pack | Description |
|---|---|
| `vercel-labs/agent-skills` | React, Next.js, React Native best practices |
| `supabase/agent-skills` | Supabase integration patterns |
| `coreyhaines31/marketingskills` | Marketing automation and content skills |
| `anthropics/skills` | Official Anthropic skill-creator with eval framework |
| `Leonxlnx/taste-skill` | Premium frontend design skills |

</details>

<details>
<summary><strong>MCP Servers</strong> — installed via <code>claude mcp add</code>, offered with the Claude Code choice</summary>

| Server | Description |
|---|---|
| `playwright` | Playwright MCP for browser testing |

> A Codex executor uses the local `codex` CLI binary, not MCP. Install it from https://platform.openai.com/docs/codex, run the current Codex auth/login flow and verify `codex --version`.

</details>

> **Want to add a pack?** Open a PR adding it to the `OPTIONAL_ADDONS` array in [`bin/devlyn.js`](bin/devlyn.js).

---

Installer updates preserve user work: before writing any selected target, devlyn refuses to replace or remove edited skills, directories with extra files (including hidden files), links, or unknown copies. `-y` does not bypass this check. Unedited copies from every published version upgrade automatically, including committed copies, historical install-path stamps and generated Python bytecode caches. Portability derives the offline skill history from Git with `node scripts/update-skill-history.js` before testing; publish ships that tested tarball. Move conflicting folders to a backup and migrate them manually; also remove conflicting tracked paths from the Git index before rerunning.

Only `__pycache__` directories containing exclusively regular `*.pyc` files count as generated Python caches. Other entries make the directory ordinary content; links and special files are refused. Standalone `*.pyc` files count as content: none of the 113 published versions through 4.2.5 shipped them. Historical path normalization applies only to the escaped absolute assignment defaults written into Markdown by the 2.8.0–4.0.0 installers.

## Requirements

- **Node.js 20 (20.17+), 22 (22.13+) or 23.5+** and npm
- **Python 3.11+** available as `python3` for the harness, and **Git** for safe installation and the harness
- **An agent CLI** installed and configured: Codex, omp, Pi or Grok, or [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- **For `auto`/`pr` delivery**, an `origin` remote naming one GitHub repository and an authenticated [`gh`](https://cli.github.com/)

On native Windows, use native Node/npm and Python plus Git for Windows Bash for the shipped shell wrapper. Run `npx devlyn-cli -y` in the project (add `--claude` for Claude Code). Skill folders follow the Agent Skills naming standard (for example `devlyn-ideate`), so a project that commits them checks out on Windows. Harness text is UTF-8 without requiring `PYTHONUTF8`.

Drain worktrees default to `<repo parent>/.devlyn-worktrees/<repo name>/<loop-id>/<task-id>`. On Windows, a newly created shared container is marked hidden, and each worktree disables content indexing for new children; names stay indexed and Microsoft Defender scanning is unaffected. For Defender performance, use a Dev Drive via `--worktree-root` or an administrator's exclusion for the root; see [loop options](config/skills/devlyn-ideate/references/loop.md).

Windows completion preserves the workspace, owned refs and recovery receipt when writer cessation cannot be proved, even after merge; resume guidance and delivery status remain separate from product verification. The portability workflow checks out the repository on native Windows and tests the POSIX-packed npm artifact there. A POSIX pass alone does not establish Windows support: acceptance requires the passing Windows job for the exact source SHA/artifact hashes.

## Contributing

- **Add a skill** — add it to `optional-skills/` and `OPTIONAL_ADDONS` in [`bin/devlyn.js`](bin/devlyn.js); the core skills are fixed by `DEVLYN_CORE_SKILLS` (lint Check 5a)
- **Suggest a pack** — PR to the pack list

## Supercharge it — pair devlyn with persistent agent memory

devlyn-cli gives your agent a **harness**. Give it a world-class **memory** and the loop compounds — decisions, corrections, and hard-won context survive across sessions instead of resetting every conversation.

> [!TIP]
> ### 🧠 [pyx-memory](https://memory.pyxmate.com) — world-class agentic memory (hybrid RAG) for coding agents
> Durable facts, corrections, and project state your agent recalls and reinforces — so every run starts smarter than the last. → **[memory.pyxmate.com](https://memory.pyxmate.com)**

- **Remembers across sessions** — decisions, gotchas, preferences, and project state, not just this conversation
- **Hybrid retrieval** — semantic *and* graph recall: find by meaning *and* by relationship
- **Learns the loop** — reinforces what works, records corrections when it doesn't

**Harness (devlyn) + Memory (pyx-memory) = agents that don't just execute — they improve.** Wire up **pyx-memory** as an MCP server so your agent recalls prior decisions before it plans and stores what it learns after it ships.

## Support & Attribution

devlyn-cli is built and maintained in the open. If it earns a place in your workflow, two small things keep it alive and help others find it:

- ⭐️ **Star the repo** — [give it a star](https://github.com/fysoul17/devlyn-cli) if it saved you time. It's the single biggest signal that keeps the project going.
- 🔗 **Leave a credit** — if devlyn-cli helped ship your project, a small attribution is genuinely appreciated (kindly requested, never required — the MIT license asks nothing of you here). Drop this badge in your README:

  ```md
  [![Built with devlyn-cli](https://img.shields.io/badge/built%20with-devlyn--cli-blueviolet)](https://github.com/fysoul17/devlyn-cli)
  ```

  Renders as [![Built with devlyn-cli](https://img.shields.io/badge/built%20with-devlyn--cli-blueviolet)](https://github.com/fysoul17/devlyn-cli)

Thank you for using devlyn — it genuinely means a lot. 🙏

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=fysoul17/devlyn-cli&type=Date)](https://star-history.com/#fysoul17/devlyn-cli&Date)

## License

[MIT](LICENSE) — Nocodecat @ Donut Studio
