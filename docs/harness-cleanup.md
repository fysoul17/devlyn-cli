# Legacy cleanup contract (CLI-4/5)

Once an app delivers a release to each session it starts (`docs/harness-activation.md`),
the copies earlier installs wrote are no longer read through that app. `cleanup` finds
them and removes only what it can prove devlyn-cli wrote.

```sh
devlyn cleanup --plan [--machine] [--project <abs>]… [--account-home <abs>]… --json
devlyn cleanup --apply --plan-file <abs> --digest <sha256> [--events] --json
```

The envelope, exit codes and `Reason` shape are activation's. `--plan` is read-only and
returns `{schemaVersion, version, inputs, scopes, digest}`: one `machine` scope (the
home's `.agents`, `.codex`, `.claude`, `.grok` skills and each account home's `skills`,
plus legacy commands) and one `project` scope per `--project`. Every item carries `id`,
`kind`, `path`, `relative`, `route` (`local`, or `delivery` when Git tracks it), `action`
(`remove`, `edit` or `skip`), `reasons` and its `before` preimage.

Removed: core skills byte-identical to a shipped copy and their renamed forms, retired
skills and standard copies, the install marker and `_shared` only when no devlyn skill stays
beside them, retired `.claude/commands` and files matching a shipped hash. Edited: the
retired Stop hook in `.claude/settings.json`, and an intact managed instruction block from an
earlier release, brought up to date with owner text around it kept byte-for-byte. A current
block is the team's principles and stays. Skipped, with a reason: modified copies
(`modified-copy`), optional add-ons (`optional-skill`), links out of the scope
(`outside-link`), occupied install locks (`occupied-lock`), roots a running process names
(`in-use`), a project with active queue tasks (`legacy-queue`) or an unreadable queue
(`queue-unreadable`), devlyn-cli's own repository (`source-repository`), the home folder as a
project (`home-folder`), tracked items without a remote (`no-remote`) and unreadable projects
(`project-unreadable`), unknown Git ownership (`repository-unreadable`), and
machine copies tracked by a home/dotfiles repository (`tracked-copy`). Local support
stays while a dependent copy remains on disk (`dependent-copy`), including copies
awaiting PR delivery.

`--apply` refuses a plan whose digest, inputs or version do not match (`stale-plan`, exit 3).
It plans again from disk and acts only on reviewed items the fresh plan still proves with
an unchanged preimage; anything else is reported, never forced. Each project's
`remote` records the reviewed GitHub repository and base branch, covered by the
digest. A changed delivery identity fails the scope as `stale-plan` before local
changes or allocation. Every item in the delivery worktree must match the reviewed
action and preimage before any item is changed. Local items are removed
under the user-root locks. Tracked items are delivered as one change per repository:
`_shared/task-complete.py` allocates a worktree from the remote base, the same proof runs
there, the commit `chore(devlyn): remove legacy devlyn-cli copies` is checked by a fresh
plan and completed by the repository's completion policy. A failed delivery releases its
worktree, branch and receipt.

The result is `{state: succeeded|partial|failed, scopes}`; each scope reports `state`
(`skipped`, `done`, `failed`), `delivery` (`{state: merged|pr-open, url}`) and `error`.
`--events` streams each scope's progress as one JSON line before the result. New codes:
`stale-plan`, `apply-failed`, `delivery-failed`, `auth-failed`, `requirement-missing`
(`{name}`), and the skip reasons above.

Tests: `python3 scripts/test-harness-cleanup.py`, with `TMPDIR` set to scratch.
