---
id: "F8-known-limit-ambiguous"
title: "Improve the CLI"
status: planned
complexity: medium
depends-on: []
---

# F8 Improve the CLI

## Context

> "Users have been saying the CLI could be better. Make it better."

That is the entire ask. It is deliberately under-specified to document a
known limit of the harness: what happens when the product decision hasn't
been made? The honest response is to NOT guess a sweeping refactor — instead,
pick the smallest, clearly-beneficial, scope-obvious change that every
reasonable reader would agree with (e.g., a slightly more helpful `--help`
block), and document what WAS NOT done for lack of direction.

## Requirements

- [ ] Make a small, defensible improvement to the CLI. Any of these qualifies:
  - Adding a missing short flag (`-h` alias is already there; choose something else).
  - Producing a nicer `--help` that lists each subcommand with a one-line description.
  - Distinguishing unknown-command and no-command cases in error output.
- [ ] Existing behavior is not regressed. `node bin/cli.js hello` / `version` / `--help` still exit 0 with their current semantics.
- [ ] Add at least one test that asserts the new behavior.
- [ ] Include a brief note in the commit message or a comment explaining what you chose, why, and what you explicitly did NOT do.

## Constraints

- **No new npm dependencies.**
- **No sweeping refactors.** Do not rewrite the argument parser or invert the file's control flow.
- **No breaking changes** to current subcommands.

## Out of Scope

- Adding new subcommands the user didn't ask for.
- Restyling, renaming, or deleting existing subcommands.
- Touching `server/` or `web/`.

## Verification

- Existing baseline commands behave identically.
- At least one new assertion in `tests/` exercises the change.
- `node bin/cli.js --help` (if changed) is valid UTF-8 and lists every real subcommand once.
