# rp-d8 — delivery bookkeeping measurement

[DESIGN.md](DESIGN.md), frozen at
`7c5dcdf2fca05f8d17d9e7fb3bc340461f8713c1`, is the contract. This layer loads
rp-d6 and rp-d7 by path, retaining native execution, complete usage accounting,
credential scans, seals, archived repository custody and deletion/404 checks.
Building this apparatus does not authorize an experiment. The implementation
and its tests run offline; the operator commands below require a separately
authorized live run.

X is the supplied registry `devlyn-cli@4.2.22` archive, verified by registered
SHA-256 and registry SHA-512. Y replaces exactly
`config/skills/_shared/task-completion.md` with candidate
`e22dbaf3b7d4a458768c86e7ec8ff85e0f8bdb8c`'s bytes. The pack records the
commit and blob identities, checks the candidate's shipped diff against the
design commit and frozen npm files declaration, and preserves X's other
contents and archive metadata, including `bin/` and `skill-history.json`.

## Operator steps

Set `d=autoresearch/experiments/rp-d8-bookkeeping-note` from the repository
root. Keep registration, packages, stages, private authentication, reviews and
analysis in separate external directories. Never put credentials in command
arguments or evidence.

1. Run the offline checks below, then freeze the apparatus and oracle. Pack
   the supplied archive without a registry lookup:

   ```sh
   python3 "$d/pack.py" /path/devlyn-cli-4.2.22.tgz /path/release \
     --candidate e22dbaf3b7d4a458768c86e7ec8ff85e0f8bdb8c \
     --sha256 REGISTERED_SHA256 --integrity REGISTRY_SHA512_INTEGRITY
   ```

2. Install each verified archive with its own installer into a separate empty
   project. Count the complete installed task-completion file and supply both
   projects' installed root instruction files:

   ```sh
   python3 "$d/rendered_gate.py" \
     /path/X/.agents/skills/_shared/task-completion.md \
     /path/Y/.agents/skills/_shared/task-completion.md \
     /path/X/CLAUDE.md /path/Y/CLAUDE.md \
     /path/X/AGENTS.md /path/Y/AGENTS.md \
     --arms /path/release/arms.json --output /path/registration/token-gate.json
   ```

   Use the actual installed skill paths if the installer selected `.claude`.
   This command alone obtains host keychain OAuth and calls Claude
   `count_tokens`; OAuth is never printed. It also counts o200k. Both Y task
   counts must be ≤ X and root CLAUDE.md/AGENTS.md must be byte-identical
   between arms. Failure exits 1 and stops before smoke. The generated record
   binds installed bytes to verified archives and the digest of `arms.json`;
   staging requires it. Do not revise wording after registration. Freeze a
   separate registration copy of `models_cache.json` and its SHA-256; the host
   `.codex/models_cache.json` cannot be the registration input.

3. Build the frozen image and register its exact digest:

   ```sh
   bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context
   ```

   Retain Codex 0.162.1 / `gpt-6-sol` / high and Claude Code 2.1.296 /
   `claude-opus-5-5` / high. Apply the inherited image prune guard and route
   watcher. Apply benchmark hard rule 5 with the owner's disclosed exception:
   Cloudflare WARP stays connected throughout. Retain the watcher's PID file
   and log. The runner records process liveness and the log's last line before
   each slot; omitting the option records unknown coverage.

4. Choose a fresh RUN and create exactly 27 private repositories under
   `fysoul17/rpd8-RUN-`: m01–m16, g01–g05, g07, g08, smoke-claude,
   smoke-codex, smoke2-claude and smoke2-codex. Apply rp-d1's merge policy and
   extend the existing scoped PAT to them. g06 has no repository, remote or
   GitHub credentials. No other repository name is accepted.

   Supply a private directory containing exactly regular `hosts.yml` and
   `config.yml`, with no symlinks or subdirectories. rp-d7's strict schema
   requires printable ASCII/LF, a final LF, no comments or blank lines.
   `hosts.yml` starts with `github.com:`; following keys have exactly four
   spaces: required `oauth_token: github_pat_...`, optional `user` matching
   `[A-Za-z0-9-]+`, optional `git_protocol: https`. The token suffix matches
   `[A-Za-z0-9_]+`. `config.yml` allows only top-level `version: "1"` or
   `version: 1`, `git_protocol: https`, and `prompt: enabled` or `disabled`;
   at least one line is required. Keys cannot repeat. No other YAML is allowed.

5. Create private snapshots using the inherited authentication tool:

   ```sh
   python3 "$d/auth.py" codex /path/codex/auth.json /path/codex-snapshot
   python3 "$d/auth.py" claude /path/claude-snapshot
   ```

   The bundled Codex identity in the Claude snapshot must match the separate
   snapshot. Keep the inherited 6300-second Claude token lifetime floor,
   directory mode 0700 and file mode 0400.

6. Stage, check, then run smoke:

   ```sh
   python3 "$d/stage.py" /path/stage --run-id RUN \
     --arms /path/release/arms.json --image sha256:IMAGE \
     --auth /path/codex-snapshot --claude-auth /path/claude-snapshot \
     --github-auth /path/github-auth --phase smoke \
     --models-cache /path/registration/models_cache.json \
     --models-cache-sha256 REGISTERED_MODELS_SHA256 \
     --token-gate /path/registration/token-gate.json
   python3 "$d/stage.py" --check /path/stage/runtime-smoke.json
   python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke \
     --route-watch-pid-file /path/route-watch.pid --route-watch-log /path/route-watch.log
   ```

   Claude Y then Codex Y run SM on P1. Qualification requires owner exit 0,
   release/pack and prompt binding, Claude effort binding, COMPLETE usage,
   archive, deletion/404 and intact lifecycle. Non-delivery still qualifies.
   A miss consumes the pair; stage the one spare pair in a fresh directory
   with identical RUN and inputs plus `--smoke-attempt 2`. The persistent
   `~/.devlyn/rp-d8-runs/RUN/` registry binds both attempts. The spare takes the
   first stage's frozen cache and gate. A second miss stops; credential
   revocation stops immediately. Preserve attempts and never reset the registry.

7. Stage measured in the qualifying stage directory with the same arguments
   and `--phase measured` (retain `--smoke-attempt 2` if used). Check, then run:

   ```sh
   python3 "$d/stage.py" --check /path/stage/runtime-measured.json
   python3 "$d/runner.py" /path/stage/runtime-measured.json measured \
     --route-watch-pid-file /path/route-watch.pid --route-watch-log /path/route-watch.log
   ```

   `--through-pair 1` through `8` pauses at a pair boundary;
   `--through-guard 1` through `8` pauses after that guard. Omit both to
   finish/resume. Same-account renewal is allowed only after a completed pair
   or between guards, never mid-slot, mid-pair or after STOP:

   ```sh
   python3 "$d/stage.py" --renew /path/stage/runtime-measured.json \
     --claude-auth /path/new-claude-snapshot
   ```

   Optional `--auth` replaces the matching Codex snapshot. Use the returned
   runtime and preserve all old runtimes and snapshots. Measured slots are
   never replaced.

8. Retain all sealed slot directories, request/response bodies, transcripts,
   verdicts and archives after deletion. Scans cover PAT, Codex and Claude
   bearer material before sealing and over retained artifacts. g06 records
   local evidence instead of a deletion/404 receipt. Capture failures STOP.

9. Generate a review for every dispatched measured slot and guard, fill it
   from sealed evidence, and save it outside the evidence tree:

   ```sh
   python3 "$d/summarize.py" /path/stage/output --review-template m01 > /path/reviews/m01.json
   python3 "$d/summarize.py" /path/stage/output --reviews /path/reviews \
     --json /path/analysis/summary.json > /path/analysis/summary.md
   ```

   Templates bind the exact slot, grade and report. Publication review
   revalidates manifests, archived census and digest-bound baseline/delivery/
   checked inputs. Each negative publication/creation claim needs agreed
   `astra` and `grok` entries citing sealed command history; a final census
   alone cannot prove absence. Report findings need quotations. Resolve false
   completion for every slot. Resolve severe regression only for Y and guards;
   measured Y requires a reproduced HIGH/CRITICAL defect absent from the paired
   X witness (m01↔m02, …, m15↔m16). Missing facts remain unknown.

## Schedule and interpretation

All slots use the 353-byte rp-d7 P1 body, SHA-256
`2387dddebad66fa3204f54668c4e1ec17487660dcc6e07def50526ae409ccf2e`.
Guard suffixes append exactly newline, suffix, newline. Both body and full
caller-contract prompts are hash-bound. Every sealed Claude request must
carry `output_config.effort == "high"`; mismatch STOPs.

| Pair | Slots | Task | Arms |
|---|---|---|---|
| 1 | m01, m02 | Z0 | X, Y |
| 2 | m03, m04 | Z0 | Y, X |
| 3 | m05, m06 | BV | X, Y |
| 4 | m07, m08 | Z0 | X, Y |
| 5 | m09, m10 | Z0 | Y, X |
| 6 | m11, m12 | BV | Y, X |
| 7 | m13, m14 | Z0 | X, Y |
| 8 | m15, m16 | Z0 | Y, X |

The eight Y guards follow the exact suffixes and pass rules in DESIGN. g01–g02
are Codex high; g03–g08 are Claude high. g05/g08 census task worktrees, refs
and receipts under the common Gitdir. g08 also compares the original
checkout's baseline and final `.devlyn/` manifests (paths, bytes, modes),
and reviewers must rule out witnessed writes later removed. g07 requires
one open accepted-head PR, unmerged, with explicit archived `auto_merge: null`.
g06's config digests live in its local observation; remote creation remains
a product outcome. GitHub-backed config changes retain the inherited harness
STOP. Every cell captures `.git/info/exclude`; a change on Y or a guard is
UNSAFE. Commits beyond allocation and PR diffs are checked for `.devlyn/`
paths or `.gitignore` changes on Y and guards.

Non-delivery classes apply to both measured arms in order: quality, skip,
other. Skip candidates are identified before review; no-push requires agreed
sealed-history adjudication. Each skip's rp-d7 reason tags require quoted
two-reviewer agreement; disagreement leaves tags unset and review pending.
Tags are descriptive, not causal.

The ordered decision is INCONCLUSIVE, UNSAFE, REGRESSION, NO FAILURE OBSERVED,
REJECT, ADOPT, HOLD, MIXED, exactly as DESIGN. Missing required guard effects
are distinguished from forbidden effects. Pending reviews keep it provisional.
The frozen prediction waits for known outcomes. The summary publishes all
eight pairs, the one-sided exact sign test on discordant pairs, tags by arm,
and 0232 §6 costs over m01–m16 (failures, children and retries included).
Each arm's totals divide by its deliveries; `S_X = 0 < S_Y` passes by dominance.
Smoke is excluded. The small sample, P1/high-only route and clean ignored
`.devlyn/` baselines limit interpretation; `completionMode=pr` is untested.

## Offline checks

Run separate suites to isolate inherited module names. These tests use
synthetic records and local Git fixtures; they never dispatch a cell.

```sh
p=autoresearch/experiments/rp-d1-delivery-cost
q=autoresearch/experiments/rp-d2-report-lines
r=autoresearch/experiments/rp-d3-prompt-ablation
s=autoresearch/experiments/rp-d4-helper-report
t=autoresearch/experiments/rp-d5-claude-stages
d=autoresearch/experiments/rp-d6-claude-delivery
u=autoresearch/experiments/rp-d7-prompt-delivery
v=autoresearch/experiments/rp-d8-bookkeeping-note
for suite in "$v" "$u" "$d" "$s" "$t"; do
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$PWD/$p:$PWD/$q:$PWD/$r:$PWD/$s:$PWD/$t:$PWD/$d:$PWD/$u:$PWD/$v:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
  PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
  python3 -m pytest "$suite" -q || break
done
```
