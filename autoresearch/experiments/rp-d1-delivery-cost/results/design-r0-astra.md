Use a small prospective adapter around 0255, retaining its accounting, source selection and local-commit check. Add GitHub transport and a separate host-side delivery verdict. This follows **No overengineering** and **No workaround**: historical runners and accounting remain unchanged. Repository checked at `5f5459bc`; no files changed or live cells started.

1. **Repository topology**

   Create nine empty private repositories: `fysoul17/rpd1-<run-id>-smoke` and `…-o01` through `…-o08`. Use one repository per observation, with fresh cell/HOME each time. Seed only the current repository with its registered post-install baseline.

   Use one repository-specific PAT per repository. This prevents authenticated access to other observations through `gh repo list`, PR history or direct API calls. A shared repository retains history; a token selecting all nine permits cross-observation access.

   After each cell’s teardown and seal, archive using the **owner’s host authentication**: `git clone --mirror`, complete PR JSON, repository policy and observed refs. Verify archive completeness and hash it before deleting that repository. Retain private archives through results review; delete raw roots after reviewed results are recorded. This implements the gate’s repository-specific transport requirement. [Gate README:48](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d1-delivery-cost/README.md:48)

2. **Credential and injection**

   Owner creates nine fine-grained PATs in the web UI **after the repositories exist**, each selecting exactly one repository: Contents RW, Pull requests RW, Metadata R; one-day expiry, with its exact expiry recorded. Revoke each immediately after its cell finishes. No cell Administration, repository-deletion or workflow permission. Classic PATs are broader; a GitHub App adds unnecessary setup. [GitHub PAT documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

   Store each `hosts.yml` in a private directory **outside both the cell output and `runtime.auth`**. The latter permits exactly three existing model-auth files. Bind the GitHub directory read-only at `/run/github`; use:

   ```text
   GH_CONFIG_DIR=/run/github
   GH_PROMPT_DISABLED=1
   GIT_TERMINAL_PROMPT=0
   GIT_CONFIG_COUNT=2
   GIT_CONFIG_KEY_0=credential.helper
   GIT_CONFIG_VALUE_0=
   GIT_CONFIG_KEY_1=credential.https://github.com.helper
   GIT_CONFIG_VALUE_1=!/usr/local/bin/gh auth git-credential
   ```

   No `GH_TOKEN` environment variable. Enter PATs through private local input, never chat, shell arguments or registration files. Preserve `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1`, existing model-auth mounts and State-only Docker inspection. [0251/auth.py:148](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0251/auth.py:148), [0251/cell.py:30](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0251/cell.py:30), [0251/cell.py:65](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0251/cell.py:65)

   For Codex, explicitly set `shell_environment_policy.ignore_default_excludes=false`, then restore the exact nonsecret variables above through `[shell_environment_policy.set]`. **`GIT_CONFIG_KEY_*` also matches the secret-name filter**; `include_only` cannot restore excluded variables. Explicit configuration avoids depending on version-specific defaults. [Official OpenAI documentation](https://learn.chatgpt.com/docs/config-file/config-advanced#shell-environment-policy)

   The apparatus supplies this configuration before launch; the participant need not change Git configuration. Before sealing, scan collected files for the PAT bytes: a leak stops sealing/publication and yields UNKNOWN. Mount placement prevents automatic capture, not deliberate credential printing. Existing sealed roots are `run`, `cell`, `tmp`, `home`. [0233/run_cell.py:108](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/run_cell.py:108)

3. **Exact prompt**

   Replace the entire inherited common text and omit `local-delivery.txt`; append the existing `CALLER CONTRACT` JSON unchanged. The inherited prompt combines both prohibited restrictions. [0237/runner.py:70](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/runner.py:70), [0232/common.txt:1](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0232/common.txt:1)

   ```text
   Complete the development request in /harness/caller.json for this repository. Restrict source and test edits to its listed allowed paths, and preserve existing user files. Do not weaken existing tests or change caller.json. Run its public checks. Git's internal metadata writes needed for normal repository operations are allowed; do not change Git configuration, dependencies or installed tools. Do not look up upstream fixes. Network access is permitted only for model calls and this repository's existing GitHub origin and GitHub API. Do not print or copy authentication material. Finish with what you changed, what you verified and anything unresolved.
   ```

   No additional owner instructions, skill invocation or delivery hints.

4. **Product arm**

   Use **B**, containing the verified `devlyn-cli@4.2.18` release tarball extracted at `control/packages/B/package`. Freeze tarball SHA256 and registry integrity; never resolve `latest` again.

   Reuse `0233.install()` unchanged: offline container, package’s own installer, `-y --claude` for Claude and `-y` for Codex, then commit installed files into the baseline. [0233/prepare.py:28](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/prepare.py:28), [0233/prepare.py:53](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/prepare.py:53)

   Expected layout: Codex reads `AGENTS.md` and `.agents/skills`; Claude receives `CLAUDE.md` importing `AGENTS.md` and `.claude/skills`. Verify and hash actual tarball-produced files, including shared helpers; do not substitute current-checkout files. [bin/devlyn.js:98](/Users/aipalm/Documents/GitHub/devlyn-cli/bin/devlyn.js:98), [bin/devlyn.js:820](/Users/aipalm/Documents/GitHub/devlyn-cli/bin/devlyn.js:820), [bin/devlyn.js:843](/Users/aipalm/Documents/GitHub/devlyn-cli/bin/devlyn.js:843)

   The installed instructions lead to `_shared/task-completion.md`, which binds its own containing directory and `task-complete.py`. Leave `devlyn.completionMode` absent: default `auto` drives allocation, acceptance, publication and merge. [task-completion.md:41](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-completion.md:41), [task-complete.py:179](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-complete.py:179)

5. **Preparation and transport**

   Replace the low-level preparation function through the runner’s private `frame.prepare.prepare` binding. Reuse source materialization, installation, committed-tree extraction and CLI construction. Replace **0233’s whole origin setup block**, not merely `mirror()`: origin creation and fetch are separately hardcoded. Install the override before ancestor preparation performs its first seal/check. [0233/prepare.py:124](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/prepare.py:124), [0237/runner.py:150](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/runner.py:150)

   Host authority seeds registered `main`; cell origin becomes exactly:

   ```text
   https://github.com/fysoul17/<registered-observation-repository>.git
   ```

   Use fixed bootstrap commit dates to precompute registered source/install SHAs; participant commits use normal time.

   Replace `frame.harness_unchanged` with these invariants: exact single origin, identical literal/fetch/push URLs, unchanged local configuration and caller/roles hashes; reject additional remotes, includes, worktree configuration, `insteadOf`, `pushInsteadOf`, `sshCommand`, and foreign repositories. Permit objects, refs, remote-tracking refs and legitimate linked-worktree registrations to change. Remove mirror immutability and `origin/HEAD == allocation_sha`; the product fetches merged main and deletes its owned remote branch. [0233/run_cell.py:136](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/run_cell.py:136), [task-complete.py:588](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-complete.py:588), [task-complete.py:619](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-complete.py:619)

   This is a transport and observation-integrity contract, not an egress firewall. Fine-grained PATs still allow public reads; observed off-repository access fails the protocol. [GitHub PAT documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

6. **Image**

   Rebuild the complete 0232 image context. Its builder pins older CLIs, so update artifact pins to Claude **2.1.296** and Codex **0.162.1**, retaining node, py-tools, pyright and commander inputs. Freeze all downloaded artifact hashes. [0232/build.sh:12](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0232/build.sh:12), [0232/Dockerfile:3](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0232/Dockerfile:3)

   The only additional tool is **gh 2.83.2**, Linux arm64:

   ```text
   gh_2.83.2_linux_arm64.tar.gz
   SHA256 b1a0c0a0fcf18524e36996caddc92a062355ed014defc836203fe20fba75a38e
   ```

   Add `COPY`, checksum verification, extraction of `bin/gh` into `/usr/local/bin`, and tarball removal before `USER 501:501`. [Official release assets](https://github.com/cli/cli/releases/expanded_assets/v2.83.2)

   Verify CLI versions offline; register the resulting Docker image `.Id`, `sha256:…`, never its mutable tag. Existing validation already enforces that identity. [0237/runner.py:113](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/runner.py:113)

7. **Host done-check and snapshot**

   **Keep the inherited snapshot.** A direct accepted receipt identifies its source commit in the anchor object database; materialization does not require the removed worktree. The product’s recovery ref preserves reachability. Independently assess this source, then compare it with GitHub—not the reverse. [0233/locate.py:89](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/locate.py:89), [0233/locate.py:206](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/locate.py:206), [task-complete.py:583](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-complete.py:583)

   After teardown and seal, the new checker uses owner host `gh` and a separate mirror archive, never fetching into sealed participant Git storage. Require:

   - Exactly one matching PR: registered repository, same-repository head, accepted head SHA, base `main`, `MERGED`, nonempty `mergedAt` and merge SHA.
   - Merge commit reachable from archived `main`; its **Git tree OID equals the accepted source tree OID**, and its raw product tree equals the checked snapshot. Commit SHAs need not match.
   - Tracked user files outside scope unchanged, plus an ignored anchor sentinel unchanged byte-for-byte and by mode.
   - Final verification, merge, cleanup and reconciliation claims supported by checks, GitHub JSON, receipt custody and remaining resources.

   Retain the inherited local-commit checker as a necessary condition. Raw extraction avoids filters/export attributes; full tree-OID comparison complements `packet.tree`, which excludes `.git` and `.devlyn`. [0237/delivery.py:21](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/delivery.py:21), [0233/locate.py:39](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0233/locate.py:39), [0222/packet.py:19](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0222/packet.py:19)

   Freeze a claim-to-evidence checklist for results reviewers; do not keyword-grade prose. Truthful `CLEANUP_PENDING` is permissible, while missing or ambiguous reporting cannot pass. Subsequent research cleanup cannot repair a false participant claim. [task-completion.md:203](/Users/aipalm/Documents/GitHub/devlyn-cli/config/skills/_shared/task-completion.md:203)

8. **Accounting and outcomes**

   Implement `Runner.run()` as a wrapper around `super().run()`, preserving its verdict and writing a separate authoritative `rp-verdict`. Add GitHub/preservation/report checks only after inherited grading gates. This avoids copying accounting orchestration or modifying module-global `delivery.check`. [0255/runner.py:83](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0255/runner.py:83), [0255/runner.py:143](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0255/runner.py:143)

   Claude retains unchanged 0254/0255 receipt accounting; Codex retains the inherited trace path. Unsupported children, independent CLI launches, retry/error/interruption shapes or missing receipts remain UNKNOWN/STOP. No new accounting exception. [0254/README.md:15](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0254/README.md:15), [0238/runner.py:140](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0238/runner.py:140)

   Ordinary `task-complete.py`, `gh` and credential-helper commands do **not** match the launch recognizers; read-only synthetic checks confirmed this. Actual independent launches—or conservatively matched executable examples in assistant tool inputs—retain existing refusal behavior. No in-product reviewer is mandated here. [0234/diagnostics.py:45](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0234/diagnostics.py:45), [0242/policy.py:15](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0242/policy.py:15), [Gate README:40](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/rp-d1-delivery-cost/README.md:40)

   Conclusive delivery failure retains complete cost and becomes `PRODUCT_INCOMPLETE`; unavailable GitHub evidence becomes instrumentation STOP. Inherited accounting STOP means `NOT_ASSESSED`, not post-STOP grading. Stop the schedule, preserve the attempt, and mark remaining slots `NOT_RUN`. Count every dispatched attempt; any unknown usage makes aggregate token cost and cost-per-success UNKNOWN. Zero successes have no per-success denominator. [0255/README.md:35](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0255/README.md:35)

9. **Models and effort**

   | Engine | Owner and native-child default | Reason |
   |---|---|---|
   | Claude | `claude-opus-5-5`, `max` | Retains receipt-validated lineage. |
   | Codex | `gpt-6-sol`, `high` | Implements HANDOFF’s implementation-model rule; retains existing Sol worker effort. |

   This deliberately replaces historical Codex owner `gpt-6-astra/ultra`. Configuration and identity expectations are route-driven. Verify both native identities in smoke; never substitute models automatically. [0237/tasks.json:10](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/tasks.json:10), [0237/tasks.json:36](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/tasks.json:36), [0222/prepare.py:59](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0222/prepare.py:59), [HANDOFF.md:258](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/HANDOFF.md:258)

10. **Files, registration and tests**

    Add under `autoresearch/experiments/rp-d1-delivery-cost/`:

    | File | Responsibility |
    |---|---|
    | `runner.py` | 0255 subclass; prompt, input seals, evaluator, private hook bindings, final verdict wrapper. |
    | `prepare.py` | Prospective materializer and GitHub transport invariant. |
    | `cell.py` | 0251 lifecycle with only GitHub mount and pre-seal secret check additions. |
    | `github.py` | Host archive, merged-tree proof, preservation evidence and cleanup inventory. |
    | `Dockerfile`, `build.sh` | Rebuilt pinned context plus gh. |
    | `common.txt`, `tasks.json`, `fixtures/`, `oracle.py` | Prompt, two tasks, public tests and independent checks. |
    | `registration.json`, `test_apparatus.py` | Frozen contract/input identities and synthetic tests. |

    Concrete tasks: **BV**, `is_expired(now, deadline)` incorrectly uses `>` instead of `>=`; **Z0**, `--limit 0` incorrectly selects default `10`. Keep existing tests outside allowed edits; allow only the implementation and a new regression-test file. Oracle checks boundaries/default/zero/positive/error cases and verifies that the added regression fails against original source. Include tracked `docs/user-notes.txt` and ignored `.user-state/draft.txt`; this tests those preservation cases, not arbitrary dirty WIP. Existing scope/evaluator machinery remains applicable. [0234/check.py:74](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0234/check.py:74)

    Freeze this order:

    ```text
    o01 BV Claude r1    o02 BV Codex r1
    o03 Z0 Codex r1     o04 Z0 Claude r1
    o05 Z0 Claude r2    o06 Z0 Codex r2
    o07 BV Codex r2     o08 BV Claude r2
    ```

    Registration contains the HANDOFF prediction verbatim; schedule, source/check hashes, release and image identities, installed instruction hashes, bootstrap/start SHAs, routes, account identities, repository policy, credential scope/expiry metadata, accounting refusal rules and reporting checklist. Owner watchdog `5400s`; review/evaluator watchdog `600s`; no budgets. Preserve inherited startup catalogs, identity, quota, authentication and seal checks. [HANDOFF.md:220](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/HANDOFF.md:220), [0237/runner.py:196](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0237/runner.py:196)

    Offline tests use actual temporary Git repositories and fake `gh`: successful merge with different commit SHA/same tree; removed worktree; wrong tree/head/base/repository; unmerged PR; preserved and damaged sentinels; truthful/pending/false reports; legitimate ref changes versus retarget/config tampering; token exclusion; Codex environment restoration; UNKNOWN gate preservation; unchanged sealed files after archival. Run unchanged 0254/0255 suites alongside targeted apparatus review.

    **One separate live smoke is necessary:** one smoke repository, two serial owner sessions—one per engine—using unrelated tiny requests. Exercise real authentication, default PR/merge, cleanup, reconciliation and accounting. Record smoke expense separately; expose neither measurement task and perform no favorable replay. 0255 currently has only offline integration evidence. [0255/README.md:6](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/experiments/0255/README.md:6)

11. **Owner/implementer action order**

    Build and offline-test apparatus → owner-authenticated host creates nine empty private repositories and configures `main`/merge-commit policy without required reviews/checks → owner creates repository-specific PATs → privately provision credentials → run and archive the separate smoke → freeze measurement registration and obtain Astra ultra/Grok 4.7 reviews → reserve a quiet account window → execute eight serial slots.

    For each completed slot: teardown, seal, revoke its PAT, host archive/check, verify archive, delete repository. On STOP, perform the same resource cleanup and delete unused empty repositories/PATs. Review results while private raw evidence still exists, record reviewed results and hashes, then remove raw roots, credentials, containers, volumes, build-only images/cache and temporary contexts. Cleanup must use the recorded resource inventory, never broad Docker pruning. Registration/results review and watchdog requirements come from [HANDOFF.md:225](/Users/aipalm/Documents/GitHub/devlyn-cli/autoresearch/HANDOFF.md:225).

DESIGN: READY
