# rp-d1 delivery apparatus — design (r0, adopted 2026-10-13)

The owner approved building the delivery apparatus named in the [gate record](README.md).
This contract adopts [Astra's design](results/design-r0-astra.md) with the changes from
[Grok's review](results/design-r0-review-grok.md) listed below. Each of those two
sources cites the inherited code it relies on. Where they disagree, this file wins.

## Scope

- A prospective adapter around 0255: GitHub transport for the cell plus a separate
  host-side delivery verdict.
- 0254/0255 accounting is reused unchanged. Every historical runner and result
  stays untouched.
- There is no new accounting code. Unsupported shapes stay UNKNOWN/STOP.

## Adopted decisions

1. **Repositories.**
   - Nine empty private repositories under `fysoul17`, one smoke and o01–o08,
     named `rpd1-<run-id>-<slot>`. Each observation gets its own repository and
     a fresh cell and HOME.
   - Before seeding a repository, the host checks that it and every later
     repository are still empty: no refs and no PRs. If any is not, STOP.
   - After each slot's teardown and seal, the host uses the owner's host
     authentication to:
     1. archive the repository with `git clone --mirror`, the full PR JSON,
        the repository settings and the refs;
     2. hash the archive and check that it is complete;
     3. scan the archive for PAT bytes, then delete the repository and confirm
        it returns 404, including after a scan hit or failure;
     4. only then start the next slot.
2. **Credential: one fine-grained PAT (S1).**
   - The owner creates it once in the web UI after the nine repositories
     exist. It selects only those nine repositories, with permissions
     Contents RW, Pull requests RW and Metadata R, and a short expiry.
   - The owner deletes it after the run, or immediately after a token-byte hit.
   - It is stored in a private directory outside both the cell output and
     `runtime.auth`. That directory holds `hosts.yml` **and** `config.yml`
     (gh writes `config.yml` itself when it is absent).
   - The directory is bind-mounted read-only at `/run/github`.
   - The cell gets this environment, and no `GH_TOKEN`:
     ```text
     GH_CONFIG_DIR=/run/github
     GH_PROMPT_DISABLED=1
     GIT_TERMINAL_PROMPT=0
     GIT_CONFIG_COUNT=1
     GIT_CONFIG_KEY_0=credential.https://github.com.helper
     GIT_CONFIG_VALUE_0=!/usr/local/bin/gh auth git-credential
     ```
     The empty `credential.helper` reset is dropped, because global and system
     configuration are already disabled.
   - Codex config:
     - Keep exactly one project table whose only key is
       `trust_level = "trusted"`: `/work` during bootstrap, then `/cell/work`
       for launch (0237/runner.py:140-145, 0238/runner.py:76).
     - Keep `shell_snapshot = false`.
     - Add `[shell_environment_policy]` with `ignore_default_excludes = false`
       and a `[shell_environment_policy.set]` table that restores the variables
       above. `set` runs after the KEY/SECRET/TOKEN filter; `include_only`
       cannot restore excluded names.
   - Before sealing and after archiving, scan raw files and streamed Git object
     contents, including registered worktree storage and archive mirrors. A hit
     or scan failure makes the observation and usage UNKNOWN, requires PAT
     revocation and stops the schedule. Scan errors never record hit locations.
3. **Prompt (S2).**
   - Replace `0232/common.txt` and omit `0237/local-delivery.txt`.
   - Then append the inherited `CALLER CONTRACT` JSON unchanged.
   - There is no network, PR, delivery, helper or credential wording:
     ```text
     Complete the development request in /harness/caller.json for this repository. Restrict source and test edits to its listed allowed paths, and preserve existing user files. Do not weaken existing tests or change caller.json. Run its public checks. Git's internal metadata writes needed for normal repository operations are allowed; do not change Git configuration, dependencies or installed tools. Do not look up upstream fixes. Finish with what you changed, what you verified and anything unresolved.
     ```
4. **Product arm B.**
   - Use the verified `devlyn-cli@4.2.18` tarball (registry integrity and
     SHA-256 frozen) extracted at `control/packages/B/package`.
   - It is installed with the unchanged `0233.install()` (`-y --claude` or `-y`),
     and the installed files are committed into the baseline.
   - Record hashes of the files the tarball actually produced.
   - `devlyn.completionMode` stays absent, so the default `auto` mode applies.
5. **Transport.**
   - Replace 0233's whole origin block through the runner's
     `frame.prepare.prepare` binding. The host seeds `main` with fixed bootstrap
     commit dates. `origin` is exactly
     `https://github.com/fysoul17/<slot repo>.git`.
   - The new `harness_unchanged` requires:
     - one origin, with identical fetch and push URLs;
     - unchanged local configuration;
     - unchanged caller and roles hashes.
   - It rejects: extra remotes, includes, worktree config, `insteadOf`,
     `pushInsteadOf`, `sshCommand` and foreign anchor/worktree Git storage.
     GitHub done-check is the delivery authority; there is no filesystem-wide
     foreign-repository sweep.
   - It allows objects, refs, remote-tracking refs and worktree registrations
     to change.
6. **Image.**
   - Build a new minimal Dockerfile (`build.sh` + `Dockerfile`) from the 0232
     pins, keeping only what these two Python tasks need:
     - the pinned python base digest;
     - git, ca-certificates, xz-utils, procps, less;
     - node 22.23.2;
     - Claude Code 2.1.296 linux-arm64;
     - Codex 0.162.1 linux-arm64;
     - gh 2.83.2 linux-arm64 (`b1a0c0a0fcf18524e36996caddc92a062355ed014defc836203fe20fba75a38e`);
     - pytest 9.0.3;
     - uid 501 `participant`.
   - Pyright, commander and click tooling are dropped (subtractive).
   - Every artifact hash is frozen, and the image is registered by `.Id`.
7. **Host done-check (`github.py`).** It runs after teardown and seal, with the
   owner's host `gh` and a separate mirror archive. It never fetches into
   sealed participant Git storage. A slot passes only if all of these hold:
   - Exactly one PR: same repository, accepted head SHA, base `main`,
     `MERGED`, with `mergedAt` and a merge SHA.
   - The merge commit is reachable from archived `main`, and its Git tree OID
     equals the accepted source tree OID. A single tree-OID comparison is
     enough; the duplicate `packet.tree` comparison is dropped.
   - Tracked user files outside the allowed scope are unchanged.
   - The ignored sentinel `.user-state/draft.txt` is unchanged by bytes and
     mode.
   - The final report's verification, merge, cleanup and reconciliation
     claims are supported by checks, GitHub JSON, receipt custody and the
     resources that remain. A truthful `CLEANUP_PENDING` is a normal outcome
     here: as uid 501 with `--init`, `/proc/1` is unreadable, and
     `task-complete.py` keeps the worktree after merge.

   The inherited local-commit check stays a necessary condition. The snapshot
   is materialized from the receipt commit, which `refs/devlyn/completed/`
   keeps reachable.
8. **Verdicts.**
   - `Runner.run()` wraps `super().run()`, keeps its verdict, and writes a
     separate `rp-verdict` after the inherited gates.
   - A conclusive delivery failure is `PRODUCT_INCOMPLETE`, with its cost.
   - Unavailable GitHub evidence is an instrumentation STOP.
   - An inherited accounting STOP means `NOT_ASSESSED`; the schedule stops and
     the remaining slots are `NOT_RUN`.
9. **Models.**
   - Claude: `claude-opus-5-5` at `max`.
   - Codex: `gpt-6-sol` at `high`, following the HANDOFF implementation-model
     rule.
   - Native children use the owner's model.
   - Unused peer, judge and reviewer routes are omitted.
10. **Tasks.**
    - **BV:** `is_expired(now, deadline)` uses `>` where `>=` is correct.
    - **Z0:** `--limit 0` falls back to the default of 10.
    - Both are small Python packages with pytest public checks.
    - Allowed edits: the implementation file and one new regression-test file.
      Existing tests are outside the allowed paths.
    - The independent oracle checks boundary/default/zero/positive/error cases.
      It also confirms that the added regression test fails against the
      original source.
    - Participant exceptions within check rows fail those rows. Oracle-internal
      failures, including unavailable imports or replay environments, stay UNKNOWN.
    - Each fixture includes a tracked `docs/user-notes.txt` and an ignored
      `.user-state/draft.txt`.
11. **Order.**
    `o01 BV Claude, o02 BV Codex, o03 Z0 Codex, o04 Z0 Claude, o05 Z0 Claude, o06 Z0 Codex, o07 BV Codex, o08 BV Claude`.
    The owner watchdog is 5400 s and the evaluator watchdog 600 s. There are no
    budgets.
12. **Live smoke** (separate, before registration):
    - One smoke repository and two serial owner sessions, one per engine, on
      unrelated tiny requests.
    - It must show `git push`, `gh pr create` and `gh pr merge` working for
      both engines, along with accounting.
    - Its expense is recorded separately. Neither measurement task is exposed.

## Order of work

1. Build the apparatus and run its offline tests (fake `gh`, real temporary Git).
2. The host creates the nine repositories, with merge commits allowed and no
   required reviews or checks.
3. The owner creates the PAT.
4. Provision the credential privately.
5. Run the smoke, then archive and delete the smoke repository.
6. Freeze the registration and get reviews from Astra ultra and Grok 4.7.
7. Run the eight slots serially, cleaning up after each one.
8. Review the results against the raw data, then record them.
9. Remove the raw roots, the PAT, the containers, the volumes and the
   build-only image and context, using the recorded resource inventory and
   never a broad prune.
