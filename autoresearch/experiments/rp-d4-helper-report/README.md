# rp-d4 — the helper states cleanup

[DESIGN.md](DESIGN.md) is frozen and authoritative. This apparatus imports
rp-d2 and rp-d3 by path, and through them rp-d1/0255/0251/0233. Delivery,
checklists, seals, accounting, archive/deletion receipts and PAT scans retain
their inherited implementations. Measured slots are never replaced. The
commands below are operator steps; building and testing this apparatus does
not authorize a live run.

X is the registry `devlyn-cli@4.2.22` archive, verified against the registered
SHA-256 and registry SHA-512 integrity supplied to `pack.py`. Y replaces only
`config/skills/_shared/task-complete.py` and
`config/skills/_shared/task-completion.md` with a candidate Git commit's bytes.
`arms.json` binds both archives, tree manifests, the full candidate commit and
both candidate blob IDs. Both extracted and installed files are checked.
Every slot uses the unchanged rp-d1 `common.txt` (P0), SHA-256
`2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf`.

Set `d=autoresearch/experiments/rp-d4-helper-report` from the repository root.
Keep release, stage, auth and evidence directories outside the repository.

1. Before pack, pass the candidate helper self-tests and the inherited
   whole-file token gate against `cbc33be9`:
   `python3 autoresearch/experiments/rp-d2-report-lines/token_gate.py cbc33be9 CANDIDATE config/skills/_shared/task-completion.md`.
   The gate uses a live counting service; preserve its passing evidence before
   registration. It is a precondition, not an outcome. DESIGN records the
   frozen gate as Claude 4867 → 4860 and o200k proxy 2979 → 2976.
2. Pack offline using registered values, without fetching Git objects:
   `python3 "$d/pack.py" /path/devlyn-cli-4.2.22.tgz /path/release --candidate COMMIT --sha256 REGISTERED_SHA256 --integrity REGISTRY_SHA512_INTEGRITY`.
   Freeze `arms.json`, X/Y hashes, candidate commit/blobs and the apparatus
   inputs in registration before smoke. No registry checksum is guessed.
3. Build the pinned inherited image:
   `bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context`.
   Use one exact image digest, Codex 0.162.1 with `gpt-6-sol`, effort `high`,
   the frozen models cache, and Claude Code 2.1.296 with `claude-opus-5-5`,
   effort `max`. Benchmark hard rule 5 requires a fixed host network,
   the VPN client quit, and route-watcher logging throughout the run.
4. Use a fresh run ID and provision 14 private repositories:
   `fysoul17/rpd4-<run-id>-m01` through `m08`, `g01`, `g02`,
   `smoke-codex-X`, `smoke-codex-Y`, `smoke2-codex-X`, `smoke2-codex-Y`,
   all with the same `rpd4-<run-id>-` prefix. Use rp-d1's merge policy and a
   fresh fine-grained PAT with its permissions. Provision private read-only
   `hosts.yml` and `config.yml` separately from model auth and output roots.
5. Create separate private model snapshots:
   `python3 "$d/auth.py" codex /path/codex/auth.json /path/codex-snapshot`
   and `python3 "$d/auth.py" claude /path/claude-snapshot`.
   Codex uses rp-d3's canonical ChatGPT OAuth snapshot and empty `claude.env`.
   Claude uses rp-d2's inherited default-host snapshot, account/profile check,
   access-only environment and expiry policy; its bundled Codex identity must
   match the Codex snapshot. Both directories are mode 0700, files 0400.
   No credential belongs in arguments, runtime JSON, reports or this repository.
   The 6300-second floor applies only to Claude, checked before guard dispatch.
   Codex validation does not contact the Claude profile service.
6. Stage smoke:
   `python3 "$d/stage.py" /path/stage --run-id RUN --arms /path/release/arms.json --image sha256:IMAGE --auth /path/codex-snapshot --claude-auth /path/claude-snapshot --github-auth /path/github-auth --phase smoke`.
   Check with `python3 "$d/stage.py" --check /path/stage/runtime-smoke.json`,
   then run `python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke`.
   Smoke runs SM/X then SM/Y, checking delivery, release binding and checklist
   emission. Y additionally requires the deterministic cleanup check below.
   Smoke reports are not graded. A failed smoke consumes the pair; preserve
   it and use a fresh stage directory with `--smoke-attempt 2` for both spare
   cells, retaining the same run ID, arms, accounts, image and models cache.
   `~/.devlyn/rp-d4-runs/<run-id>/` preserves shared attempt reservations and
   bound verdicts across stage directories. Preserve that registry with the
   evidence; changing the stage or release directory cannot reset it. A failed
   spare stops the run. Credential revocation stops either attempt. There is
   no replay or third attempt.
7. Stage measured with the same arguments/directory and `--phase measured`.
   Both selected smoke verdicts must qualify and carry archive/deletion/404
   receipts. Accounts must remain identical; a renewed snapshot may be used.
   Check `runtime-measured.json`. Run:
   `python3 "$d/runner.py" /path/stage/runtime-measured.json measured`.
   Order is BV X/Y, BV Y/X, Z0 X/Y, Z0 Y/X (`m01`–`m08`), followed by Claude
   Y/BV (`g01`) and Y/Z0 (`g02`). `--through-pair N` pauses after Codex pair
   1–4; omitting it resumes the remainder, including both guards.
8. Between complete Codex pairs, or after m08 before the guards, renew with
   `python3 "$d/stage.py" --renew /path/stage/runtime-measured.json --auth /path/new-codex-snapshot --claude-auth /path/new-claude-snapshot`.
   Either snapshot option can be omitted to retain it. A replacement Claude
   snapshot must meet the 6300-second floor. Both accounts must be identical.
   Check/resume the printed runtime. Prior runtime files and evidence remain
   intact; mid-pair renewal (including between guards), account changes and
   resuming a STOP are refused.
9. For every measured and guard slot, generate a review template:
   `python3 "$d/summarize.py" /path/stage/output m01 --review-template`.
   Use the unchanged review instructions in
   [rp-d3's review prompt](../rp-d3-prompt-ablation/results/measured/reviews/prompt.md),
   adapting only the run/slot/file references to include all ten slots.
   Astra ultra (`astra-ultra`) and Grok 4.7 (`grok-4.7`) each fill separate
   slot JSON files against the frozen checklist. Summarize with
   `python3 "$d/summarize.py" /path/stage/output --review astra=/path/astra --review grok=/path/grok`.
   `summary.json` and the table report Codex per-arm and per-pair categories,
   successes, owner wall/input/output per success, and Claude guard results.
   Costs include every dispatched measured attempt for the arm; smoke and
   the uncontrolled Claude guard are outside the Codex comparison.

The helper's stdout JSON is captured in native tool results. Its per-call
`actions` record is intentionally not persisted by the product. Y smoke alone
therefore uses a read-only Python observer in the harness, loaded through
`PYTHONPATH`, to capture `complete`'s action record and returned object without
changing the installed helper bytes, prompt or receipt. Captures enter the
inherited raw evidence seal and credential scans. Qualification binds the
observer, matches its returned object to native stdout, renders the exact
DESIGN sentence from the call's action/scratch status, and compares claims
with `report-checklist.json.resources`. Missing or inconsistent evidence fails
qualification. Measured and guard slots have no observer.

Two implementation interpretations are explicit. DESIGN gives sentence
clauses but no delimiter rule: the checker uses the candidate's specified
semicolon-separated clauses and final period, tested independently of its
renderer. DESIGN has no Claude smoke from which to learn a boot catalog;
following rp-d3, there is no prelearned catalog comparison. The inherited
Claude startup catalog is still collected and validated by the native runner.
The two guard slots form one uninterrupted guard block for auth renewal.

The ordered decision is INCONCLUSIVE for a STOP, incomplete dispatch, failed
delivery (including any observed `merge_refused`) or missing adjudication;
then BASELINE MOVED, REJECT, ADOPT, HOLD or MIXED exactly as DESIGN specifies.
Any reviewer FALSE in any Y slot vetoes adoption. Zero Y successes fails cost;
positive Y successes against zero X successes pass by dominance. Otherwise
all three per-success costs must be no greater, with a strict success or cost
improvement. Exact ties HOLD. Both guard reports need both reviewers to mark
all four categories SUPPORTED. This apparatus reports a decision; it never
publishes a release. Missing wall evidence makes a required cost comparison
INCONCLUSIVE under 0232 §6; UNKNOWN token usage overrides every branch.

Offline checks use synthetic artifacts and credentials, with live boundaries
blocked. Run one directory at a time to keep inherited test module names isolated:

```sh
p=autoresearch/experiments/rp-d1-delivery-cost
q=autoresearch/experiments/rp-d2-report-lines
r=autoresearch/experiments/rp-d3-prompt-ablation
for suite in "$d" "$q" "$r"; do
  PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH="$PWD/$p:$PWD/$q:$PWD/$r:$PWD/$d:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
  PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
  python3 -m pytest "$suite" -q || break
done
```
