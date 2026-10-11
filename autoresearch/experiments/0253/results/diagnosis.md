# 0253 offline native lifecycle diagnosis

The exact internal loss cause remains **UNESTABLISHED**. The demonstrated failure
is an interior native child message whose terminal usage was not preserved in
the available message evidence. No parser correction or residual-cost recovery
is justified. 0252 remains CLOSED_ACCOUNTING_STOP with whole cost UNKNOWN.

Prediction was saved before investigation in
`astra-native-lifecycle-prediction-v1.json`. Only native accounting/lifecycle
metadata was inspected. No credential files, source/oracle grading, provider
calls, tests or historical modifications were used.

## What the trace establishes

The missing message `msg_011CfunbQhY59sLNzUGB5DeQ`, request
`req_011CfunbQSukX6eR7yg1aY6j`, has three snapshots in child JSONL lines 53–55
and stdout lines 1684–1686. All have null stop reason and progress output 8.
The last is timestamped 04:05:09.087Z. This is followed by a successful tool
result at 04:05:09.451Z and a *different* request with terminal usage at
04:05:48.474Z. Native child termination occurs later, at 04:06:17.314Z.

Both compared children have native metadata `requestShape: background`,
`requestNonInteractive: true`, and spawn depth 1. For both, native stderr
explicitly reports stopping background tasks still running ten minutes after
the owner's last turn. The owner-end-turn to native-kill interval is 600.224s
for d02 and 600.216s for d07. Each stream then records child status `killed`,
a stopped notification, and a success result. Each child ends with the native
interruption marker; that marker is not evidence of a human interruption.
The outer runner's normal exit follows this native sequence.

d02 is an accounting-healthy comparator, not a successfully completed child
lifecycle: it also gets killed at the ten-minute native ceiling. Its emitted
terminal-message counters nevertheless reconcile. Therefore the shared native
kill behavior does not establish the cause of d07's earlier interior gap.

All four owner/child JSONLs and both stdout captures are structurally complete,
newline-terminated and match their sealed hashes. Later messages, tool results,
kill notifications and success results survive. This disfavors ordinary final
collector truncation. The task `.output` paths are symlinks to the same child
JSONLs, not independent copies with missing terminal data.

## Important format distinction

Every assistant block in stdout has `stop_reason: null`: 98/98 in d02 and
101/101 in d07. Healthy transcript messages subsequently contain terminal
updates that stdout does not. For example, d07's final owner message is
null/output 8 in stdout 1651–1652 but end_turn/output 258 in transcript 191–192.
Its next child request is null/output 3 in stdout 1689–1691 but
tool_use/output 4,919 in child transcript 60.

Thus the missing message's identical nonterminal copies do **not** disprove
transcript serialization/update timing loss. The available data distinguishes
neither that mechanism from other native reporting loss nor whether the provider
terminal was received internally. No missed terminal event with an incompatible
schema was found. Native progress figures and aggregate arithmetic cannot fill
the gap.

The exploratory `astra-native-lifecycle-report-v1.json` is preserved. It records
the full comparison as unequal, but its prose incorrectly generalized equality
and overly disfavored transcript-writer timing loss. v2 corrects that interpretation;
neither the prediction nor any old evidence is rewritten.

## Smallest admissible next step

Keep the accounting guard unchanged. A single preregistered operational probe of
official native per-attempt request/terminal-response file capture targets the
missing evidence boundary. It must demonstrate owner and native child coverage
in the actual pinned venue, with remote exporters disabled, before a parser or
prospective reconciliation policy is written. The probe is not a d07 reproduction,
an efficacy draw, a spontaneous child-lifecycle test or instruction admission.

Foreground wording or a background-ceiling override would change execution
behavior without explaining this interior gap. They are separate hypotheses,
not established remedies. If official capture cannot expose request-bound
terminal counters, retain UNKNOWN and close the operational step; do not build a
speculative collector or weaken acceptance.

Detailed source hashes, line metadata and timings are in
`astra-native-lifecycle-report-v2.json`. Key d07 source hashes remain:

- stdout: `a3f7c3a60e0d13716252a2e867226c943e4b8e683994757a86ee4ef417d54539`
- child JSONL: `16b62e46de3804071162f87c9e7cc7118da36f7ec077ce6ffcf924a11d2b8b50`
- stderr: `c0f99eded2e1e57512abc989a650735097c87a07dbe05883d23e93b0e1ec814b`
