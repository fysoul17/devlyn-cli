Round 2 finds the round-1 defects fixed in the current tree. No new defect would invalidate or unsafely grade a live run.

`git diff HEAD~1` and the README pytest loop were not executed: this session has no shell or pytest tool (only Telegram MCP). The review is of the working tree as read. Worktree `HEAD` is `253a2ffd` (`wip: rp-d4 apparatus r1 fixes`), parent `14a4c6fc` (`wip: rp-d4 apparatus (Astra)`), from the worktree `logs/HEAD`. This is not a green-suite claim. Memory tools were unavailable.

## Round-1, fixed in the current sources

| Round-1 | Where it is closed |
|---|---|
| Astra/Grok **HIGH** — Claude bearer not scanned before seal | `runner.scan` runs the rp-d3 Codex scan, then for `auth_engine == 'claude'` reads `CLAUDE_CODE_OAUTH_TOKEN` and reuses the streaming/filename/symlink/git scanner. A hit or failure writes only `{status: STOP, revocation_required: true}` to `claude-scan.json` and raises a fixed string with `from None`. `Runner.run` points seal and the cell at `auth.for_engine(...)` before launch and forces `STOP` if `codex-scan.json` or `claude-scan.json` exists. Covered by `test_guard_selected_snapshot_is_scanned_before_sealing`, `test_claude_leak_stops_guard_and_remaining_schedule`, `test_claude_scan_failure_is_nonsecret_and_closed`, `test_clean_snapshot_scan_allows_sealing`. |
| Astra **HIGH** / Grok **MEDIUM** — unrecognized helper launches dropped `merge_refused` | `shell_complete` / code-mode parsing raise `helper command cannot be classified` for variable paths, `env` wrappers, process substitutions, `python -c`, depth > 4, and `shlex` failure. A later success cannot clear that. Echo and `--help` stay non-invocations. Covered by `test_ambiguous_shell_invocations_stop_even_before_a_later_success`, `test_compound_shell_separators_cannot_hide_refusal_after_echo`, `test_code_mode_unparsed_helper_forms_preserve_refusal_detection`, `test_merge_refusal_survives_a_later_success`. |
| Astra **MEDIUM** — spare consumption stuck in one stage directory | Registry is `~/.devlyn/rp-d4-runs/<run-id>/attempt-{1,2}.json`. Attempt 2 requires attempt 1 `FAILED`, identical arms/image/accounts/models cache, and archived deletion/404. Exclusive create. Revocation or a failed spare sets `STOP`. Measured staging binds the qualifying attempt's stage. Covered by `test_spare.py`. |
| Grok **LOW** — observer could change the helper | `observe` catches `Exception` and returns. `test_observer_failures_leave_helper_return_and_locals_untouched`, `test_actual_python_profile_observes_unmodified_helper_return`. |
| Grok **LOW** — missing `merge_refused` treated as false | `decision` requires `merge_refused is False`. Missing is `INCONCLUSIVE`, including on a guard. `test_inconclusive_precedes_baseline_moved` covers `missing_merge_refused` and `guard_missing_merge_refused`. |

## Checked, no new finding

**Arms.** X is a byte copy after SHA-256, `sha512-` integrity, and `package.json` `devlyn-cli` `4.2.22`. Y repacks exactly `config/skills/_shared/task-complete.py` and `config/skills/_shared/task-completion.md`; both must change; manifests, type, mode, and member metadata/order stay aligned except those sizes; Y blob ids must match the local commit. `package/../`, absolute paths, and `package/./alias` are rejected. `binding` checks every installed copy at prepare and again in `bound_launch`. The observer is installed only for Codex SM smoke arm Y, and `/harness` is prepended only then. Measured and guard plans stay on `src:/control/python`.

**Schedule.** `m01`–`m08` are BV X,Y; BV Y,X; Z0 X,Y; Z0 Y,X, then `g01` BV Y and `g02` Z0 Y. Repository names are `fysoul17/rpd4-<run-id>-` plus those fourteen suffixes. `--through-pair` is 1..4 and pauses on the Codex prefix; omitting it runs both guards as one block. Renewal is only at completed counts 0, 2, 4, 6, and 8, with the same Codex account, the same Claude account, and the same Codex identity inside the Claude snapshot.

**Credentials.** Docker argv uses `--env-file` for `claude.env`, mounts `codex.json` by path, and records `create_argv` without the bearer. Inspect requests `.State`. Plan env rejects `ANTHROPIC_`, `CLAUDE_CODE_OAUTH_`, `CLAUDE_CODE_REMOTE_`, and the subscription/tier keys. Codex preflight does not call Claude `profile`. The 6300 s floor runs in Claude preflight, and at renew only when the Claude snapshot path changes. An unchanged Claude path is checked again at guard dispatch.

**Decision.** `summarize.decision` follows DESIGN order: `INCONCLUSIVE` unless all ten slots are dispatched, every delivery passed, both reviews are PASS or FAIL, usage is `COMPLETE`, and `merge_refused is False`; then BASELINE MOVED, REJECT, ADOPT, HOLD, MIXED. Cost matches 0232 §6: `S_Y = 0` fails, `S_X = 0 < S_Y` is dominance with no raw-sum comparison, otherwise each of wall, input, and output per success is Y ≤ X over every dispatched Codex attempt, failures included. Strict improvement is `S_Y > S_X` or one strictly lower per-success cost; three-way ties HOLD. A missing wall on a required comparison is `INCONCLUSIVE`. `FALSE` from either reviewer on any Y slot, including the guards, blocks ADOPT. Guard pass is both guards and all four categories SUPPORTED by both reviewers. Codex tallies exclude smoke and the guards. The offline tests, as written, lock those branches.

No new findings.

VERDICT: SHIP
