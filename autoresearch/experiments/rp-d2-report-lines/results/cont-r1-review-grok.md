I'll review the commit against the design contract and the inherited rp-d1 path, starting with the decision record and the four files under judgment.The design rule is accounting-only UNKNOWN on measured cells, with smoke still stopping. Next I’ll compare the continuation path to the inherited rp-d1 gates.The continuation class reimplements the post-accounting gates. I’ll compare that copy to the inherited 0255/0238 order and to rp-d1’s archive sequence.The copied post-accounting tail matches 0255/0238, and it runs before archive, deletion, and the PAT scan. The Claude allowlist does not. A 0254 fail-fast gap can skip account, lifecycle, and scope checks that a COMPLETE cell must pass, and the cell can still be quality-graded.

## HIGH

`autoresearch/experiments/rp-d2-report-lines/runner.py:78` allows ten Claude gap strings. `0254/audit.py:84` keeps only the first `require` failure, and `0255/runner.py:41` runs the foreign-carrier and independent-launch inventory only when that audit returns `MATCH`. Continuation never re-runs either set. A COMPLETE cell cannot be graded unless those checks passed. An allowed gap grades the cell anyway.

- `0254/audit.py:224` (`error or retry outside scope`, the smoke `api_error` case) returns before the account and session check at `0254/audit.py:248`. A request whose account hash does not match the frozen account is never read. The same is true for `invalid native aggregate counters` (`0254/audit.py:173`) and the five `usage()` failures, which fire at `0254/audit.py:177`.
- `child result aggregate mismatch` (`0254/audit.py:351`) returns before `unaccounted child launch` (`0254/audit.py:352`) and `child did not complete` (`0254/audit.py:371`). A broken child lifecycle is graded as accounting-only and can become a success.
- Any allowed gap leaves the audit `UNKNOWN`, so `0255/runner.py:41` does not run. An owner-launched Codex session stays `identity.status == MATCH` because `0234/cell.py:34` skips `owner_launched`. A COMPLETE cell would record `foreign native evidence carrier outside scope` or `independent invocation or incomplete native inventory outside scope` and stop, because those strings are not allowed. The continued cell is graded.

Codex does not have this hole. `0234` keeps every gap, `runner.py:84` admits a cell only when every gap is one of the three counter disagreements, and `0238/runner.py:165` has already required clean teardown, `identity` `MATCH`, and peer `MATCH`.

There is no inherited resume hook. `0255/runner.py:125` and `0238/runner.py:171` catch the usage error inside `run`, so calling `run` again would relaunch the owner. The tail copy can stay. Eligibility has to be the same checks a COMPLETE cell has already passed: re-run the skipped 0254 account and lifecycle requires, and run the `0255/runner.py:41` scope inventory, before grading. Keep 0254 itself unchanged.

## LOW

`runner.py:146` leaves `reason` as `ValueError: whole-run usage UNKNOWN` after it sets `ADJUDICATE` or `CHECKS_PASS`. The schedule grade is unaffected: `rp-d1-delivery-cost/runner.py:202` copies `reason` only while status is `STOP`. Someone reading `verdict-<cell>.json` can treat a graded cell as stopped.

## The four checks

1. The hand-copied tail matches the inherited post-raise order. Identity, boot catalogs, quota, `unchanged`, locate, check, delivery, and the status ternary (`runner.py:108` and `runner.py:121`) follow `0255/runner.py:127` and `0238/runner.py:173`, including `protocol_violations`. The extra peer, teardown, PAT-marker, and seal checks are fail-closed. Peer `MATCH` already means no gaps and no violations (`0242/policy.py:286`). `Runner.run` calls `rp-d1` `run`, which calls this hook, which calls `0255`. Archive, `done_check`, delete/404, and the final PAT scan stay in `rp-d1-delivery-cost/runner.py:193` and then `rp-d1-delivery-cost/runner.py:211`. The grade split is the skipped pre-raise checks above, not the tail formula.

2. The Codex gap set is the three counter disagreements and nothing else. The Claude set is not accounting-only. The scenarios above can hide an account mismatch, a broken child lifecycle, or a foreign engine launch.

3. The diamond is `rp-d2.Runner` → `rp-d1.Runner` → `AccountingContinuation` → `0255.Runner`. Claude stays in `0255.run`. Codex hits `return super().run()` and lands on `0238.run`, because no class between them defines `run`. Smoke returns at `runner.py:96` before grading, so the cell stays `STOP`. Continuation failures record only the exception type (`runner.py:145`). `rp-d1` still strips any other escaped payload, and the final scan reads the verdict file.

4. One `UNKNOWN` attempt leaves that arm×engine token totals and every per-success cost `None`, keeps `owner_seconds` and `wall_completeness`, and still counts quality (`summarize.py:29`). A compared cost row with `UNKNOWN` usage or wall becomes `UNKNOWN` and the decision is `INCONCLUSIVE` (`summarize.py:60`). A zero-success row stays `NO_BASELINE` and is not compared (`summarize.py:56`), which is the registered edge case.

VERDICT: REVISE
