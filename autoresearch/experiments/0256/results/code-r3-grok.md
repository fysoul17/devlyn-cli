I'll confirm the round-2 fixes against the design and the two review reports, without editing anything. First I'll load the spec, the findings, the fix contract, and the executor report.The seven contract items are mapped. I'll read the fixed modules and the tests that claim to cover them.No HIGH, MEDIUM, or LOW findings.

All seven round-2 items are fixed. Each new test fails on the old behavior.

Conflicting terminals (`record_usage.py:145`, `:217`) keep per-counter minima and a disagree gap. `test_folded_conflicting_terminal_copies_use_counter_minima` requires bound 2 and UNKNOWN for folded inputs 9 and 2; `test_folded_conflict_uses_minimum_for_each_counter` checks every counter.

An owner event placeholder takes the folded child model (`record_usage.py:213`). `test_folded_child_fills_owner_event_placeholder_model` expects input 2 and no gaps. The old path raised `AttributeError` from `None.split`.

A reproduced witness needs an explicit bool on the paired cell, in both directions (`decide.py:91`). A missing entry makes that panel NOT_FINISHED. `test_reproduced_witness_requires_explicit_paired_result` loads real verdict rows; the old omission became PACKAGE_LOWERS_QUALITY.

`grade` clears inherited `claude_limits_after` and its error before the new query (`run_cell.py:259`). `test_regrade_replaces_inherited_claude_telemetry` fails while either old field remains, so `estimates` sees only the new sample.

Tokens with at most 300s left skip the profile and renew (`driver.py:93`). `test_expired_and_expiring_tokens_skip_old_profile_before_renewal` returns 401 for the old token, both expired and at 300s, and profiles only the renewed token. That 401 used to hold before `claude -p`.

Renewal `TimeoutExpired` and `OSError` are caught, then the keychain is rechecked (`driver.py:172`). `test_renewal_command_fault_rechecks_keychain_and_holds_only_if_needed` covers both faults: an advanced matching token continues; otherwise the attempted expiry stays and the owner hold is recorded.

Profile, usage, and Codex `OSError`s, including `TimeoutError`, return rc 3 (`run_cell.py:91`, `:97`, `:101`). The same faults from `credential` or the window query hold (`driver.py:154`, `:192`), covered by the three timeout tests.

After renewal, fingerprints must match the sealed account (`driver.py:179`). The fixes match DESIGN.md.

SHIP
