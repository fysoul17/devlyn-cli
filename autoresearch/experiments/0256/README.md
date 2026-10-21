# 0256 apparatus

Run `python3 -m pytest -q autoresearch/experiments/0256` offline. Freeze current D3/D4 issues with `snapshot_issues.py`, then supply its override to preparation (default `tasks-override.json`, or `runtime.tasks_override`). The owner supplies the verified package cache, frozen image, models cache, auth, and runtime paths before dispatch. Run `driver.py` under `caffeinate -dimsu` with `smoke.tsv` then `cells.tsv`.

| File | Origin | 0256 delta |
| --- | --- | --- |
| `control.py` | 0233 | Published B tarball, npm integrity and sha256; no C or pack |
| `prepare.py` | 0233 | A/B, issue override, account context exclusions, trust rewrite, final boot digests, working tree set to the committed baseline modes |
| `snapshot_issues.py` | new | Raw current issue freeze and override |
| `models_cache.py` | 0233 `codex_limits` | Pinned-image cache generation; named container always reaped |
| `cell.py` | 0237 `cell-init-v1.py` | Imports unchanged `run` |
| `record_usage.py` | 0233 | Claude terminal/envelope reconciliation, native child folding and lower bound |
| `generate_cells.py` | 0233 | Two-arm order; 56 measured and four smoke cells |
| `cells.tsv`, `smoke.tsv` | 0233 | Generated 0256 registration |
| `decide.py` | 0233 | B/A readings per panel and configuration, missing evidence report |
| `run_cell.py` | 0233 | Image dispatch hold, extended seal, assessor credential hold, windows |
| `driver.py` | new, 0233 run protocol | Serial hold, renewal, fresh-token window reserve and retry handling |
| `calibrate.py` | 0233 | Imports unchanged overlay runner |
| `test_apparatus.py` | 0233 | Offline two-arm contract tests |
| `tasks-override.json` | new | The registered D3/D4 issue snapshots (`snapshot_issues.py` output) |
| `restore_i0185.py` | new | Restores I0185's inputs from Git history into the run worktree and verifies 0233's seals |
| `direct_run.py` | new | Owner-directed serial run without the floor reserve (registration amendment) |
| `registration.md` | new | Frozen identities, owner amendments and SMOKE qualification |

Claude Code 2.1.281 transcript assumption: an assistant JSONL row with a non-null `message.stop_reason` has terminal `message.usage`; earlier copies of the same `message.id` may be provisional. Native child rows may share the owner's `sessionId` or carry `parentSessionId`. Owner `stream_event` progress binds from `message_start.message.id` through `message_stop`; unbound API retry, error or abort makes usage UNKNOWN, while id-free hook progress is ignored. Renewal requires runtime `renewal_command` as an argv array containing `-p --tools '' --strict-mcp-config --mcp-config '{"mcpServers":{}}'`; its flags are checked against host `claude --help` before use. Runtime `caps` has numeric `seven_day` and `five_hour` percentages. No model or Docker run is needed for unit tests.
