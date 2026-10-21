**Fix round 1 is complete.** I observed the regression tests fail before the behavior fixes and pass afterward. For the already-correct cutoff and renewal boundaries, I confirmed the new tests fail against temporary faulty variants, then restored the code.

| Item | Test | Before → after |
| --- | --- | --- |
| 1. Verdict statuses | `test_product_incomplete_verdict_loads` | `PRODUCT_INCOMPLETE` was unresolved → loaded as a failed product. |
| 2. Decisions file | `test_unreadable_decisions_are_named_gaps_for_every_panel` | Missing file raised → every panel reports `NOT_FINISHED` with a named gap. |
| 3. Strict gain | `test_strict_gain_condition_in_every_reading` | Cost reading omitted `strict_gain` → false or unknown gain is listed. |
| 4. Window resets | `test_window_jitter_and_reset_crossing_estimates`, `test_split_wait_ignores_reset_jitter_but_releases_on_real_reset`, `test_estimates_exclude_reset_crossing_sample` | Jitter split one window and released a wait → sub-600-second jitter stays in one window; reset-crossing samples are excluded. |
| 5. Renewed token | `test_renewal_threshold_and_fresh_window_token`, `test_claude_limits_accepts_access_token`, `test_credential_snapshot_carries_window_token` | Readiness queried with the saved old token → it uses the renewed keychain token and proceeds. |
| 6. Image check | `test_image_mismatch_is_not_dispatched` | Wrote STOP, return 2 → writes a hold, return 3. |
| 7. Telemetry | `test_after_grading_telemetry_error_keeps_verdict` | `TimeoutError` escaped → error is recorded and the COMPLETE verdict is writable. |
| 8. Transcripts | `test_synthetic_and_unbound_hook_progress_are_ignored`, `test_bound_retry_before_assistant_takes_model`, `test_native_subagent_sessions_reconcile_to_owner`, `test_usage_attribute_error_is_recorded_not_raised` | False gaps or `AttributeError` → healthy owner and child reconcile to COMPLETE; recording errors remain in the verdict. API events and independent sessions also have explicit gap tests. |
| 9. Cache cleanup | `test_models_cache_timeout_reaps_container` | Timeout left no reap call → named container is reaped in `finally`. |
| 10. Test strength | `test_assessment_snapshot_1500_second_cutoff`, `test_renewal_threshold_and_fresh_window_token`, `test_estimates_exclude_reset_crossing_sample` | Temporary incorrect cutoff, threshold, and reset logic each failed its test → restored behavior passes. |

[README.md](/Users/aipalm/Documents/GitHub/devlyn-cli.devlyn.noindex/0256-package-replay/autoresearch/experiments/0256/README.md) reflects the changed roles. Final offline check: **39 passed, 5 subtests passed in 1.86s**; pyflakes clean. No commits were made.

The persistent-memory write was rejected because that MCP action requires approval and this session’s approval policy is `never`; it did not affect the repository work.
