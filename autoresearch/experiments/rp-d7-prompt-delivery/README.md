# rp-d7 — Claude high delivery with P1

[DESIGN.md](DESIGN.md) is frozen. This thin layer loads rp-d6 by path and
keeps its native lifecycle, accounting, installed-instruction checks, PAT and
model credential scans, seals, archive custody, repository deletion and 404
confirmation. All six possible slots install the unchanged, verified registry
`devlyn-cli@4.2.22` X archive. There is no candidate, Y arm or token gate.
Building and testing the apparatus does not authorize a live experiment.

P1 is derived from rp-d1 `common.txt` using the two exact registered
replacements, each occurring once. Both source and result hashes are checked;
the result is 353 bytes including its trailing newline. The plan, baseline,
prompt file and argv bind P1 and the unchanged caller contract. The installed
AGENTS.md managed block and runtime-principles binding is rp-d6's. CLAUDE.md
must equal its verified X managed block or the installer's exact 11-byte
`@AGENTS.md` import with a trailing newline.
The binding runs before launch and prompt bytes are checked again after sealing.

| Slot | Task | Engine / model / effort | Arm |
|---|---|---|---|
| m01 | BV | Claude Code 2.1.296 / claude-opus-5-5 / high | X |
| m02 | Z0 | Claude Code 2.1.296 / claude-opus-5-5 / high | X |
| m03 | BV | Claude Code 2.1.296 / claude-opus-5-5 / high | X |
| m04 | Z0 | Claude Code 2.1.296 / claude-opus-5-5 / high | X |

Smoke is one `smoke-claude` SM cell; its single spare is `smoke2-claude`.
Every slot uses P1 and the per-slot high override of the inherited max pin.
Every sealed API request must carry `output_config.effort == "high"` or STOP.
No Codex cell or guard can dispatch.

## Operator steps

These commands document a separately authorized live run. Offline checks do
not run them. Set `d=autoresearch/experiments/rp-d7-prompt-delivery` from the
repository root. Keep registration, releases, stages, private authentication
and review output in separate external directories. Never place credential
values in arguments or evidence.

1. Run the offline checks below. Freeze the apparatus and oracle. Materialize
   the supplied registry archive using the registered SHA-256 and registry
   SHA-512 integrity; no registry lookup occurs in the packer:

   ```sh
   python3 "$d/pack.py" /path/devlyn-cli-4.2.22.tgz /path/release \
     --sha256 REGISTERED_SHA256 --integrity REGISTRY_SHA512_INTEGRITY
   ```

   Freeze a registration copy of `models_cache.json` and its SHA-256.
   Staging refuses the host `.codex/models_cache.json` as a registration source.

2. Build one image from the frozen rp-d1 definition and register its digest:

   ```sh
   bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context
   ```

   Use that exact digest throughout. Apply the inherited image prune guard
   and route watcher, retaining default-route changes. Apply benchmark hard
   rule 5 with the owner's disclosed exception: Cloudflare WARP stays
   connected. Keep the same network condition for all slots.

3. Choose a fresh RUN ID. Provision six private repositories:
   `fysoul17/rpd7-RUN-m01` through `m04`,
   `fysoul17/rpd7-RUN-smoke-claude`, and
   `fysoul17/rpd7-RUN-smoke2-claude`. Apply rp-d1's merge policy and extend
   the existing scoped PAT to all six. Store read-only `hosts.yml` and
   `config.yml` in a separate private authentication directory.
   Before mounting, rp-d7 requires exactly those two regular files, with no
   symlinks or subdirectories, and exactly one fine-grained `github_pat_`
   credential in hosts.yml. Extra tokens or credential keys in either file fail.
   Use literal YAML with simple keys; escapes, tags, anchors and aliases are rejected.

4. Create the inherited private snapshots:

   ```sh
   python3 "$d/auth.py" codex /path/codex/auth.json /path/codex-snapshot
   python3 "$d/auth.py" claude /path/claude-snapshot
   ```

   **Transport-only Codex dependency:** rp-d6's Claude snapshot still contains
   `codex.json`. `0251/auth.py` requires it in the exact snapshot/manifest;
   `0251/cell.py` unconditionally mounts it; rp-d4 auth validates its OAuth
   identity and rp-d4's pre-seal scan scans its tokens. Removing it would
   change the inherited launcher, authentication and credential-scan contract.
   This layer therefore retains that bundled identity and rp-d6's separate
   matching Codex snapshot bookkeeping. No Codex CLI request/cell runs.
   Claude uses one account, with the unchanged **6300-second** remaining
   token lifetime floor. Snapshot directories are 0700 and files 0400.

5. Stage, check and run smoke:

   ```sh
   python3 "$d/stage.py" /path/stage --run-id RUN \
     --arms /path/release/arms.json --image sha256:IMAGE \
     --auth /path/codex-snapshot --claude-auth /path/claude-snapshot \
     --github-auth /path/github-auth --phase smoke \
     --models-cache /path/registration/models_cache.json \
     --models-cache-sha256 REGISTERED_MODELS_SHA256
   python3 "$d/stage.py" --check /path/stage/runtime-smoke.json
   python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke
   ```

   Qualification requires owner exit 0, release/P1/effort binding, COMPLETE
   usage, archive, deletion/404 and intact lifecycle. Non-delivery qualifies.
   A miss consumes the attempt. Stage the spare in a new directory with the
   same inputs and RUN, adding `--smoke-attempt 2`. It takes the cache from
   the first stage, and `~/.devlyn/rp-d7-runs/RUN/` binds both attempts.
   A second miss stops; credential revocation stops immediately. Preserve
   every attempt and never reset the registry to retry.

6. Stage measured in the qualifying stage directory with the same command
   and `--phase measured`, preserving `--smoke-attempt 2` if applicable:

   ```sh
   python3 "$d/stage.py" --check /path/stage/runtime-measured.json
   python3 "$d/runner.py" /path/stage/runtime-measured.json measured --through-slot 1
   ```

   `--through-slot 1` through `4` pauses at that measured boundary; omit it
   to finish/resume. Measured slots are never replaced. Same-account renewal
   is allowed only between completed measured slots, never mid-slot or after
   STOP:

   ```sh
   python3 "$d/stage.py" --renew /path/stage/runtime-measured.json \
     --claude-auth /path/new-claude-snapshot
   ```

   Use the printed new runtime for subsequent slots; preserve old runtimes
   and snapshots. Optional `--auth` replaces matching transport bookkeeping.

7. Retain all sealed slot evidence, request/response bodies, native
   transcripts, verdicts, archives, registration and runtimes after deletion.
   Inherited PAT, Codex transport and Claude bearer scans run before sealing
   and over retained archive/verdict artifacts. A scan failure stops and
   requires credential revocation.

8. Produce a review template for each dispatched measured slot, fill it from
   sealed evidence, and persist it outside the evidence tree:

   ```sh
   python3 "$d/summarize.py" /path/stage/output --review-template m01 > /path/reviews/m01.json
   python3 "$d/summarize.py" /path/stage/output --reviews /path/reviews \
     --json /path/analysis/summary.json > /path/analysis/summary.md
   ```

   Reviews bind the exact slot, grade and report. False completion needs a
   resolved value and evidence, plus a report quote when true; an unresolved
   value remains unknown and makes the ordered decision INCONCLUSIVE. A mechanical finding
   cannot be erased. Skip candidates require independent `astra` and `grok`
   publication entries. Each no-push claim cites an exact path from sealed
   `history_evidence`, and reviewers inspect all transcripts/requests and the
   archived census. Review application revalidates record-bound manifests,
   their listed files and the archive, then recomputes publication facts.
   Mutations fail explicitly. Missing evidence, incomplete parses and disagreements leave
   publication unknown. Final census absence alone never proves no push.
   Each skip's reason tags use report-substring quotes; disagreement leaves
   the agreed set unset and is published. Any non-empty subset of the tag
   vocabulary is valid, including `none` alongside other applicable tags.
   Severe-regression adjudication is
   removed because this unchanged-product decision does not use it.

Non-delivery classification checks quality first, without a count prerequisite.
Skip requires an integer local commit count, zero PRs, no positive grader push
finding and a review-established no-push finding. Other requires a witnessed
push, merge or positive integer PR count, without requiring both counts.
Only unmatched outcomes remain unset. The ordered decision is INCONCLUSIVE, UNSAFE, NO SKIP OBSERVED,
SKIPS PERSIST, MIXED. Pending reviews are provisional. Costs include failed
measured slots, native children and retries; smoke is excluded. The summary
reads rp-d6's retained X result for description and computes the one-sided
hypergeometric Fisher probability. That earlier run is not a contemporaneous
control, and stated reason tags do not establish causation.
Prediction support waits for every measured outcome and skip tag set to be
known; an established counterexample can disprove it before completion.

## Offline checks

Synthetic fixtures prohibit subprocess/network calls in rp-d7. Inherited
suites also use local Git fixtures; no live service or experiment cell is used.
Run directories separately to isolate inherited test module names:

```sh
d=autoresearch/experiments/rp-d6-claude-delivery
u=autoresearch/experiments/rp-d7-prompt-delivery
p=autoresearch/experiments/rp-d1-delivery-cost
q=autoresearch/experiments/rp-d2-report-lines
r=autoresearch/experiments/rp-d3-prompt-ablation
s=autoresearch/experiments/rp-d4-helper-report
t=autoresearch/experiments/rp-d5-claude-stages
for suite in "$u" "$d" "$s" "$t"; do
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$PWD/$p:$PWD/$q:$PWD/$r:$PWD/$s:$PWD/$t:$PWD/$d:$PWD/$u:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
  PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
  python3 -m pytest "$suite" -q || break
done
```
