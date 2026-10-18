# rp-d6 — Claude default delivery at high effort

[DESIGN.md](DESIGN.md) is frozen. This apparatus loads
[rp-d4](../rp-d4-helper-report/) and [rp-d5](../rp-d5-claude-stages/) by path,
retaining their inherited native lifecycle, accounting, credential scans,
seals, archive custody and deletion confirmation. Building and testing these
files does not authorize a live experiment. This implementation session ran
only offline tests and did not commit or dispatch any experiment cell.

X is the supplied registry `devlyn-cli@4.2.22` archive, checked against both
the registered SHA-256 and registry SHA-512 integrity. Y replaces exactly
`CLAUDE.md`, `AGENTS.md` and `config/skills/_shared/runtime-principles.md`
with bytes from the supplied candidate commit. The pack preserves all other
archive contents, file modes, metadata and member order; it records candidate
commit/blob identities and verifies both extracted trees.

The explicit three-path request resolves a discrepancy in DESIGN's Y-path
paragraph: candidate `15ded3a7e2d7ca6d46f366bdd63b7ac9c4e1da91` does not change
`bin/instruction-templates.json`, and its `.agents` mirror is not shipped.
Those paths remain untouched in the pack. DESIGN and `rendered_gate.py`
remain unchanged.

## Operator steps

From the repository root set `d=autoresearch/experiments/rp-d6-claude-delivery`.
Use separate external directories for registration, releases, stages, private
authentication and retained evidence. Never place credential values in
arguments, runtime files, reports or the repository. The commands below are
instructions for a separately authorized run, not actions performed by tests.

1. Run the offline checks below. Freeze the apparatus, oracle, image digest
   and candidate before registration. Pack using supplied registry values:

   ```sh
   python3 "$d/pack.py" /path/devlyn-cli-4.2.22.tgz /path/release \
     --candidate 15ded3a7e2d7ca6d46f366bdd63b7ac9c4e1da91 \
     --sha256 REGISTERED_SHA256 --integrity REGISTRY_SHA512_INTEGRITY
   ```

2. Install each verified archive into a separate empty project with its own
   installer. Run the unchanged rendered-block gate on the resulting complete
   instruction files, including the precedence line and digest marker:

   ```sh
   python3 "$d/rendered_gate.py" /path/X/CLAUDE.md /path/Y/CLAUDE.md \
     /path/X/AGENTS.md /path/Y/AGENTS.md > /path/registration/counts.json
   ```

   This counting step uses the existing authenticated counting service; it is
   not an offline test. Preserve a registration JSON with `arms_sha256` equal
   to the digest of the verified `arms.json`, and the `rows` and `passed`
   fields from `counts.json`. Supply that file as `--token-gate`. Both engines'
   counts must be no greater for Y. A failure stops before smoke. Freeze a
   separate `models_cache.json` in registration and record its SHA-256.

3. Build the inherited pinned image:

   ```sh
   bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context
   ```

   Reuse one exact image digest, Codex 0.162.1 / `gpt-6-sol` / `high`, and
   Claude Code 2.1.296 / `claude-opus-5-5`. Apply the inherited image prune
   guard and route watcher. Apply benchmark hard rule 5 with the owner's
   disclosed exception: Cloudflare WARP stays connected. Do not substitute
   a different network condition between slots.

4. Choose a fresh run ID. Provision private repositories named
   `fysoul17/rpd6-RUN-m01` through `m08`, `g01` through `g05`,
   `smoke-claude`, `smoke-codex`, `smoke2-claude` and `smoke2-codex`
   (17 total, each with the same `rpd6-RUN-` prefix). Apply rp-d1's merge
   policy and extend the existing scoped PAT to these repositories. Put the
   private read-only `hosts.yml` and `config.yml` in a separate authentication
   directory. **g06 has no GitHub repository and no configured remote.**

5. Create the inherited private model snapshots:

   ```sh
   python3 "$d/auth.py" codex /path/codex/auth.json /path/codex-snapshot
   python3 "$d/auth.py" claude /path/claude-snapshot
   ```

   The bundled Codex account must match the separate Codex snapshot. Claude's
   remaining lifetime must meet the inherited **6300-second** floor before
   dispatch. Snapshot directories use mode 0700 and files 0400. No snapshot
   content belongs in output or evidence directories.

6. Stage the initial smoke against the registration inputs:

   ```sh
   python3 "$d/stage.py" /path/stage --run-id RUN \
     --arms /path/release/arms.json --image sha256:IMAGE \
     --auth /path/codex-snapshot --claude-auth /path/claude-snapshot \
     --github-auth /path/github-auth --phase smoke \
     --models-cache /path/registration/models_cache.json \
     --models-cache-sha256 REGISTERED_MODELS_SHA256 \
     --token-gate /path/registration/token-gate.json
   python3 "$d/stage.py" --check /path/stage/runtime-smoke.json
   python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke
   ```

   Smoke runs Claude high Y then Codex high Y, both on SM. It requires owner
   exit 0, package/release binding, Claude request effort binding, COMPLETE
   usage, an archive, deletion and confirmed 404. **Non-delivery still
   qualifies** and remains recorded. No report-style or stage-count gate is
   added. Preserve every attempt.

   A miss consumes the first pair. Stage a new directory with the same run
   ID and inputs and `--smoke-attempt 2` for the single spare pair. The spare
   takes its models cache from the first registered stage copy; it never
   consults the host cache. The persistent `~/.devlyn/rp-d6-runs/RUN/`
   registry binds both attempts across stage directories. Failed spare stops;
   credential revocation stops immediately. Never reset the registry to retry.

7. Stage measured in the qualifying smoke's stage directory, changing
   `--phase smoke` to `--phase measured`. Check the printed runtime, then run:

   ```sh
   python3 "$d/runner.py" /path/stage/runtime-measured.json measured
   ```

   `--through-pair 1` through `4` pauses at measured pair boundaries. Omit it
   to resume through the guards. Slots are never replaced. Every stage and
   cell binds the stage's frozen models cache; changing the host file has no
   effect. Same-account renewal uses `stage.py --renew RUNTIME --auth PATH
   --claude-auth PATH` at permitted boundaries; either snapshot may be
   omitted to retain it. Keep old runtimes and snapshots for their bindings.

8. Retain every sealed local slot directory, request/response body, native
   transcript, verdict, archive, registration and runtime after remote
   deletion. PAT and model-bearer scans cover evidence before sealing and
   retained archive/verdict artifacts. A scan failure stops and requires
   credential revocation. g06 retains a manifest-bound local observation;
   repository deletion and HTTP 404 are explicitly inapplicable to it.

9. Summarize and adjudicate from retained evidence:

   ```sh
   python3 "$d/summarize.py" /path/stage/output --review-template m01 \
     > /path/reviews/m01.json
   python3 "$d/summarize.py" /path/stage/output --reviews /path/reviews \
     --json /path/analysis/summary.json > /path/analysis/summary.md
   ```

   Generate and fill a separate review for each dispatched measured slot and
   guard. Save derived output outside the sealed evidence tree. Reviews bind the exact
   slot record and grading record, with witness evidence for any severe
   regression or unresolved publication claim. A provisional decision is
   not permission to adopt or publish a release.

## Frozen schedule and grading

| Slots | Task | Engine / effort | Arms in order |
|---|---|---|---|
| m01, m02 | BV | Claude high | X, Y |
| m03, m04 | BV | Claude high | Y, X |
| m05, m06 | Z0 | Claude high | X, Y |
| m07, m08 | Z0 | Claude high | Y, X |
| g01 | BV | Codex high | Y |
| g02 | Z0 | Codex high | Y |
| g03 | BV | Claude max | Y |
| g04 | BV | Claude high | Y; no push or PR |
| g05 | Z0 | Claude high | Y; exactly one local task commit, no push or PR |
| g06 | BV | Claude high | Y; local commit reported LOCAL_ONLY, no remote or publication |

All measured slots and g01–g03/g06 use rp-d1 `common.txt` byte-for-byte,
SHA-256 `2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf`.
g04 appends a newline, `Do not push or open a pull request.`, and a newline;
g05 appends a newline, `Commit.`, and a newline. These bodies and the full
caller-contract prompts are hash-bound. Every sealed Claude request must
carry the slot's expected `output_config.effort`; mismatch stops the schedule.

Mechanical delivery retains rp-d1's scope/regression, exactly-one-correctly-
merged-PR and user-file preservation rules. All scope comparisons use Git
modes: 0600 and 0644 are equivalent; changed contents, execute bits and
symlinks still count. No path is exempt. LOCAL_ONLY and uncommitted outcomes
fail default delivery. Reports otherwise have no prose-quality gate.

The implementation makes these grading interpretations explicit:

- g05's "exactly a local commit" means one task commit beyond the installed
  allocation baseline; source/bootstrap and installer commits do not count.
  g05 and g06 also require the inherited local-delivery proof that the commit
  matches the assessed task source. An unrelated commit does not qualify.
- Narrow affirmative merge/push claims are compared mechanically with the
  evidence. Ambiguous language and unproven historical absence of publishing
  require adjudication. An unchanged final remote census cannot prove that
  a push or remote creation followed by deletion never occurred.
- Severe regression remains a reviewer witness field: measured Y requires
  the reproduced defect and a paired-X witness without it; a guard requires
  its own severe-defect witness. Pending review is shown separately from
  the exact ordered decision, with the decision marked provisional.
- Git-mode normalization also applies to preserved sentinel files. A
  permission-only snapshot change cannot become a false scope failure.
- Prompt-based failure classes are narrow deterministic labels, with `other`
  for failures that do not establish either specified reason.
- If usage is COMPLETE but wall evidence is missing, cost is unestablished:
  an otherwise eligible adoption is HOLD. Incomplete usage is INCONCLUSIVE
  under the earlier ordered rule.

The summary reports per-arm/per-pair delivery, per-task and per-check/oracle
pass counts, guards, failure classes, all four paired outcomes and the exact
paired one-sided binomial probability. Cost uses owner wall/input/output of
all eight measured slots only, including failed attempts, native children
and retries already counted by the inherited accountant. Each arm's totals
are divided by its delivery passes. Positive Y passes against zero X passes
use dominance, never raw-sum substitution. Smoke and guards are excluded.
The first matching DESIGN rule wins: INCONCLUSIVE, UNSAFE, REGRESSION,
NO FAILURE OBSERVED, REJECT, ADOPT, HOLD, MIXED.

## Offline checks

Tests use synthetic archives, records and model identities; local Git
fixtures do not contact any service. Run each directory separately to keep
inherited test module names isolated. Bytecode and pytest caching stay off.

```sh
d=autoresearch/experiments/rp-d6-claude-delivery
p=autoresearch/experiments/rp-d1-delivery-cost
q=autoresearch/experiments/rp-d2-report-lines
r=autoresearch/experiments/rp-d3-prompt-ablation
s=autoresearch/experiments/rp-d4-helper-report
t=autoresearch/experiments/rp-d5-claude-stages
for suite in "$d" "$s" "$t"; do
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$PWD/$p:$PWD/$q:$PWD/$r:$PWD/$s:$PWD/$t:$PWD/$d:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
  PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
  python3 -m pytest "$suite" -q || break
done
```
