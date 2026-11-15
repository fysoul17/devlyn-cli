# Research handoff

## Start here

The research record is [DECISIONS.md](DECISIONS.md), newest entry last, with [iterations/](iterations/) and
[experiments/](experiments/) beside it; the owner's decisions are recorded there. This file holds no queue:
what is open, and whose call it is, is in the newest entries.

## Reviews

Astra reviews read-only with Codex's isolation flags: `DEVLYN_CODEX_PROMPT_FILE=<prompt> config/skills/_shared/codex-monitored.sh --ignore-user-config --ignore-rules --ephemeral --disable codex_hooks --disable hooks -C <repo> -s read-only -m gpt-6-astra -c model_reasoning_effort=ultra -`.
- Send stdout to a file, never a pipe.
- Wait on `^\[codex-monitored\] codex exited` in stderr.

## Open owner item

- **The `_devlynjudge` user record (uid 450) remains.** macOS refuses its deletion without Full Disk Access. Removing it is the user's call.

## Known follow-ups

- **Repetition kept on purpose:** in the 4.2.12 design check both Astra and Grok kept the block's "An ideate drain delivers every task." (4.2.23 deleted task-completion.md's direct-work copy, rp-d8) as the always-loaded delivery boundary. SKILL.md's add-retry sentence stays on Grok's advice (Astra would have deleted it): package-format.md:120 states the same rule, but the add section never points there, so an add-only host that finds the copies gone could take a retry for a new loop.
- **Contents lists for long references (video review, 2026-10-12):** Anthropic's skill guidance gives a reference file over 100 lines a contents list and keeps references one level deep. `package-format.md` (127 lines) and `task-completion.md` (253) have none, but both are linked directly, and no trace shows a host stopping at line 100 and missing a rule (0237's partial read was fixed by moving the paragraph). Astra would try it as a measured candidate that replaces overview prose without adding tokens; Grok would not. Reopen only on such a trace.
- **Bounded defaults across engines:** rp-d3's real-model cross-host planning cases (display defaults proceed and enter task checks; persistent-state ambiguity or an unrequested interface stops) are unrun.
- **A loop with a started task, or one added in place of a legacy row, cannot be withdrawn**; failing a started task by name waits for the owner.
- **rp-d8:** `git add -f` on an experiment directory also adds ignored `__pycache__` — add the `.log` file alone.

## Standing rules

- **No token, cost or call budgets in the harness or in tests.**
  - Keep only the watchdogs: 90 min per task, 10 min per review, 600 s per judge seat.
  - Keep post-hoc usage recording. Missing usage is UNKNOWN, never 0.
  - Promotion criteria compare recorded usage; they are not budgets.
- **Models.**
  - Claude: `claude-opus-5-5`.
  - Codex: `gpt-6-astra` for design, review and judges, and `gpt-6-sol` for implementation.
  - `grok-4.7` is an optional reviewer only.
  - Do not auto-substitute Fable 5.2+.
- **Resolve and intent run only inside registered comparisons the owner approved.**
  - 0232's cells were approved on 2026-10-05.
  - Do not rerun D1. 0185 and D1–D4 are not holdout evidence.
- **Frozen material.**
  - A16, frozen results and the original WIP stay untouched.
  - The 0225–0229 raw roots in `/Users/Shared` were deleted on 2026-10-07 with the owner's approval; their results remain under `experiments/`.
  - Past stop verdicts (0211–0219, 0224, 0225) are history, not something to regrade.
  - Do not run a third 0225 replay or its live comparison, and do not publish its held candidate `22616b57`.
- **Replay apparatus gotchas (0225).**
  - Judge roots go outside `$HOME`: Claude loads every ancestor `.claude/CLAUDE.md`.
  - Codex judges need an isolated HOME (a shim), because `--ignore-user-config` still loads `$CODEX_HOME/AGENTS.md` and `~/.agents/skills`.
  - nvm Codex auto-updates silently, so pin a private install.
- **User-facing messages** are always in Korean, plain and short: the conclusion first, then what the user must decide, then the recommendation.
