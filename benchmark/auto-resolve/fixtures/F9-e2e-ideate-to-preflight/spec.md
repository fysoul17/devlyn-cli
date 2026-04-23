---
id: "F9-e2e-ideate-to-preflight"
title: "End-to-end: idea → shipped CLI feature"
status: planned
complexity: high
depends-on: []
---

# F9 End-to-End Novice Flow

## Context

A first-time user has a vague idea:

> "I want a CLI subcommand that shows basic stats about the current git repo — commit count, last commit date, top 3 authors. Call it `gitstats`."

The variant arm is expected to use the pipeline: `/devlyn:ideate` to
produce a VISION/ROADMAP + spec, then `/devlyn:auto-resolve` to implement
per spec, then `/devlyn:preflight` to verify. The bare arm receives the
same idea as a direct prompt and implements it without the pipeline.

This fixture is the suite's most important gate for the "novice user contract":
a first-time user typing `/devlyn:ideate` should land at working, well-structured software.

## Requirements

- [ ] A new `gitstats` subcommand exists in `bin/cli.js`.
- [ ] `node bin/cli.js gitstats` (run inside a git repo) prints:
  - Line 1: commit count (e.g., `Commits: 42`).
  - Line 2: last commit ISO date (e.g., `Last commit: 2026-04-23T12:00:00Z`).
  - Lines 3-5: top 3 authors by commit count, format `<rank>. <name> <count>`.
- [ ] Run outside a git repo → stderr message `Error: not a git repository` and exit 2.
- [ ] `node bin/cli.js gitstats --json` emits valid JSON with the same data.
- [ ] Existing subcommands (`hello`, `version`) unchanged.
- [ ] Add at least one test.
- [ ] For variant: a `docs/VISION.md`, `docs/ROADMAP.md`, and a `docs/roadmap/phase-1/` spec file must exist after the run (evidence the ideate stage happened).

## Constraints

- **No new npm dependencies.** Use `child_process` to shell out to `git`.
- **No silent catches.**
- **Non-git-repo handling.** Do not assume the user is always in a repo.

## Out of Scope

- Parsing commit messages, tags, branches.
- Remote API calls.
- Touching `server/` or `web/`.

## Verification

- Inside this worktree (which IS a git repo): `node bin/cli.js gitstats` exits 0 and prints at least 5 lines of summary.
- `node bin/cli.js gitstats --json | node -e 'const d=JSON.parse(require("fs").readFileSync(0,"utf8")); console.log(typeof d.commits)'` prints `number`.
- `cd /tmp && node <worktree>/bin/cli.js gitstats` (from outside a repo — use the worktree's absolute path) exits 2.
- For variant: `test -f docs/VISION.md && test -f docs/ROADMAP.md && ls docs/roadmap/phase-1/*.md | head -1`.
- `node --test tests/` passes.
