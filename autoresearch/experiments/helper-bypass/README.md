# Helper bypass: why merged PRs skip `task-complete.py` (2026-10-19 to 2026-10-27)

Read-only investigation requested by the owner on 2026-10-27. It was delegated to a Claude subagent and spot-checked by
root. The owner's repositories are private, so this record names no repository, session or person. The detailed
version stays on the owner's machine.

## Method

- **Repositories:** 24 of the owner's repositories carry the devlyn block or a `devlyn-completion/` folder.
- **PRs:** 713 PRs merged in the window. A PR counts as helper-delivered when a receipt's `pr_number` equals it. All
  433 helper-delivered PRs matched that way.
- **Transcripts:** 3,736 Claude Code and 2,881 Codex transcripts changed since 2026-10-17. Every `gh pr create`,
  `gh pr merge` and `task-complete.py` call was extracted with its output and tied to the PR URL or branch it named.
  That found the creation call for 244 of the 280 misses; the 36 without one are the 30 PRs from other accounts and 6
  owner PRs.

## Coverage

Twenty of the 24 repositories merged PRs in the window.

| repositories | merged | via helper | owner PRs to `main` via helper |
|---|---:|---:|---:|
| largest (release flow to staging/production) | 285 | 141 (49%) | 141/147 (96%) |
| second largest | 253 | 177 (70%) | 177/253 (70%; 97% without one long session) |
| 10 repositories with full coverage | 88 | 88 | 88/88 (100%) |
| 8 others | 87 | 27 | 27/54 (50%; 0–100% per repository) |
| **total** | **713** | **433 (61%)** | **433/542 (80%)** |

## Causes of the 280 misses

1. **Release PRs to non-default branches (141).** These are the owner's PRs to staging or production branches. The
   helper only delivers to the default branch. Leaving them out alone lifts total coverage to 76%.
2. **Other accounts (30).** Other people's accounts opened these PRs, so they are outside the helper's reach.
3. **Owner PRs to `main` delivered by hand (109).** The PR was opened and merged with manual `gh pr create` and
   `gh pr merge`. The scan classified where each branch came from:
   - 74 from a worktree made by hand with `git worktree add` and never allocated;
   - 8 from `checkout -b` or `switch -c` in a checkout;
   - 2 from a helper allocation that was later abandoned: one was refused after a reboot changed the device number,
     which devlyn-cli #278 has since fixed, and the other took a "manual route" to bundle a release;
   - 25 unclassified; spot checks found hand-made worktrees or `checkout -b`.

   One long design session opened 71 of these PRs, in the second-largest repository, and never called the helper. A
   regex flagged 60 misses as delegations to Codex or Astra worker lanes, with instructions such as "Claude commits;
   you make no git mutations"; 46 of them came from hand-made worktrees. The regex may miss some.

**Who made the misses:** every creation call found (244) was in a Claude Code main session; none was in a Codex
transcript.

**Not observed:** a missing or unresolvable helper, and the ideate drain.

## What makes hand-made worktrees look normal (cause 3)

- **devlyn-cli's own contract:** "`warm-build-dirs.py <worktree>` does the same for a worktree made without
  allocation" and "Unreceipted tasks remain owner-managed".
- **A downstream project's instructions:** a line in its `CLAUDE.md`/`AGENTS.md` says where to "make a worktree
  without allocation".
- **An outdated project memory note:** it says the helper refuses a dirty checkout, so `git worktree add -b` should be
  used instead. One session read the note and made a worktree by hand eight transcript lines later.
- **The no-adoption rule:** the helper refuses to adopt an existing branch or worktree. One session read that rule and
  then delivered by hand.

**Compaction:** in 12 misses, the agent had used the helper before a compaction and stopped using it afterwards. In
one session, every PR after the compaction was opened by hand, although the compaction summary still described the
helper.

## Could not determine

- Why three sessions never used the helper at all; their transcripts give no reasoning.
- Who created one PR, and how another was created.
- The exact number of misses that involved worker lanes; the regex flagged 60, and others may have been missed.

The extraction scripts and intermediate data stay private and are not committed. No product change follows from this
record alone; the next step is the owner's.
