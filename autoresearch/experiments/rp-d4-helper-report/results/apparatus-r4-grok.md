**(a) The helper printer and the native files agree.** `main` prints both the normal return and the `BLOCKED` object with `json.dumps(result, sort_keys=True)`, which uses the default `": "` separator. `merge_refused` is set only by `result("PR", merge_refused=refused)` when `refused` is a non-empty string, so the value is a JSON string. The same two lines are in `.agents/skills/_shared/task-complete.py`. A captured Codex `command_execution` already stores that printer's stdout inside `aggregated_output` with spaces preserved (`0242/fixtures/retained-helper-events.json`).

| File | What it stores | Bytes on disk |
|---|---|---|
| `run/stdout` | Claude `stream-json` `tool_result.content`; Codex `--json` `aggregated_output` | once-escaped `\"merge_refused\": \"` |
| `home/.claude/projects/**/*.jsonl` | same stdout in `content` and `toolUseResult.stdout` | once-escaped |
| `home/.codex/sessions/**/*.jsonl` | `aggregated_output`; code-mode `custom_tool_call_output` text | once-escaped, or twice-escaped `\\\"merge_refused\\\": \\\"` |
| `cell/trace/**` | protocol payload JSON, `aggregated_output` as a string | once-escaped; raw payload bytes match the plain form |

`merge_refused` scans those paths and those three spellings. Claude API bodies are included when sealed; this launch does not enable them. Subagent jsonl files under `projects/` are included. `sort_keys` puts `merge_refused` before the long `receipt` and `resume` fields, so a later poll that holds only the tail is not required for a hit.

**(b) Benign bytes do not match.** Repo-wide, the plain spelling occurs only as the scanner's own literal in `smoke.py`, which is not installed in the cell. `task-complete.py` and `task-completion.md` (config and `.agents`) use `merge_refused=refused` and `` `merge_refused` ``, and the self-tests use `result["merge_refused"]`. Receipts are `atomic_json` documents and never gain this key. `cat` or `rg` of those files, including two JSON wraps, stays clear in `test_real_helper_source_and_instructions_do_not_trigger`. A real refusal is the printer above, which is the hit the gate wants. A hit sets `PRODUCT_INCOMPLETE`; `decision` then stays `INCONCLUSIVE` because `merge_refused is False` is required before any adoption branch.

**(c) Bad evidence stops.** The seal manifest must exist, list `run/stdout`, and have an empty `failures` list. Each scanned file is hash-checked before the scan continues, so a later missing, unreadable, or changed file still raises. Empty stdout raises. `runner.run` catches that and sets `STOP` with `helper evidence qualification failed`, which `decision` treats as `INCONCLUSIVE`.

**(d) The rest of the gate is unchanged.** Y-smoke `qualify` still matches sealed action records to reconstructed stdout and rejects a `merge_refused` key there. Measured and guard slots do not use the observer. Schedule, credential scan, and the ordered decision (ten slots, deliveries, reviews, `COMPLETE` usage, then BASELINE MOVED, REJECT, ADOPT, HOLD, MIXED under the 0232 §6 cost rules) are the same.

The suite was not executed in this session. The conclusion is from the current sources, the retained helper event, and the refusal tests as written.

VERDICT: SHIP
