I'll review the delivery path against DESIGN.md with full rigor, starting from the contract and the credential-handling code.Two HIGH defects block a live run. The inherited accounting, identity, and seal gates are still in force, and the transport, cleanup, and snapshot checks match `task-complete.py`.

**HIGH**

1. PAT (personal access token) bytes can land in the retained archive without the pre-seal scan seeing them. `cell.py:40-68` and `cell.py:92-94` only walk `out` and only compare raw bytes. A later host pull stores the full pull-request (PR) document, including `body` and `title`, at `archives/<slot>/repository.json` (`github.py:161-163`, `github.py:189`). `runner.py:156-173` archives only when `pat-scan.json` is absent, and it never scans that archive. `gh pr create --body-file /run/github/hosts.yml` (or a PR edit from that file) puts the token in the GitHub body. The command line and the tool result need not contain the bytes, and `task-complete.py:770-776` reuses an existing PR without replacing the body. The schedule then continues and does not set `revocation_required`. The same hole exists for a token that exists only inside a git object the scanner does not inflate (`git commit -F /run/github/hosts.yml`): `0233/run_cell.py:117-123` seals the compressed object, and the mirror copy is kept.

2. Codex is launched against a project it does not trust. `prepare.py:167` uses `codex exec -C /cell/work`. `0237/runner.py:144-145` rewrites trust to that cwd, and `0238/runner.py:76` does the same. `runner.py:79-81` then overwrites the file with `codex_toml()`, whose only project is `[projects."/work"]` (`prepare.py:35-39`). `/work` is not `/cell/work` and is not an ancestor of it. `test_apparatus.py:465-466` locks that end state in. Shell restoration itself is in that file (`shell_snapshot = false` and `[shell_environment_policy.set]` matches `GITHUB_ENV`); the same write undoes the cwd trust that the policy depends on. Claude is unaffected: it inherits `plan['env']` directly. Codex slots `o02`, `o03`, `o06`, and `o07` do not get a trusted `danger-full-access` project.

**MEDIUM**

3. `tasks.json:16-22`, `tasks.json:25-31`, `tasks.json:43-49`, and the Codex mirrors at `tasks.json:67-78` and `tasks.json:94-98` set `peer_routes.P`, `pair_judge`, and `reviewer` to the other engine. DESIGN.md §9 says native children use the owner's model. A child launched from those roles becomes an inherited accounting STOP, and the delivery is `NOT_ASSESSED`.

4. `test_apparatus.py:390-414` never builds a PR body, a git object, or an archive, so it stays green with finding 1. `test_apparatus.py:453-472` stubs `install`, so the fixed bootstrap date is not tied to `0233.install`'s real `git` binding.

**LOW**

5. A PAT hit is recorded as `status='STOP'` (`runner.py:183-186`), not UNKNOWN, which is what DESIGN.md §2 names. `usage` is UNKNOWN and `revocation_required` is set. An inherited auth refusal (exit 3, no verdict file) is relabeled `rp-d1 instrumentation failed: ValueError` (`runner.py:143-145`, `runner.py:178-180`).

6. `github.seed`'s returned SHA (`github.py:126`) is unused (`prepare.py:153`). Nothing larger can be removed without dropping a check.

Checked and holding: `task-complete.py:767` pushes a refspec and does not set upstream or rewrite config, so the config-hash transport check is not too strict for this product. Persisted `insteadOf`, `pushInsteadOf`, extra remotes, includes, and `sshCommand` are rejected (`prepare.py:78-91`). `/proc/1` makes `stopped_writers` raise, the worktree stays, and `github.py:341` records `CLEANUP_PENDING` without failing the slot. The snapshot is the receipt commit. `refs/devlyn/completed/` is updated before cleanup (`task-complete.py:321-324`) and checked at `github.py:227-229`. `account`, identity, and `seal_after_teardown` are wrapped, not replaced.

VERDICT: REVISE
