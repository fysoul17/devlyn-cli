# 0248 d10 partial-usage and process audit

Prospective read-only prediction, 2026-10-10T23:13:24.247784+00:00: the flagged inference must be traced to its native start and terminal events before attributing a cause. A cancellation or provider failure without usage leaves whole-run usage unknown even if the owner exits zero; a retained authoritative completion would instead identify a reader/accounting defect. Preserve STOP/PARTIAL, count only supported lower bounds, and do not replay tests or evaluate product behavior.

## Diagnosis

The original **STOP / PARTIAL** is supported by an explicit native failure event. It is not a demonstrated usage-parser bug. The owner eventually exited zero, but that does not supply usage for a failed inference.

In `cell/trace/trace-0a1c3c5e-475f-4114-8458-c91a821045e2-01a12810-e397-7633-afc5-13c7882a1eb4/trace.jsonl`:

| Event | LF | UTC |
| --- | ---: | --- |
| Inference `6d82b8a7-dc63-4201-98b3-dc45b2359694` starts; request payload36 | 40 | 2026-10-10 23:06:17.704 |
| Same inference fails | 41 | 23:06:26.253 |
| New inference `883fc15b-2727-4595-a451-8a54d7f845b1` starts; payload37 | 42 | 23:06:26.997 |
| New inference completes with usage; payload40 | 46 | 23:06:47.649 |

The failed event says **“stream disconnected before completion: websocket closed by server before response.completed”**, with `upstream_request_id=null` and `partial_response_payload=null`. It lasted 8.549 seconds from start to failure. This directly establishes a stream/server-close failure and absent completion, not a cancellation. It does not establish why the upstream server closed, whether work was billed, or that authentication/quota caused it.

The trace ends with completed turn/thread/rollout events at LF163/166/167. Thus native recovery let the task continue, while accounting for the failed attempt remained unavailable. Preserve **381.6193476660119 s**, owner **EXITED_0**, identity MATCH, teardown CLEAN, and whole-run input/output **null**. Do not subtract the failed interval from elapsed cost.

## Known usage and recovery limit

All 167 trace records parse as JSON. LF framing and the inherited splitlines reader see the same 167 records; no literal U+2028/U+2029/U+0085 occurs in that stream. There are **15 starts, 14 completions and one inference_failed**. All 14 retained completion response payloads have native counters.

The independent sum is:

| Counter | Known lower bound |
| --- | ---: |
| Input, including cached input | 564,624 |
| Cached input, already included above | 496,512 |
| Cache write input | 0 |
| Output, including reasoning | 17,725 |
| Reasoning output, already included above | 7,771 |

The sum exactly equals both the final native rollout token_count (LF149) and stdout turn.completed (LF57), including each component counter. Those cumulative values add no independently recorded residual for the failed attempt. Counting cached/reasoning tokens again would double count; treating the totals as complete would silently assign unknown failed-attempt usage to zero.

The inherited `0232/trace_usage.py` sets usage only upon inference_completed with valid counters, then emits “started without completed usage” for an unresolved call (lines84-85). That is the observed case. No retained authoritative completion or partial-usage payload allows recovery. Request length, elapsed time, a subsequent successful inference or final task success cannot recover the missing counters. This diagnosis requires no collector loosening or product regrade.

## Native identity and observed S check

Session **01a12810-e397-7633-afc5-13c7882a1eb4** is the single root thread, with no native children or experimental peer activation. Native session_configured and all **15 actual request payloads**, including the failed and subsequent calls, consistently specify **gpt-6-astra / max**. No substituted model is observed.

The owner reads AGENTS.md at stdout LF10/11 and the installed S `_shared/pair.md` at LF13/15. This file is titled “Counterexample check” and calls for an additional executable witness in the owner's own session. The recorded activation is LF37; the concrete check is executed at LF42/43:

`node --test --test-name-pattern='fulfill-wave rolls back repeated lot use' tests/cli.test.js`

The retained source test (line203) uses two four-unit lots. An earlier accepted order consumes one; another order tentatively consumes one twice from the same lot, then fails a five-unit single-warehouse line. The expected rollback restores only those two tentative deductions, allowing the following order to consume the remaining seven as3+4. The targeted test records exit0, one pass; LF44 reports no supported violation. This documents activation and actual execution, not the adequacy or general effectiveness of the S guide.

Other owner outputs show baseline3/3, a predicted red accepted-allocation check before implementation (unknown command; LF28), later55/55 and final59/59 (11 top-level plus48 nested; LF48). The owner corrects fixtures that serialized Infinity as null before that final run. These are process observations only.

## Preserve STOP and local observations

The owner records local commit **d7d15874f1a424190c05ca84e6dab4962d235ebb** and a clean working tree in LF52-55, listing only `bin/cli.js` and `tests/cli.test.js`. That is retained owner output, not an independent delivery verdict. The normal post-STOP artifacts `checked.json`, `checks.json`, `checks-raw.json` and `delivery.json` are absent. No source, public, hidden-oracle or delivery assessment was run or inferred by this audit.

The initial protected set covers **172** source, guide, raw, trace/payload, native rollout and frozen registration files. Every before/after SHA256 matches; the JSON companion contains the complete binding. The prospective prediction above remains unchanged. Only this report and its JSON companion were written. No further writes are planned.
