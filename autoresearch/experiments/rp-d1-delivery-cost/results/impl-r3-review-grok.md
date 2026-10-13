I'll review the round-3 delivery path against the round-2 findings and DESIGN.md, starting with those reviews, the commit, and the files the runner and stage actually read.Round-2 left four open findings: partial-archive PAT scans, post-evaluation record scans, the installer-date test, and the measured Claude boot catalog. I'll read the binding design and the files that commit changed.The scan and catalog gates are in place. Next I’ll compare the staged runtime and control tree with what 0233, 0234, 0237, 0238, 0251, and 0255 actually read.Round-2 findings are closed in `914d1272`. No new HIGH or MEDIUM defect on the live PR+merge path, the PAT records, or the inherited accounting, identity, and seal gates.

## Round-2 closures

**Partial archive (Astra HIGH).** `runner.py:230-234` scans the archive root whenever it exists, including after `repository.json` is written and manifest creation fails. Deletion still runs only after `archive()` returns (`runner.py:202-216`) through `delete_archived`, which re-verifies the manifest. `test_partial_archive_pat_is_scanned_and_repository_retained` (`test_apparatus.py:988-1027`) fails without that root: the final scan omits the archive, the slot stays `STOP` with `usage` `COMPLETE`, and the assertions on `UNKNOWN`, `revocation_required`, `RETAINED`, and `delete_archived` not called all fail.

**Evaluator records (Astra HIGH).** `runner.py:230-241` scans the whole slot after evaluation, `github-delivery.json`, and `report-checklist.json`, and only then writes `rp-verdict.json`. `test_final_scan_catches_real_evaluator_output_after_seal` (`test_apparatus.py:1034-1086`) fails without it: the token printed by a correct BV import lands in `checks-raw.json` after the pre-seal scan, and the slot stays `ADJUDICATE` instead of `UNKNOWN` with revocation.

**Installer dates (Astra and Grok MEDIUM).** `runner.py:66` rebinds `frame.prepare.git` to `bootstrap_git`. `0233/prepare.py:61-62` calls that global, so the real `install B` commit gets `BOOTSTRAP_DATE`. `test_full_ancestor_prepare_restores_codex_environment_single_table_and_dates` (`test_apparatus.py:704-741`) runs `Runner.prepare` with only the Docker `subprocess.run` mocked. Deleting line 66 leaves a wall-clock commit and the `%aI`/`%cI` assertion fails.

**Measured Claude catalogs (Grok HIGH).** `stage.py:63` and `stage.py:74` put the smoke-claude verdict catalogs at `boot_catalogs.claude.B`, which `0237/runner.py:200-206` reads. A missing catalog still raises before prepare, and `runner.py:35-37` plus `runner.py:223-225` keep that exact text. `test_measured_copies_recorded_catalogs_and_keeps_smoke_inputs_frozen` (`test_stage.py:109-120`) calls real `boot_expectation` via `check()` and fails if the key is absent or misshaped. `test_measured_claude_without_catalogs_refuses_before_github_mutation` (`test_apparatus.py:818-827`) fails if prepare or launch runs, or if the reason is collapsed to `rp-d1 instrumentation failed: ValueError`.

On every `run()` path the final scan is in `finally` after the slot, archive, inherited verdict, and not-dispatched files, and before `rp-verdict.json`. A hit or scan error forces `UNKNOWN`, clears usage and tokens, and sets `revocation_required`.

## stage.py

`stage.py:64-74` writes the runtime keys those runners read: `phase`, `image`, `control`, `output`, `smoke_output`, `scratch`, `sources`, `source_root`, `auth`, `auth_manifest_sha256`, `account`, `tasks_file`, `models_cache`, `release`, and `boot_catalogs`. Control layout matches the mounts and the installer: `public/python`, `public/autoresearch`, `oracle/experiments/rp-d1-delivery-cost/`, and `packages/B/package`, with `control.manifest.json` using the same file census as `control_unchanged`. Credential checks use `credential_directory` (`stage.py:78` and `stage.py:127`) and never `credential()`, so the PAT bytes are not read. `--check` (`stage.py:112-142`) only hashes inputs, verifies the release and auth binding, checks catalog shape and smoke deletion receipts, and runs `docker image inspect`. It does not call `run()`, `gh`, or a model.

## New defects

None at HIGH or MEDIUM. A clean 4.2.18 merge still reaches the inherited done-check with absent `devlyn.completionMode` (`policy()` defaults to `auto`), and a PAT hit cannot remain `PASS` or `ADJUDICATE` in `rp-verdict.json`.

## Removable

Nothing further can be removed without dropping a seal, a refusal string, or a scan root.

VERDICT: SHIP
