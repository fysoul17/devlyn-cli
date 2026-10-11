# 0253 — Native request and terminal-response capture

0252 stopped because one native child message lacked terminal usage, although
later child requests completed. Its exact internal cause remains unestablished.
The later ten-minute background shutdown does not explain that earlier gap.
Stdout contains block-time snapshots even for healthy messages, so matching
nonterminal copies do not rule out transcript update loss. Preserve 0252's
UNKNOWN whole cost; see [diagnosis](results/diagnosis.md).

This research-only adapter adds Claude Code's documented local API body capture
to the unchanged 0251 launcher. `OTEL_LOG_RAW_API_BODIES=file:<directory>` writes
request attempts, terminal responses and an identity index; remote metrics,
logs and traces exporters are set to `none`. The pinned CLI is 2.1.296. See the
official [monitoring reference](https://code.claude.com/docs/en/monitoring-usage).
Raw bodies remain private because they contain task and code context. Only
reviewed metadata is published.

[Registration](registration.json) predates one operational owner with one tiny,
prompt-directed foreground child. It freezes B instructions, image, model and
effort, fixed authentication, the 5,400-second watchdog, native tool access and
all existing identity/accounting/catalog/quota/peer-policy checks. Authentication
must retain at least 6,300 seconds of lifetime at preparation and launch. No
retry or replacement is allowed. Source/oracle/delivery grading is absent.

`runner.py` adds only capture configuration and its input binding. `probe.py`
uses the registered prompt and writes an exclusive dispatch record before
preflight. An interrupted invocation cannot be dispatched again into that root.
`CAPTURE_OBSERVED` means that existing guards passed and an index exists; it is
deliberately pending independent request/response and child-identity inspection.
Run it only from a retained source copy with a frozen runtime and bindings:

```sh
python3 -B probe.py <runtime.json> <bindings.json>
```

The [verification record](results/verification.json) and
[native audit](results/audit-native-v1/audit.md) describe the single observation.
It establishes capture coverage for that owner and child, not every possible
native failure path. It neither reproduces d07 nor tests spontaneous foreground
behavior, instruction efficacy or provider billing. Thinking is included in
output once; cache reads and writes are included in input.

No new reconciler or source-precedence rule is admitted here. A prospective
accounting change would need to bind every request attempt and reject missing,
cancelled, malformed or conflicting terminal evidence, with meaningful negative
tests. Old results must never be backfilled. This applies **No guesswork**,
**No workaround** and **No overengineering**; product instructions, versions and
closed efficacy studies are unchanged.
