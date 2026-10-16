`merge_refused` is now any receipt-bound helper result in native tool output whose `merge_refused` value is not null. The command string is not consulted. A later success is another result in that set, so it cannot clear an earlier refusal.

## Round-2, closed

| Round-2 | Where it is closed |
|---|---|
| **HIGH** — sourced variables, wrappers, and a trailing `# --help` dropped a refusal | `complete_outputs` keeps every Claude `tool_result` and every Codex `item.completed` `aggregated_output`, then `json_objects` walks envelopes (`output`, `stdout`, `content`, `text`, nested strings, lists). A result counts only with this slot’s receipt, `delivery_status` in `COMPLETE`/`PR`/`PENDING`/`LOCAL_ONLY`/`FAILED`, and `status` of that value or `CLEANUP_PENDING`. `carriers` covers `command_execution`, `exec_command`, `shell_command`, Claude `Bash`, and `functions.exec` for `source …; python3 "$helper"`, a trailing comment, and `/tmp/finish-task`. `test_merge_refusal_survives_a_later_success` and `test_multiple_results_in_one_tool_output_keep_refusal` keep the refusal after a later `COMPLETE`. |
| **MEDIUM** — `rg`/`grep`/`cat` of `task-complete.py` raised `helper command cannot be classified` and the runner turned that into STOP | Those outputs are not receipt-bound result objects. `merge_refused` returns false and does not raise, so `runner.run` does not take the qualification `except` path. `test_source_inspection_interleaved_with_completions_does_not_stop` covers both engines and code mode between real completions. |

The live helper object matches the filter. `completion_result` prints `receipt` as `Path.absolute()` (`task-complete.py` around the `completion_result` return), and a refused merge is `result("PR", merge_refused=refused)` with that key set only when the reason is non-empty. A captured `command_execution` already carries that JSON in `aggregated_output` after a Python heredoc wrapper (`0242/fixtures/retained-helper-events.json`). Checklist receipts are `cell/work/.git/devlyn-completion/<id>/receipt.json` (`0231/locate.py`), which `receipt_matches` maps from `/cell/…`. The same three roots cover `/tmp` and `/home/participant`.

## Checked, no new finding

**Refusal stays.** `any(result.get('merge_refused') is not None …)` spans every bound result. Split polls rejoin only on a literal `session_id` or `cell_id`; each piece is still scanned on its own, so a complete object in one tool result does not depend on the join. Code-mode `write_stdin({session_id: N})` and `functions.wait` are included. Assistant prose is not a tool result.

**Ignored noise.** Another receipt fails `receipt_matches`. Echo text, broken JSON, a receipt without `delivery_status`, and a status that disagrees with `delivery_status` never enter the set. `BLOCKED` and `ALLOCATED` prints, including `allocate`’s `reconciled` entries for other receipts, lack this slot’s delivery shape. The on-disk receipt uses `delivery`, so reading that file does not look like a completion result.

**Fail closed.** A missing, empty, or torn `run/stdout`, a non-string `aggregated_output`, or a torn owner trace raises. `runner.run` catches that and sets `STOP` with `helper evidence qualification failed`. `decision` treats `STOP` and a missing `merge_refused` as `INCONCLUSIVE`.

**Rest of the apparatus.** The Y-smoke observer is still a read-only `sys.setprofile` on `complete`, bound to the helper hash, and swallowed on its own failure. `qualify` still requires sealed action records, the rendered sentence, resource agreement, stdout equal to those returns, and no `merge_refused` key. `decision` is unchanged: ten dispatched slots, every delivery passed, both reviews adjudicated, usage `COMPLETE`, and `merge_refused is False`, then BASELINE MOVED, REJECT, ADOPT, HOLD, MIXED, with the 0232 §6 cost rules.

The suite was not executed in this session. The conclusion is from the current sources and the retained native event shape.

VERDICT: SHIP
