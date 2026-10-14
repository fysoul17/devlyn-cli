# rp-d2 — report lines

The authoritative contract is [DESIGN.md](DESIGN.md). The apparatus loads the
frozen rp-d1 and 0255/0251/0233 code by path. Its internal `B` route means
installed product; rp-d2 plans, baselines and verdicts bind the actual X/Y arm,
release hashes and manifest. Tasks, checks, grading, scans and delivery stay rp-d1.

From the repository root, set `d=autoresearch/experiments/rp-d2-report-lines`.
Keep all stage, auth, archive and build directories outside the repository.

1. Pack offline from the verified registry artifact into a new directory:
   `python3 "$d/pack.py" /path/devlyn-cli-4.2.18.tgz /path/arms --candidate a623b382e655e893f6b39b96199ef8675afdde05`.
   X is copied verbatim; Y changes only the registered paragraph. `arms.json`
   records both tarball identities and extracted file manifest digests.
2. Build the pinned image with `bash autoresearch/experiments/rp-d1-delivery-cost/build.sh /path/new-build-context`.
   Register its exact `sha256:...` image ID for both arms.
3. Create the 24 private repositories `fysoul17/rpd2-<run-id>-<slot>`:
   `m01`..`m16`, `smoke-<claude|codex>-<X|Y>` and
   `smoke2-<claude|codex>-<X|Y>`. Use rp-d1's merge policy and fine-grained PAT
   permissions. Provision its private read-only `hosts.yml` and `config.yml`
   separately from the model auth snapshot and output roots.
4. Stage smoke:
   `python3 "$d/stage.py" /path/stage --run-id RUN --arms /path/arms/arms.json --image sha256:IMAGE --auth /path/model-auth --github-auth /path/github-auth --phase smoke`.
   Run `python3 "$d/stage.py" --check /path/stage/runtime-smoke.json`, then
   `python3 "$d/runner.py" /path/stage/runtime-smoke.json smoke`.
   A complete repeat uses a fresh stage directory and `--smoke-attempt 2`.
   Preserve attempt 1; no third attempt is registered.
5. Stage measured with the same arguments and directory, changing only
   `--phase measured`. This freezes one Claude smoke catalog per arm and
   requires the same Claude account/org and Codex account. Runtime binds Codex
   by the 12-hex SHA-256 prefix of `codex.json`'s `tokens.account_id`.
   Check `runtime-measured.json` as above;
   all four selected smoke cells must have working delivery and archived
   deletion/404 receipts. Freeze inputs and obtain registration reviews before exposure.
6. Run `python3 "$d/runner.py" /path/stage/runtime-measured.json measured`.
   For renewal, use `--through-pair N` to return after complete pair N, then
   `python3 "$d/stage.py" --renew /path/stage/runtime-measured.json --auth /path/new-model-auth`.
   Check and resume using the printed new runtime path. Earlier runtimes and
   slots remain intact; only the auth snapshot may change, on the identical
   Claude account/org and Codex account. Mid-pair renewal and stopped-run recovery are refused.
   The inherited 6300-second credential lifetime floor applies at every launch.
7. Generate each review with
   `python3 "$d/summarize.py" /path/stage/output m01 --review-template`.
   Astra ultra and Grok 4.7 fill separate `<slot>.json` files against raw
   evidence. Then run
   `python3 "$d/summarize.py" /path/stage/output --review astra=/path/astra --review grok=/path/grok`.
   `summary.json` and the table give arm × engine costs and the mechanical
   ADOPT / REJECT / INCONCLUSIVE decision with row reasons.
8. If reevaluation is needed, run
   `python3 "$d/reevaluate.py" /path/stage/output /path/new-corrections`.
   The rp-d1 seal/archive checks and optional `--disclosed-change SLOT:cell/work/.git/index`
   apply unchanged. Regenerate reviews and summarize with `--checklists /path/new-corrections`;
   raw evidence remains untouched until final adjudication.

Offline verification (importlib collection avoids the three frozen fixtures'
identically named test modules; their source directories supply local imports):

```sh
p=autoresearch/experiments/rp-d1-delivery-cost
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH="$PWD/$p:$PWD/$d:$PWD/$p/fixtures/BV/src:$PWD/$p/fixtures/SM/src:$PWD/$p/fixtures/Z0/src" \
PYTEST_ADDOPTS='--import-mode=importlib -p no:cacheprovider' \
python3 -m pytest "$p" "$d" -q
```

Tests use synthetic tarballs/auth and mocked external boundaries, never real
credentials, models, Docker or GitHub.

Measured slots continue after an accounting-only usage UNKNOWN: preserve the
inherited STOP in `accounting-stop.json`, verify identity, sealed evidence,
credentials/bindings and teardown, then run the normal checks and delivery grading
before repository deletion, in rp-d1's archive/done-check/delete/404/scan order.
No attempt is retried or replaced. Other instrumentation/security failures and
smoke UNKNOWNs still stop. Quality counts and numeric wall time remain; the
affected arm × engine's token totals and costs per success are UNKNOWN, which
blocks adoption on a compared cost row.
