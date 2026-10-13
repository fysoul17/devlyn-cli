I'll review the design against the brief and the cited repository files, then judge S1 and S2. No edits.The design and brief are in. Next I’ll check the cited lines and the inherited delivery path those claims depend on.The design matches the inherited delivery and accounting path. No HIGH findings. Adopt S1 and S2.

**MEDIUM**

- The replacement materializer must leave the Codex config with exactly one `[projects."/work"]` entry whose only key is `trust_level = "trusted"`. `0237/runner.py:140-145` rejects anything else before launch. Add `shell_environment_policy` beside that table, and keep `shell_snapshot = false` from `0222/prepare.py:62`. With the snapshot enabled, that policy does not apply to the shell Codex actually runs.
- Seed both `hosts.yml` and `config.yml` under the read-only `/run/github` mount. `gh` creates `config.yml` when it is absent. The required smoke has to show `git push`, `gh pr create`, and `gh pr merge` for both engines. On a clean PR, gh 2.83.2 merges immediately when `--auto` is passed (`autoMerge` is set only when the PR is not already mergeable), so the owner does not need a separate auto-merge repository setting when there are no required checks.
- Treat `CLEANUP_PENDING` as the normal merged outcome. The cell runs as uid 501 with `--init` and `--cap-drop ALL`, and `stopped_writers` (`task-complete.py:469-493`) keeps the worktree when `/proc/1` is unreadable. The merge has already landed (`task-complete.py:806-810`). The receipt commit stays reachable through `refs/devlyn/completed/` (`task-complete.py:324` and `:585`), and `0233/locate.py:100-103` plus `:211` materialize that commit without the worktree.

**LOW**

- `task-complete.py:619` is the remote-URL check. The branch delete is `:625`. `task-completion.md:203` is the report split. `CLEANUP_PENDING` is `:129` and `:216`. `--env-file` is `0251/cell.py:45`. `:65` is the State-only inspect.
- The second snapshot comparison duplicates the Git tree-OID check. `0222/packet.py:19-24` only drops `.git` and `.devlyn`, which are already untracked. The empty `credential.helper` entry is unused while `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1`.

Checked and holding: one direct receipt survives worktree removal. `0234/diagnostics.py:47-64` and `0242/policy.py:15-41` do not treat `task-complete.py`, `gh`, or the credential helper as launches. The Claude path is `0255/runner.py:83-160`. The Codex path is `0238/runner.py:140` via `super().run()`. The image pins are linux-arm64 (`0232/build.sh:12-14`, `Dockerfile:3` and `:25`). `0251/auth.py:148` allows only the three model-auth files. Codex `set` runs after the KEY/SECRET/TOKEN filter, so it can restore `GIT_CONFIG_KEY_*`. `include_only` cannot.

**S1.** It preserves the isolation this measurement needs. At observation k the token can still call the other selected repositories, but past repositories are gone and future ones are empty, so there is no prior solution or PR to read. Contents RW and Pull requests RW can write only refs and PRs, and Metadata is read-only. The pre-check stops the schedule on those writes, so a later slot is `NOT_RUN` rather than graded on planted content.

Residuals to write into the procedure: check the target empty before seeding it, and check every later repository empty. Confirm each deleted repository, including smoke, returns 404 before the next cell. On a token-byte hit, revoke the PAT and stop. Do not wait until the end of the run. `gh repo list` still shows the remaining opaque repository names.

**S2.** Better. Those two sentences are the prompt's delivery and credential hints. HANDOFF step 4 and the brief forbid teaching that. The replacement prompt already drops `0232/common.txt`'s network ban and `0237/local-delivery.txt`. Delivery still comes from the installed `task-completion.md` under bypassPermissions and `danger-full-access`. Codex web search stays off (`0222/prepare.py:61`). "Do not look up upstream fixes" stays. The seal scan is the leak control.

VERDICT: SHIP
