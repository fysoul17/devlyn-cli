# s02-h-codex-v2 accounting diagnosis

Read-only raw-evidence audit. No models, authentication, tests, source edits, frozen-input changes or regrading. Whole-run STOP/PARTIAL remains unchanged.

The unresolved inference `dd112f33-b674-448a-9593-dff63fe76214` is **explicitly cancelled with missing terminal usage**, not merely a missing trace lifecycle record. It belongs to the fresh Astra peer (thread01a1263f-0580-7c32-9d49-11b8792e8494), not the outer owner. Evidence favors normal in-flight interruption to incorporate its child's answer; the exact cancellation cause and billed usage are not proven by these artifacts.

## Exact timeline (UTC)

In trace25345594-d448-4d6f-87f6-cdf414669e3a:

- Seq52,14:37:46.051: inference_started dd112f33, modelgpt-6-astra; request payload46 is `response.create`, stream=true, chained from a previous response. Client metadata request_kind=turn; no prewarm marker observed.
- Seq68,14:37:54.142: child final answer observed for tiny_rounding_check.
- Native peer rollout lines38–39,14:37:58.495–.501: reasoning item `rs_066553c3531f4efe016aca4dc68704819183613a1110cca32b` completes and is retained.
- Rollout lines42/44,14:37:58.513/.518: child message and final answer enter parent history.
- Seq69,14:37:58.519: inference_cancelled dd112f33; reason exactly `response stream dropped before provider terminal event`; upstream_request_id=null. Partial payload62 has response_id=null and token_usage=null, but contains that same reasoning item (encrypted content retained; not decoded).
- Seq70,14:37:59.012: replacement inference abab26a1 starts. Payload63 is a new full-input response.create (19 items, no previous_response_id), incorporating both the retained reasoning item and the child's final answer.
- Seq73,14:38:14.770: replacement completes with20343input/539output. The later request is a distinct inference, not evidence of usage for dd112f33.

The approximately12.468-second inference produced a retained provider reasoning item. Therefore treating this as an unused prewarm or assuming zero cost is unsupported. Temporal ordering and replacement input strongly suggest child-message incorporation interrupted the active response. The generic recorded cancellation reason alone cannot exclude a transport drop or another native cancellation cause.

## Counter reconciliation

Fresh trace has10starts,9completions,1cancellation. Its six completed primary inferences sum111854input/2162output; three child completions sum48548input/351output. Native primary rollout token counters at lines36 and40 remain byte-equivalent in usage values across cancellation:49518input/1384output cumulative and17977input/161output last-request. Thus line40 repeats the previous known usage; it is not a new dd112f33 usage receipt. At line51 cumulative becomes69861/1923, exactly adding the replacement's20343/539. At line61 it reaches111854/2162, equal to the six completed primary requests. Resumed-session later counters add separate completed requests.

Across all captured traces,34starts,33completions,1cancellation. Direct summation of33 completed payload usages yields1217463input,27994output,1107072cached input and13819reasoning output, matching usage.json's retained totals. Reasoning is a subset of output, not an additional charge. This reconciliation establishes that the collector retained the available completed-request counters; it does **not** establish total billing completeness. Missing terminal usage is omitted from both the native cumulative counter and completed-request sum, so agreement cannot prove zero residual cost.

Fresh and resumed peer completion receipts both show exit0, source_unchanged=true and retained final answer paths. The fresh native trace ends cleanly and includes events after the cancellation. This is not evidence of wholesale log truncation or a harness failure to parse an available inference_completed for this ID. A native producer limitation/defect in retaining terminal usage after cancellation remains possible; root is separately auditing that code. No terminal usage for dd112f33 was found in the inspected trace/partial payload/peer rollout. Operational completion does not repair that accounting gap.

## Evidence hashes

- `cell/trace/trace-25345594-d448-4d6f-87f6-cdf414669e3a-01a1263f-0580-7c32-9d49-11b8792e8494/trace.jsonl`: `102d2b9ec016526c369cca958d62a2594585e21492fcffe4a8463aa734cfe7fb`
- `cell/trace/trace-25345594-d448-4d6f-87f6-cdf414669e3a-01a1263f-0580-7c32-9d49-11b8792e8494/payloads/46.json`: `3a3ded43947b1cf209261656b5a4973736cd498ab6e847cd7e63b0aa71b9f72a`
- `cell/trace/trace-25345594-d448-4d6f-87f6-cdf414669e3a-01a1263f-0580-7c32-9d49-11b8792e8494/payloads/62.json`: `673539eab968ef36ca1e466417a96017e82a1f7c5538219f4d2bafc645b9dc98`
- `cell/trace/trace-25345594-d448-4d6f-87f6-cdf414669e3a-01a1263f-0580-7c32-9d49-11b8792e8494/payloads/63.json`: `83401027d0909fd1ff3b1f353f5c8e634ef2db2158745a887fd7a2f9f81e5f73`
- `home/.codex/sessions/2026/10/10/rollout-2026-10-10T14-37-06-01a1263f-0580-7c32-9d49-11b8792e8494.jsonl`: `fb054f1f3e7d537a5f04b82ca7d91703b85c1cf6cf99807a67de8435511b3abe`
- `usage.json`: `7ea517e682ae80b6f9730d8ac80d428c87ff9cf5edb266111c3bfce177ad3cf4`
