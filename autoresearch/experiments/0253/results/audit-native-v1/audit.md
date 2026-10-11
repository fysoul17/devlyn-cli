# 0253 native receipt mechanism acceptance audit

**SHIP — zero HIGH findings**, scoped to this one observed successful operational probe. The prospective prediction was saved before native-file inspection. Twenty receipt-metadata checks and 26 custody checks passed.

Exactly three requests, three terminal responses and three index rows bind without orphan files, duplicate index identifiers or conflicting terminal metadata. There are two owner requests and one foreground same-model child request. Each index entry matches its request/response file, native request id, message id and terminal message UUID in the owner or child transcript. Request metadata uses the same session and its account hash matches the frozen runtime account; raw account identifiers are not published.

| Role | Native request | Input | Cache creation | Cache read | Output | Thinking included | Stop |
|---|---|---:|---:|---:|---:|---:|---|
| owner | req_011CfurzKHhVhPtAvLZ6ydK8 | 2 | 18189 | 0 | 394 | 230 | tool_use |
| child | req_011CfurzesgM8TjeEoxtL4KQ | 2 | 12264 | 0 | 59 | 44 | end_turn |
| owner | req_011CfurznsdsWqXySYsBJ4pF | 2 | 665 | 18189 | 15 | 0 | end_turn |

All three terminal receipts sum to **49,313 input tokens and 468 output tokens**, including 274 thinking tokens. The native `modelUsage` aggregate matches every counter. Native top-level `result.usage` is owner-only: 37,047 input, 409 output and 230 thinking; it must not be interpreted as the whole owner-plus-child aggregate. Native emitted list-price cost is $0.2619658, not provider billing evidence. No residual was inferred.

Exactly one Agent tool call specifies `general-purpose`, `run_in_background=false`, no model override, and the exact registered child task. Task start, child metadata, terminal transcript, completed notification and parent tool result all link the same tool/agent ids. The child uses no tools and returns the required sentinel before the parent returns its sentinel. Both child metadata (`requestShape=foreground`) and lifecycle completion corroborate foreground execution. No extra invocation, retry, request error or cancellation is observed. One rate-limit event is `allowed_warning` at 94% five-hour utilization; it is not an execution refusal and no overage is used.

All request bodies specify `claude-opus-5-5` and `output_config.effort=max`. Plan and recorded argv preserve the pinned image, B configuration, 5,400-second watchdog, fixed authentication and original lifecycle. The official native file exporter is configured, with metrics/logs/traces remote exporters all `none`. This verifies configuration, not a network traffic trace.

All 126 bindings, four reviewed file hashes, five prepared seals and 2,048 raw manifest entries match. The seven native body/index files are all sealed. The raw manifest's defined scope excludes 31 other regular files and two symlinks, separately inventoried in custody v2; it is not claimed to seal the entire output tree. Owner exit is `EXITED_0`, identity `MATCH`, elapsed 11.085199 seconds, teardown `CLEAN`; read-only live checks confirm the recorded container and temporary volume are absent. Recorded fixed-auth admission had 8,400 seconds remaining.

Exact evidence:

- Raw evidence manifest: `3b9c1a8bf178ec5d1f004f84f874f951f5eb6906ceb397f08b9e190951eabf86`
- Native receipt metadata report: `59a204b606c0efd70b142174300fdeba6ba8fa273b76151163a9c790c9e4be2e`
- Corrected custody report: `9c1a77bf8e45d1c5db7ca64f18fab8b5099cb349fc63c8a20cb84b18e50e0faa`
- Prospective audit prediction: `8e7265269efd453af3bce8f63f38818f9d3fa99282f2897e0bd3645109b589ac`
- Detailed final audit JSON: `cd9d2d32632d71d1646272d8115c5cecb4334eb1b289161b7d844932e2aa593f`

The custody subcheck initially imposed an unsupported extra requirement that the test file also be runtime-bound; its actual bytes are bound by the frozen code review, and the three runtime files are directly bound. Original reports remain preserved with an explicit correction; no source/evidence mismatch occurred. An initial metadata print included the already-public operational prompt in argv; no provider request/response payload or credential contents were exposed.

This establishes **native file receipt coverage for this successful owner and foreground child only**. It does not reproduce or resolve d07's interior transcript gap, prove error/retry/cancellation capture, establish spontaneous foreground behavior, or admit any efficacy/product change. Previous STOP is immutable. No new parser or gate precedence is accepted. No credential contents, provider/model call, test or source/oracle/delivery grading was used in this audit.
