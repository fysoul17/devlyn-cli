# Prospective v5 Claude accounting closure

Research apparatus only. The observed d01/0239 failure is a parent inference that
emitted progress, lost its connection and retried without a retained terminal
usage carrier. The native aggregate reports more cost than completed transcripts,
then reports COMPLETE; that label does not establish full interrupted-stream cost.
No old verdict, usage, cell, 0234/0237 source or frozen 0239 input is modified.

Before editing, all seven v4 review files and its manifest were copied verbatim
to `apparatus-v4/`. The already-reviewed staging dependency fix and its test were
also preserved there. `apparatus-v4/manifest.json` binds those bytes. The v4 native
pair dependencies still match their original hashes.

## Smallest integration

`claude-accounting-v1.py` reads retained Claude results and native transcripts,
using the existing 0234 result-envelope discovery. It reconciles each session and
model, with cumulative result maxima for resumed sessions and terminal messages
counted once. Same-session native children and explicitly parent-linked native
child sessions are included in the owner's accounting scope. Independent peer
sessions retain separate totals. Input buckets and reasoning counters are
compared, and reasoning is never added on top of output.

A nonterminal message, missing transcript/result, mismatched counters or API error
without a terminal record bound to that same request makes the accounting result
UNKNOWN. A subsequent successful request cannot silently close an earlier failed
one. An unbound stream retry remains UNKNOWN even if aggregate totals happen to
match. A failed but fully accounted peer turn followed by resume is supported;
its costs remain included. An explicitly request-bound retry is accepted only
when its terminal evidence and full totals reconcile.

Stream retry detection covers the owner's stdout and every Claude first/resumed
peer capture listed by the existing receipt inventory, including incomplete
captures. Each retry needs its own explicit terminal request binding; a prior
bound error in the same session cannot cover a later anonymous retry. Capture
hashes and per-event paths are retained. A pure Codex run with no Claude session
has no Claude closure obligation; existing identity/receipt checks separately
reject expected-but-missing sessions.

The runner keeps the unchanged 0234 recorder and calls this read-only guard
immediately afterward. It saves `claude-accounting.json`. A gap preserves the
recorder's original reported counters, keeps its former completeness label under
`reported_completeness`, marks usable counters PARTIAL with an explicit null
UNKNOWN residual, and takes the existing STOP path before product evaluation.
The verdict retains `known_usage_lower_bound`; its complete-cost fields stay
null. This is an apparatus/accounting stop, not PRODUCT_INCOMPLETE. The new guard
file participates in the runner's input seal. Native command routes, helper,
identity policy, Docker init/caps/watchdogs, delivery and evaluator stay unchanged.

## Prediction and local outcomes

Predictions were recorded before each test invocation:
`claude-accounting-v1-prediction.json`, `-prediction-2.json`, and `-prediction-3.json`.

- Initial guard tests: **9/9 pass**, 0.350s host duration.
- Initial runner tests: **25/26 pass**, one fixture failure. A synthetic test
  switched from Claude to Codex while retaining its newly complete Claude-owner
  transcript; peer policy correctly treated that leftover as unbound evidence.
- Follow-up removes only that obsolete fixture during the engine switch. It also
  corrects `terminal_message_count` to exclude incomplete messages, with an
  assertion in the missing-terminal test. The reversible follow-up patch is
  retained and reconstructs the exact initial predicted source hashes.
- Second guard tests: **9/9 pass**, 0.293s host duration.
- Second runner tests: **26/26 pass**, 7.146s host duration.
- Final guard tests after the peer-stream correction: **11/11 pass**, 0.315s
  host duration. Added first/resumed peer stream-only retries with coincidentally
  matching totals, prior bound-error non-substitution, and pure Codex applicability.
  `accounting-v5-initial/` preserves the earlier unmeasured draft bytes.
- Final runner tests: **26/26 pass**, 6.838s host duration. These include actual
  accounting-STOP classification, positive/no-op/deleted source classification,
  retained init/native-identity behavior, peer failures/recovery, scope, resumes,
  F23 supplement and existing evaluator boundaries.

Raw commands, stdout, stderr, exits and durations remain in
`claude-accounting-v1-tests-{1,2,3}.*` and
`claude-accounting-v1-runner-tests-{1,2,3}.*`. The initial failure is not erased.
No unchanged Docker/full evaluator suite was repeated.

The real controls use disposable copies when invoking the legacy writer, and
verify the original file hashes afterward. `claude-accounting-v1-replay-3.json`
retains the separate read-only derived guard reports and exact source hashes:

| Retained cell | New guard | Original reported input | Original reported output |
| --- | --- | ---: | ---: |
| 0239 s01 short | MATCH | 1,828,901 | 48,810 |
| 0239 s02 long | MATCH | 1,779,956 | 43,851 |
| 0239 d01 C | UNKNOWN | 25,986,453 | 411,981 |

These are offline guard controls, not reruns or historical regrading. The d01
recorded totals remain intact and no estimate is used to fill its missing stream
closure. Original files are unchanged; no credentials were copied or read.

## Explicit limits

This guard is deliberately conservative. A native API-error event without a
request identity cannot be cleared from a later successful result, even if totals
match. The positive explicitly bound-error/retry fixture is synthetic; it does
not claim the pinned CLI emits a request ID on d01's anonymous error or retry. An unexplained
native charge without a corresponding terminal message also stops measurement.
A separately evidenced counter format would require prospective review, not an
implicit compatibility fallback.

The scope is retained native accounting, not a provider invoice or invisible
server-side work. Codex continues using the existing per-inference trace recorder;
no Codex behavior changes. Product quality is not inferred from an accounting
failure. No model, Docker or authentication call occurred. v5 is a prospective
review freeze only and requires review plus registration before model dispatch.
