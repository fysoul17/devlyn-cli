The round-1 check summary, effort comparison, network deviation, guidance quote, and six-repository 404 list match the smoke record. Two statements still go past that record.

## MEDIUM

**The spare stop is a later re-run, and the handoff states it as the original refusal.** `spare-refusal.txt` is labeled a re-run at `2026-10-18T00:09:52Z`. It prints `github_rpd1_prepare.EvidenceError: spare changed registered release, accounts, image or models cache` and then `exit=0`. `stage.py` `main` lets `EvidenceError` propagate, so a refusal from that process is a non-zero status. The registered `models_cache_sha256` matches `run-registry-attempt-1.json` (`38e0d508…`), and the host hash differs (`5a0d377d…`), which is enough for `reserve_smoke` to raise. The only mtime is `2026-10-18T09:09:43+0900`, nine seconds before that re-run. `results.md` says the file was rewritten again during this write-up. HANDOFF line 3 and the rp-d5 paragraph say the spare was refused because that host file’s hash changed, and that the file drifts between days.

## LOW

**Local retention still has an end date.** `results.md` keeps the sealed smoke stage, without credentials, until rp-d6’s write-up merges, and cites DESIGN. DESIGN keeps evidence until the analysis is reviewed. `README.md` says never prune local evidence after repository deletion.

The verdict and the report agree on `PRODUCT_INCOMPLETE`, the delivery reason, `product_check_pass: false`, `source_check_pass: false`, the three scope paths, public `13 passed`, five oracle `PASS` rows, effort binding `MATCH`, accounting `MATCH`, qualification `FAIL` on delivery, 5 terminal turns, `owner_seconds` `48.41594350000014`, output `3293`, and thinking `1243`. The block quote matches the report. The cell window `23:40:54Z`–`23:41:42Z` is the guidance file’s `started_at` / `ended_at`; the route log’s last line is `23:32:24Z` `en0`; `network.txt` records WARP connected at `23:40:14Z`. rp-d4 g01/g02 are 23 and 28 terminal messages, `423.170…` s and `447.467…` s, output `36686` and `39814`, arm Y, `claude_effort` `max`. The speed paragraph marks that comparison untested. The guidance file’s request hash matches the verdict source for `683f90b9…`. `common.txt` has no publishing ban. The six 404 lines are the six README repository names, and `smoke-claude` also has `DELETED`, HTTP 404, and an archive hash in the verdict. No credential, VPN hostname, or IP is in the write-up or those smoke files.

VERDICT: REVISE
