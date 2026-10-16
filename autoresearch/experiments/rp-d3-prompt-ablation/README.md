# rp-d3 — prompt ablation

[DESIGN.md](DESIGN.md) is authoritative. The apparatus imports
rp-d2 and, through it, the frozen rp-d1/0255/0251/0233 code by path. Delivery,
checklists, seals, accounting, archive/deletion receipts and PAT scans retain
their inherited implementations. No measured slot may be replaced.

Both prompts install the single registry `devlyn-cli@4.2.18` artifact (internal
installed route/mount `B`). `pack.py` checks its registered SHA-256 and registry
SHA-512 integrity with rp-d2's archive utilities; no candidate is repacked.
The extracted and installed reporting instruction must match Git blob
`faff9b9c8303ccc5bcbb52bbd19456f8584ea00b` (`7516ebc9:config/skills/_shared/task-completion.md`)
before sealing. Only the prompt body selects P0/P1. Registered body SHA-256:

- P0: `2ccc7f6a11891f6270685c09ada44cc4376bbedb047f8a0864f950b415bf50cf`
- P1: `ea77742f3d54f28638d1ca5e7240b8ce7fa1df9644429784239d6c806f601a21`

P1 deletes exactly the registered suffix including its leading space and keeps
the newline. Both append the unchanged caller contract. Verdict `prompt_sha256`
is the body hash; baseline `prompt_sha256` remains the inherited whole-prompt
hash, and plan/baseline additionally record `prompt_body_sha256`.

Authentication is a private Codex-only snapshot with a 12-hex SHA-256 prefix of
`tokens.account_id`, immutable file hashes and the original Codex JSON. Its
empty `claude.env` is solely the env-file transport required by the unchanged
0251 launcher: it contains no credential and must remain empty. No host Claude
login, account/profile request, expiration or boot catalog is read. The inherited
6300-second floor checks Claude's `expiresAt`, never Codex's token; rp-d3 does
not transfer that Claude-only policy to Codex or invent an expiry. Runtime
`account` is the Codex digest alias needed by rp-d2 staging, not an account pair.
The snapshot is checked during validation/preflight and again immediately before
launch. Renew only to the identical Codex account between complete pairs.

From the repository root set `d=autoresearch/experiments/rp-d3-prompt-ablation`.
Keep build, stage, auth and evidence directories outside this repository.

1. Verify/copy the registry artifact offline:
   `python3 "$d/pack.py" /path/devlyn-cli-4.2.18.tgz /path/release`.
   `arms.json` contains one `B` release and one `B.tgz`.
2. Build with the pinned rp-d1/rp-d2 image definition:
   `bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context`.
   Use one exact `sha256:...` image ID throughout, with Codex 0.162.1,
   `gpt-6-sol`, effort high and the frozen models cache. Hold the host network
   fixed and quit the VPN client for the run (benchmark hard rule 5).
3. Use a fresh run ID and create 12 private repositories:
   `fysoul17/rpd3-<run-id>-m01` through `m08`,
   `smoke-codex-P0`, `smoke-codex-P1`, `smoke2-codex-P0`, `smoke2-codex-P1`
   with the same repository prefix. Use rp-d1's merge policy and a fresh
   fine-grained PAT with its permissions. Provision private, read-only
   `hosts.yml` and `config.yml` separately from model auth and output roots.
4. Snapshot the explicit Codex auth source:
   `python3 "$d/auth.py" /path/codex/auth.json /path/model-auth`.
   The directory is mode 0700 and its files 0400. No credential belongs in
   command arguments, runtime JSON, reports or this repository.
5. Stage smoke:
   `python3 "$d/stage.py" /path/stage --run-id RUN --arms /path/release/arms.json --image sha256:IMAGE --auth /path/model-auth --github-auth /path/github-auth --phase smoke`.
   Run `python3 "$d/stage.py" --check /path/stage/runtime-smoke.json`, then
   `python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke`.
   Smoke runs SM/P0 then SM/P1 and qualifies delivery, prompt/release bindings
   and checklist emission; its reports are not graded. A stopped smoke is
   discarded as a pair. Preserve it; repeat both cells in a fresh stage directory
   with `--smoke-attempt 2`. There is no third attempt.
6. Stage measured with the same arguments/directory and `--phase measured`;
   an updated Codex snapshot may be supplied and the smoke identity is retained.
   Check `runtime-measured.json`. Both selected smoke cells must have working
   delivery and archived deletion/404 receipts. Freeze inputs and obtain the
   registration reviews before exposure.
7. Run `python3 "$d/runner.py" /path/stage/runtime-measured.json measured`.
   Order: BV P0/P1, BV P1/P0, Z0 P0/P1, Z0 P1/P0 (`m01`..`m08`).
   `--through-pair N` pauses after pair 1..4. Between pairs use
   `python3 "$d/stage.py" --renew /path/stage/runtime-measured.json --auth /path/new-model-auth`,
   then check/resume the printed runtime. Prior runtimes/evidence stay intact.
   Mid-pair renewal, account changes and resuming a STOP are refused.
8. For each measured slot, generate a template:
   `python3 "$d/summarize.py" /path/stage/output m01 --review-template`.
   Astra ultra (`astra-ultra`) and Grok 4.7 (`grok-4.7`) fill separate slot JSON
   files against the frozen checklist. Summarize with
   `python3 "$d/summarize.py" /path/stage/output --review astra=/path/astra --review grok=/path/grok`.
   `summary.json` and the table report both-reviewer success/category tallies,
   delivery passes, pair outcomes, descriptive token/wall costs and the exact
   registered decision/follow-ups. Any STOP, undispatched slot, delivery failure
   or pending reviewer makes attribution INCONCLUSIVE, even if the other reviewer
   already supplied a valid FAIL. Cost does not determine the decision.

Offline checks (no Docker, GitHub, network, models or real credentials):

```sh
p=autoresearch/experiments/rp-d1-delivery-cost
q=autoresearch/experiments/rp-d2-report-lines
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH="$PWD/$p:$PWD/$q:$PWD/$d:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
python3 -m pytest "$d" "$q" "$p" -q
```
