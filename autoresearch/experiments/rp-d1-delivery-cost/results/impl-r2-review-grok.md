I'll review the round-2 delivery path against the round-1 findings and DESIGN.md, starting with the prior reviews, the two fix commits, and the binding design.Round-1 HIGH items are closed in the tree at `1a83526f`. One inherited gate still stops every measured Claude delivery, so the measured half of the study cannot start.

## Round-1 closures

**PAT scan errors (Astra HIGH).** `cell.py:90-97` turns any scan failure into a fixed `ValueError` after writing `pat-scan.json`, with `raise ... from None`. `runner.py:222-225` then forces `UNKNOWN` and `revocation_required`. `test_unreadable_token_named_directory_records_unknown_without_path` (`test_apparatus.py:376-394`) locks the exact message and the marker. `test_real_inherited_auditor_gap_and_pat_hit_stop_before_grading` (`test_apparatus.py:825-882`) fails if the token or the cell path appears in `verdict-o01.json`, `rp-verdict.json`, or `pat-scan.json`.

**Archive bypass (Astra HIGH, Grok HIGH).** `runner.py:199-212` scans the archive before `done_check` and deletes in `finally`. `test_pat_only_in_archived_pr_body_deletes_repository_and_stops_schedule` (`test_apparatus.py:886-922`) puts the token only in the PR body; without the archive scan, grading runs or the slot stays `CHECKS_PASS` and the repository is not `DELETED`.

**Compressed Git objects (Astra HIGH, Grok HIGH).** `cell.py:81-87` streams `git cat-file --batch-all-objects --batch`. `test_unreachable_git_blob_and_registered_worktree_objects_are_scanned` (`test_apparatus.py:404-420`) and `test_archive_mirror_blob_is_scanned_without_changing_archive` (`test_apparatus.py:422-432`) store the token with `hash-object -w` and assert the raw files do not contain it. Without `cat-file`, both stay green and never raise `PAT-byte hit`.

**Codex trust (Grok HIGH).** After 0237/0238 rewrite the file, `runner.py:114-120` writes `prepare.codex_toml` (`prepare.py:35-39`) with `[projects."/cell/work"]` and the shell-policy `set` table, then reseals. `test_full_ancestor_prepare_restores_codex_environment_single_table_and_dates` (`test_apparatus.py:714-719`) walks that ancestor chain. Dropping the rewrite leaves 0238's base toml, which has no `shell_environment_policy`, and the assertion fails.

**Peer routes (Grok MEDIUM).** `tasks.json:3-19` and `smoke-tasks.json:3-19` register only `owner`. `runner.py:37-45` rejects any other key, and `runner.py:72-75` seats the native child as that owner. `test_routes_register_only_owner_and_native_children_use_owner` (`test_apparatus.py:728-734`) fails if a peer, judge, or reviewer route returns, or if the child seat is not the owner.

**Oracle datetime row (Astra MEDIUM).** `oracle.py:43-45` compares datetimes inside the row, and `oracle.py:65-69` records a participant exception as `FAIL`. `test_float_implementation_passes_public_but_datetime_exception_fails_row` (`test_apparatus.py:971-986`) uses `float(now) >= float(deadline)`, expects pytest exit 0, and expects the datetime row to be `FAIL` with oracle exit 0. The old path emitted `UNKNOWN` and exit 2.

**PR-body / object / archive tests (Grok MEDIUM, first half).** Closed by the three PAT tests above.

**Foreign-repository sweep (Astra MEDIUM).** Removed on purpose. `DESIGN.md:89-91` makes the GitHub done-check the delivery authority. `prepare.py:72-87` only rejects anchor `commondir`, alternates, includes, `insteadOf`, `pushInsteadOf`, `sshCommand`, and a worktree `commondir` other than `../..`.

## Still open from round 1

**MEDIUM — `test_apparatus.py:703-711`.** The bootstrap-date binding is still not tied to `0233.install`. `runner.py:63` assigns `self.frame.prepare.git = prepare.bootstrap_git`, and `0233/prepare.py:61-62` commits through that global. The test replaces `install` and commits through `p.bootstrap_git` directly (`test_apparatus.py:704-707`). `test_apparatus.py:722` only reads `HEAD`. Deleting `runner.py:63` leaves this test green, and a live install commit is dated at wall clock.

## Smoke path

Smoke and measured share `Runner.run` (`runner.py:162-228`): prepare, inherited launch, seal, archive scan, done-check, delete, 404. `runner.py:54-62` rejects overlapping roots and points smoke at `smoke_output`. Smoke slots set `measurement_eligible` false (`runner.py:174`). Costs stay in the smoke root (`test_apparatus.py:497-558`). `runner.py:145-160` makes `o01` read both smoke verdicts from `smoke_output` and refuse unless each is `PASS` or `ADJUDICATE` with `DELETED` / `404` / a manifest hash. `test_o01_refuses_missing_invalid_or_stopped_smoke_receipts` (`test_apparatus.py:591-622`) and `test_smoke_delivery_failure_keeps_cost_and_stops_codex_and_measurement` (`test_apparatus.py:625-646`) cover a missing receipt, a bad receipt, and smoke `PRODUCT_INCOMPLETE`.

## New defect

**HIGH — `0237/runner.py:201-202`, reached from `runner.py:60` and `runner.py:180`.** Measured Claude calls `boot_expectation` before prepare. With phase `measured` and no `runtime.boot_catalogs.claude.B`, it raises `measured Claude requires boot_catalogs.claude.B`. `DESIGN.md` does not define that field. Smoke uses phase `smoke`, so the same gate is skipped and a good smoke Claude run does not predict measured Claude. `o01` is Claude, so the raise stops the schedule before dispatch and the other seven slots are `NOT_RUN`. `runner.py:217-219` records only `rp-d1 instrumentation failed: ValueError`, so the verdict does not name the missing catalog. Offline tests never execute this path: `test_apparatus.py:788` and `test_apparatus.py:858` patch `boot_expectation`, and the other runner tests replace `legacy.Runner.run`.

No new PAT path into `rp-verdict.json`, `pat-scan.json`, or `rp-schedule.json`. Inherited `account`, identity, and `seal_after_teardown` stay wrapped. A correct merged PR still matches the done-check: direct acceptance, head SHA equal to the receipt SHA, merge-commit tree equal to that source tree, `CLEANUP_PENDING` when `/proc/1` is unreadable.

## Removable

Nothing else can be removed without dropping a check. `errors.tell()` on the `cat-file` stderr file shares the child's offset, so a stderr warning still fails closed.

VERDICT: REVISE
