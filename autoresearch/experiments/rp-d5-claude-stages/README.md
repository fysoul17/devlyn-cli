# rp-d5 — Claude delivery stages and effort

[DESIGN.md](DESIGN.md) is frozen. This apparatus imports
[rp-d4](../rp-d4-helper-report/) by path and retains its rp-d2/rp-d3/rp-d1,
0251 and 0254 lifecycle, authentication, delivery checks, seals and accounting.
It makes no product change and nominates no candidate. Building or testing it
does not authorize a live run.

Only the registry `devlyn-cli@4.2.22` tarball is installed (arm X). The supplied
registered SHA-256 and registry SHA-512 integrity must both match. There is no
candidate package. Every slot uses rp-d1's unchanged `common.txt`, SHA-256
`2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf`.

| Slot | Task | Effort |
|---|---|---|
| smoke-claude | SM | high |
| smoke2-claude (one spare) | SM | high |
| c01 | BV | max |
| c02 | BV | high |
| c03 | Z0 | high |
| c04 | Z0 | max |

The selected smoke precedes c01. Measured slots run serially in table order,
with Claude Code **2.1.296**, model **claude-opus-5-5**. No Codex inference is
scheduled. Slot task projections change only Claude's inherited effort; the
launch route, identity/accounting checks and every sealed request body bind
the same expected value. Any request effort mismatch STOPs before the next
slot, even if another auditor invariant fails first.

## Operator steps

From the repository root set `d=autoresearch/experiments/rp-d5-claude-stages`.
Keep release, stage, auth and evidence directories outside the repository.
Commands below use path placeholders; do not put secret values in arguments,
environment dumps, reports, runtime JSON or this repository.

1. Run all offline checks below. Register the apparatus commit, oracle and
   release identity before smoke; do not change them after the run starts.
2. Pack the supplied registry archive offline:

   ```sh
   python3 "$d/pack.py" /path/devlyn-cli-4.2.22.tgz /path/release \
     --sha256 REGISTERED_SHA256 --integrity REGISTRY_SHA512_INTEGRITY
   ```

   Preserve `arms.json` and its referenced tarball and manifest. No checksum is
   guessed and no Git candidate is substituted.
3. Build the pinned inherited image with
   `bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context`.
   Record and reuse its exact image digest and frozen models cache. Apply the
   inherited image prune guard. Benchmark hard rule 5 requires a fixed network,
   VPN client applications quit, and route-watcher logging throughout the run.
4. Use a fresh run ID and provision private repositories
   `fysoul17/rpd5-<run-id>-<slot>` for c01–c04, smoke-claude and smoke2-claude.
   Follow rp-d1's merge policy. Provision a fresh fine-grained PAT with the
   inherited permissions in private read-only `hosts.yml` and `config.yml`,
   separately from model auth and output roots.
5. Create a private Claude snapshot:

   ```sh
   python3 "$d/auth.py" /path/claude-snapshot
   ```

   This uses rp-d4's Claude snapshot semantics: default-host Claude identity,
   account/profile validation, access-only transport and a **6300-second**
   remaining-lifetime floor. The inherited snapshot bundles `codex.json` and
   validates its identity; no separate Codex snapshot is required. Directories
   are mode 0700 and files 0400. Wait for the host's normal token refresh if
   the lifetime is insufficient; do not weaken the floor.
6. Stage, check and run smoke:

   ```sh
   python3 "$d/stage.py" /path/stage --run-id RUN \
     --arms /path/release/arms.json --image sha256:IMAGE \
     --auth /path/claude-snapshot --github-auth /path/github-auth --phase smoke
   python3 "$d/stage.py" --check /path/stage/runtime-smoke.json
   python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke
   ```

   Qualification requires delivery, bound effort, reconciled accounting and a
   stage table without UNKNOWN. Mutation-unknown and low-coverage flags are
   descriptive and do not independently fail smoke. A failed first smoke is
   preserved; stage a fresh directory with the same inputs/run ID and
   `--smoke-attempt 2`. The persistent `~/.devlyn/rp-d5-runs/<run-id>/` registry
   prevents replay across stage directories. A failed spare or credential
   revocation stops the run. Keep this registry with the evidence.
7. Stage measured with the same arguments and selected smoke stage directory,
   changing `--phase measured`. Qualification and archive/deletion/404 evidence
   must be present. To pause after c01, run:

   ```sh
   python3 "$d/stage.py" --check /path/stage/runtime-measured.json
   python3 "$d/runner.py" /path/stage/runtime-measured.json measured --through-slot 1
   ```

   Resume with `--through-slot 2`, then 3 and 4 as needed. Without the option,
   all remaining slots run serially. Every dispatched slot is retained with
   its outcome and costs; none is replaced and STOP cannot be resumed.
8. Between completed measured slots, create a new snapshot on the identical
   Claude account and renew:

   ```sh
   python3 "$d/stage.py" --renew /path/stage/runtime-measured.json \
     --auth /path/new-claude-snapshot
   ```

   Check and resume the newly printed runtime path. The lifetime floor and
   both inherited account identities remain enforced. Keep old runtimes and
   snapshots available for their bound evidence. Renewal changes no release,
   prompt, schedule or completed evidence.
9. Analyze retained evidence locally, after repository archive/deletion:

   ```sh
   python3 "$d/attribute.py" /path/stage/output/c01 --markdown
   python3 "$d/summarize.py" /path/stage/output --json /path/analysis/summary.json \
     > /path/analysis/summary.md
   ```

   The analysis directory must already exist; choose a new JSON output path.
   No report review is required:
   delivery retains rp-d1's scope/regression, exactly-one-merged-PR and user
   file checks. `LOCAL_ONLY` and any `merge_refused` are failed deliveries.

**Keep every local slot directory, sealed request/response body, project
JSONL, manifest, inherited verdict, archive and runtime after GitHub repository
deletion. Never prune local evidence.** Repository deletion requires the
inherited archive and confirmed 404 receipt. The inherited PAT, bundled Codex
and Claude bearer scans run before sealing and across retained artifacts;
a scan failure stops the run and requires credential revocation.

## Reading the analysis

0254 is the only token accountant. One row per audited receipt follows index
order, including foreground children, with tools taken from its response and
results joined by tool-use ID. Row sums must reconcile exactly. Thinking is
inside output; marginal tokens are output plus cache write. Stage cache-read
columns are context observations, not a charge. Cache-read series and slot
first-row cache write/read are shown separately. Wall is only `owner_seconds`;
there is no stage wall estimate or first-row wall subtraction.

Raw and first-row-excluded deltas are **max minus high**, within each task.
The frozen prediction requires strictly more turns and thinking at max and
the same delivery outcome. Efficiency is withheld unless both slots deliver
and the required costs are known. These are four observations, not a rate or
a causal estimate. Repeated exact tool operations show occurrence rows and
intervening writes/unknowns; their enclosing-row tokens are shared and
non-additive.

The following classifier details resolve DESIGN's remaining implementation
ambiguities and are covered by the frozen oracle:

- The requested per-stage cache-read column is informational context only;
  the row series is retained and neither marginal tokens nor stage charges
  include cache read.
- Git read commands ignore bare revision-shaped tokens such as `HEAD` and
  hashes; slash/dot path-shaped tokens are normalized, and outside-tree tokens
  are ignored as revisions. Shell parsing is lexical, not shell execution.
- Task paths include the inherited helper's sibling
  `/cell/work.devlyn.noindex/` allocation tree. Explicit additional task roots
  can be supplied to the attribution API.
- The stated stage priority applies literally: the last tool-free receipt is
  Report, earlier tool-free receipts are Other, including after delivery.
  Report also takes precedence after an unparseable completion result.
- A completion's invoking row stays outside After delivery. When that row
  also matches another primary predicate it is Mixed under rule 3; a pure
  completion row is Deliver. Subsequent tool rows are After delivery.

The fixture oracle is `test_attribute.py`; its named Bash cases have explicit
expected labels and predicates, including heredocs and quoted command words.

## Offline checks

Run one directory at a time so inherited module names remain isolated. Tests
use synthetic native receipts/JSONL and block live boundaries. Disable bytecode
and pytest's cache to avoid changing inherited apparatus directories.

```sh
p=autoresearch/experiments/rp-d1-delivery-cost
q=autoresearch/experiments/rp-d2-report-lines
r=autoresearch/experiments/rp-d3-prompt-ablation
s=autoresearch/experiments/rp-d4-helper-report
for suite in "$d" "$s"; do
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$PWD/$p:$PWD/$q:$PWD/$r:$PWD/$s:$PWD/$d:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
  PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
  python3 -m pytest "$suite" -q || break
done
```
