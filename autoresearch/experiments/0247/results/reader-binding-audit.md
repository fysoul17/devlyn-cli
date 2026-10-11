# 0247 reader-binding audit

Read-only implementation support against the actual 0245 import chain and retained 0246 d05 bytes. No tests, native/model/auth calls, source edits or historical regrade.

**The proposed two reader bindings cover owner stdout and canonical peer captures. Two additional live aliases also lose actual d05 rollout records and should use the LF reader.** No parser framework or changes to historical files are needed.

## Actual chain and minimal bindings

Runner inheritance is 0245 → 0244 → 0242 → 0241 → 0240 → 0238 → 0237. After all inherited initializers:

- `frame.cell_run` is `0238/cell-init-v1.py`.
- Its `legacy` is `0234/cell.py`; its `base` is `0222/cell.py`.
- Its `evidence` is the private `0234/evidence.py` instance shared explicitly with `frame.usage.evidence`.
- `frame.usage` is `0234/record_usage.py`; its independent `base` is `0222/record_usage.py`.
- 0244's initializer finally binds `evidence.claude_envelopes` to `partial(0244.capture_discovery.claude_envelopes, evidence=evidence)`.

Apply prospective overrides **after super().__init__**:

| Receiver | Why it is active |
| --- | --- |
| `evidence.lines` | Inventory/native rollouts/transcripts and stdout use module-global lookup. Usage peer captures and launch inventory, 0238 Claude accounting, and 0242 peer policy call this shared object. |
| `frame.cell_run.lines` | 0238 run passes these parsed stdout rows to `base.final_message`; inherited startup catalog extraction also calls this receiver. |
| `frame.cell_run.legacy.lines` | `identity = legacy.identity` is a function alias, so its globals remain in 0234/cell.py. Its native-rollout reroute scan at line 77 looks up this separate name. Rebinding only the outer cell's lines does not reach it. |
| `frame.usage.base.events` | 0234/record_usage.py:42 reads Codex rollout counters through this independent 0222 reader; codex() calls rollout_counters() at line 101. |
| `evidence.claude_envelopes = partial(new_discovery.claude_envelopes, evidence=evidence)` | Replaces 0244's installed partial. The new copy's inline output loop must split LF; its outer stdout traversal already uses evidence.lines. |

There is **no additional required `frame.cell_run.base.lines` binding** on this execution path. 0222/cell.py's `final_message(events, engine)` consumes supplied rows and does not call its own lines function. Its historical native_identity/run bodies are not invoked by the 0238 cell run. Changing base.lines alone would also not repair the already-bound 0234 legacy.lines alias.

Likewise, `evidence.usage0222.own_events` receives parsed rows from evidence.lines; no separate events reader is called there. Sharing evidence across identity and usage is already explicitly checked by 0241/0244 and must remain intact.

## Exact retained rollout proves the extra scope

File: `/Users/aipalm/.local/share/nx01/0246-live/out-measured/d05-f23-claude-p/home/.codex/sessions/2026/10/10/rollout-2026-10-10T19-50-54-01a1275e-4c9a-7051-a198-8bdc92dfb9b9.jsonl`

SHA-256: `f2ab7ecea59fa2fc2639a5492a08578217c8614665a1d7466c09f9ffbbd1686f`; 480,715 bytes.

Parsing unchanged retained bytes gives **101 valid LF-delimited records**. Python splitlines produces **103 pieces**, of which only **99 parse as dict records**. There are exactly two literal U+2028 occurrences:

- LF record 72: `event_msg / item_completed`.
- LF record 74: `response_item / custom_tool_call_output`.

Both active old rollout aliases therefore drop real recorded events. These are not model, reroute or usage-counter records, so this observation **does not imply an identity or accounting-total error in d05**. It supports the two additional explicit reader bindings without broadening into unrelated trace parsing.

The canonical d05 peer capture separately has 56 valid LF records versus 57 splitlines pieces; this is already covered by evidence.lines and the helper's LF fix.

## Startup identity and expected catalogs

Model enforcement remains separate from repeated-init normalization:

- 0234/cell.py:85–96 compares Claude's observed init model to the prepared plan's model, checks reported owner models and observed effort. Codex trace/rollout identity and per-inference model checks remain in the same function.
- 0242/policy.py validates actual peer models/efforts, each Codex native configuration and turn context, reroutes, capabilities and Claude tool use against registered routes.
- 0238/runner.py:167–178 checks identity, peer policy and COMPLETE accounting before startup catalog extraction, then compares its returned normalized catalog with the run's frozen expected catalog.

Therefore the new extraction can validate **every init** for nonempty string session_id/model, consistent identity, explicit list-shaped skills/plugins/mcp_servers and consistent normalized catalogs, then return the one agreed catalog for the **existing single frozen expected-catalog comparison**. It must not silently select a favorable init. Nonidentity fields such as cwd/uuid can differ as d05 actually shows. A consistent but wrong model is still rejected by unchanged identity enforcement; duplicate expected-model logic in catalog extraction is unnecessary.

## Boundary retained

All actual helper-path owner stdout, canonical peer captures, native identity, final message, boot, peer policy and Claude-accounting reader bindings are covered above.

One distinct legacy path remains outside this repair: 0234/record_usage.py dynamically loads diagnostics and calls its `output_envelope` for a direct `claude -p` launch with no saved capture; that extractor still uses splitlines. It is not the observed d05 helper route and cannot be fixed by changing the already-loaded discovery diagnostics object. Diagnostics also has independent readers for trace timing/reporting. Do not silently claim those unrelated paths were repaired or introduce a loader-wide patch for them.

The targeted fix needs explicit receivers, not recursive module rewriting. This audit wrote only this note and performed no new behavioral experiment.

