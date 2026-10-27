# Legacy cleanup contract (CLI-4/5)

Once an app delivers a release to each session it starts (`docs/harness-activation.md`),
the copies earlier installs wrote are no longer read through that app. `cleanup` finds
them and removes only what it can prove devlyn-cli wrote.

```sh
devlyn cleanup --plan [--machine] [--project <abs>]… [--account-home <abs>]… --json
devlyn cleanup --apply --plan-file <abs> --digest <sha256> [--include <item-id>]… [--events] --json
```

The envelope, exit codes and `Reason` shape are activation's. `--plan`
returns `{schemaVersion, version, inputs, scopes, digest}`: one `machine` scope (the
home's `.agents`, `.codex`, `.claude`, `.grok` skills and each account home's `skills`,
plus legacy commands) and one `project` scope per `--project`. Every item carries `id`,
`kind`, `path`, `relative`, `route` (`local`, or `delivery` when Git tracks it), `action`
(`remove`, `edit` or `skip`), `reasons` and its `before` preimage.

For a project with a remote and tracked items to remove or edit, `--plan` first attempts
the same base-branch fast-forward described below. After all attempts, if any HEAD moved,
all scopes are planned again so the review covers the bytes delivery acts on. Anything else is planned
as it stands, including another branch, a refused fast-forward or a failed fetch. The fetch
is non-interactive and times out after 30 seconds; failure does not fail the plan.

Removed: core skills byte-identical to a shipped copy and their renamed forms, retired
skills and standard copies, the install marker and `_shared` only when no devlyn skill stays
beside them, retired `.claude/commands` and files matching a shipped hash. Edited: the
retired Stop hook in `.claude/settings.json`, and an intact managed instruction block from an
earlier release, brought up to date with owner text around it kept byte-for-byte. A current
block is the team's principles and stays. Skipped, with a reason: modified copies
(`modified-copy`), optional add-ons (`optional-skill`), links out of the scope or through
another link (`outside-link`), occupied install locks (`occupied-lock`), roots a running process names
(`in-use`), a project with active queue tasks (`legacy-queue`) or an unreadable queue
(`queue-unreadable`), devlyn-cli's own repository (`source-repository`), the home folder as a
project (`home-folder`), tracked items without a remote (`no-remote`) and unreadable projects
(`project-unreadable`), unknown Git ownership (`repository-unreadable`), and
machine copies tracked by a home/dotfiles repository (`tracked-copy`). Local support
stays while a dependent copy remains on disk (`dependent-copy`), including copies
awaiting PR delivery.
Skill-root links directly into their scope are classified once at the real path; cleanup itself
never removes the links or their target directory. Git may prune an empty target during checkout.

`--apply` refuses a plan whose digest, inputs or version do not match (`stale-plan`, exit 3).
It plans again from disk and acts only on reviewed items the fresh plan still proves with
an unchanged preimage; anything else is reported, never forced. Repeatable `--include` chooses
reviewed skips whose sole reason is `modified-copy`, excluding support, with the same fresh proof;
kept support stays until a later plan, and the digest still covers only the plan. Each project's
`remote` records the reviewed GitHub repository and base branch, covered by the
digest. A changed delivery identity fails the scope as `stale-plan` before local
changes or allocation. Every item in the delivery worktree must match the reviewed
action and preimage before any item is changed. Local items are removed
under the user-root locks. Tracked items are delivered as one change per repository:
`_shared/task-complete.py` allocates a worktree from the remote base, the same proof runs
there, the commit `chore(devlyn): remove legacy devlyn-cli copies` is checked by a fresh
plan and completed by the repository's completion policy. A failed delivery releases its
worktree, branch and receipt. A reviewed item with no counterpart in the base's fresh plan
passes only when the base changed its content or removed it in every spelling, and the checkout
holds it, under its tracked spelling, unchanged since the fork point. With every item so settled,
nothing is delivered. A fresh counterpart with different bytes still fails as `stale-plan`;
before reporting that refusal and its detail, a checkout strictly behind the base takes the base
so the next plan reviews its bytes. On a stale delivery, a checkout not behind stays untouched. After a merged
delivery, or when every item is already settled, the checkout also takes the base. A checkout on the
base branch is fast-forwarded to the base (fetched into a ref the call owns, merged by commit
without autostash or overwriting ignored files); another branch, or a
fast-forward Git refuses, fails the scope as `update-checkout` and is left as it is.

The result is `{state: succeeded|partial|failed, scopes}`; each scope reports `state`
(`skipped`, `done`, `failed`), `delivery` (`{state: merged|pr-open, url}`) and `error`.
`--events` streams each scope's progress as one JSON line before the result. New codes:
`stale-plan`, `apply-failed`, `delivery-failed`, `auth-failed`, `update-checkout`,
`requirement-missing` (`{name}`), and the skip reasons above.

Tests: `python3 scripts/test-harness-cleanup.py`, with `TMPDIR` set to scratch.

## Devlyn AI OS history

Cleanup also recognizes the frozen private `agent-devlyn-v1` generation. The public
manifest contains hashes, never its template text. Command discovery covers
`.claude/commands`, `.agent/workflows`, `.gemini/commands` and `.cursor/rules`;
ownership still requires a known content hash. The earliest CLI also wrote Gemini
commands; later provider registries listed Gemini and Cursor as coming soon.
The desktop wizard's `devlyn-spec`, `devlyn-plan` and `devlyn-implement` commands
are included. After the 2026-01-13 CLI removal, `src/prompts/*.md` was embedded
into the worker/Rust build rather than installed as project slash commands.

The three Jarvis scripts (`post-to-jarvis.sh`, `post-to-jarvis.mjs`,
`hook-to-file.mjs`) are fingerprinted from evaluated historical CLI, desktop and
worker generators at their default ports. Their settings entries require a
historical event, matcher and complete hook object. Owner entries and wrapper keys
stay byte-for-byte through JSON syntax-tree edits, including large numbers, escapes,
line endings and duplicate owner keys. Both Jarvis and retired Stop-hook cleanup remove event
keys and the `hooks` key only when cleanup emptied them; pre-existing empty containers stay.
If that leaves an empty document, the same `settings-entry` / `edit` item deletes the file,
with its reviewed preimage and local/delivery route unchanged. Ambiguous duplicate hook paths are refused.
A script with unknown remaining references (including `settings.local.json`), unsafe settings or a different
tracking route from its settings stays as `dependent-copy`. Selecting an edited
script with `--include` also selects its reviewed settings preimage; a narrowed or
stale pair is refused together. Local write failures restore staged scripts.
Non-default ports and per-project placeholder substitutions without exact shipped
hashes stay reviewable modified copies. Project data/configuration is not retired
by this evidence: `.gitignore`, `devlyn.config.json`, `specs/`, `logs/`, `trees/`,
`tasks.md` and `.ports.env` stay.

To re-derive the frozen seed from a full local private checkout, then verify the
combined public history (Node 22):

```sh
node scripts/update-cleanup-ai-os-history.js /path/to/agent-devlyn-v1 --check
node scripts/update-cleanup-history.js --check
```

Omit `--check` to regenerate. The seed pins revision
`d251b04141134589fb811dd5a0f2e99feef701e1` and traverses all its ancestors; it reads
Git blobs, never local installed copies. Public CI consumes
`scripts/cleanup-ai-os-history.json` and needs no private repository access.
