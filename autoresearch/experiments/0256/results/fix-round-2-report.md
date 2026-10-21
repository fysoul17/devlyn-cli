Fixed all seven round-2 items in `0256/`. The regression tests are in [test_apparatus.py](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/test_apparatus.py). The changes follow **No workaround** and **No guesswork**: they repair the accounting and dispatch rules, with the failing behavior observed before the fixes.

| Item | Test | Before → after |
|---|---|---|
| 1. Conflicting terminal copies | `test_folded_conflicting_terminal_copies_use_counter_minima`; `test_folded_conflict_uses_minimum_for_each_counter` | Folded 9/2 copies gave bound 9 → bound 2, `UNKNOWN`; each counter uses its minimum. |
| 2. Folded placeholder | `test_folded_child_fills_owner_event_placeholder_model` | Raised `AttributeError` on `None` → model `m`, input 2, no gaps. |
| 3. Paired witness evidence | `test_reproduced_witness_requires_explicit_paired_result` | Missing paired result gave `PACKAGE_LOWERS_QUALITY` → named gap and `NOT_FINISHED`, in both directions. |
| 4. Regrade telemetry | `test_regrade_replaces_inherited_claude_telemetry` | Old `claude_limits_after` survived a failed query → only the new error remains; a successful query replaces both old fields. |
| 5. Expired token renewal | `test_expired_and_expiring_tokens_skip_old_profile_before_renewal` | Old-token 401 blocked renewal → the old profile is skipped and the renewed token is checked. |
| 6. Renewal command faults | `test_renewal_command_fault_rechecks_keychain_and_holds_only_if_needed` | A timed-out renewal could stop the driver without rechecking → timeout and `OSError` both recheck; advanced matching credentials proceed, otherwise the owner hold retains the attempted expiry. |
| 7. Network fault holds | `test_preflight_profile_timeout_is_not_dispatched`; `test_preflight_usage_and_codex_query_oserrors_are_not_dispatched`; `test_driver_profile_and_window_timeouts_are_holds` | A preflight profile timeout escaped → preflight profile, usage, and Codex query faults return rc 3 with a reason; driver profile and window faults hold. |

Final checks: `49 passed, 11 subtests passed` from `python3 -m pytest -q autoresearch/experiments/0256`; pyflakes clean. No files outside `0256/` were edited, and no Git delivery action was taken under the build contract.
