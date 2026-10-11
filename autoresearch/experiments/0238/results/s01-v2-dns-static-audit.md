# s01-h-claude-v2 DNS static audit

Read-only diagnosis, 2026-10-10. No credentials read, authentication, inference, container start, source edit, or frozen-input mutation. Inspected retained owner/peer transcripts and receipts, recorded create arguments, accounting outcome, registration-smoke.md and registration-proposal.md. Docker/host metadata inspection only; the separate connectivity probe below was performed by root, not this reviewer.

## Observed failure

Owner session e5525c6b-d917-43a1-bdac-a7678ed64a2f has 51 genuine assistant records (not necessarily 51 independent requests), last timestamp 13:03:53.039Z. It launches the fresh same-engine peer then. Peer session 8690f61b-5691-424d-83f0-4f938f64e1d4 has no genuine assistant response. Peer transcript lines 15–24 record ten retries from 13:04:23.671Z through 13:08:13.877Z, each `getaddrinfo EAI_AGAIN api.anthropic.com`, with isSSLError=false. Its synthetic final error arrives 13:08:59.495Z; completion.json records exit1 after306.860s, below the540s watchdog. Owner transcript lines152–161 then records the same ten DNS retries from13:09:20.146Z through13:13:08.985Z, followed by synthetic error13:13:55.949Z. No HTTP authentication rejection is established by these errors.

Recorded owner creation uses the pinned image, default bridge, --init, PID256, memory4g, CPU2; no DNS override or proxy variable is in the recorded added env. This does not prove image-level env absence. Native model identity matches, owner exits nonzero after1327.940s, teardown CLEAN. The measured container is no longer present. No contemporaneous pids.current/pids.events, memory.events, resolver contents or network trace was found in these run records. Peer stderr contains ordinary30-second monitor heartbeats, not OOM or fork-failure evidence.

## Supported diagnosis and limits

Leading explanation is a transient shared resolver/network-path failure affecting api.anthropic.com, somewhere between container resolver, Docker Desktop forwarding, host connectivity and upstream DNS. Both processes fail on exactly the same hostname; owner had worked before the peer launch and still fails after the peer exits. This weighs against a peer-only authentication defect. It does not locate the faulty hop or prove peer launch caused DNS loss.

Resource pressure remains an alternative, not a finding. Historical0237/results/f04-process-lifetime-audit.md establishes a different run reaching PID252/256 under unreaped orphans. This run already has --init; that historical cause cannot simply be imported. --init also does not rule out all live-thread/PID pressure. Current Docker metadata reports Desktop,11CPUs,16,748,867,584bytes VM memory and numerous unrelated service containers; these are present-state observations, not historical load. Host resolver metadata currently lists61.41.153.2 and1.214.68.2. No prior DNS incident was found in the bounded0238/0239-results Markdown search.

Root's retained results/s01-v2-connectivity-result.json subsequently reports a same-image/bridge/resource-envelope, credential-free probe at14:07:07Z: container resolver192.168.65.7; api.anthropic.com DNS PASS~20ms and HTTPS404; platform.claude.com and claude.ai DNS PASS~15ms with HTTPS403. These HTTP responses prove later DNS/TLS/HTTP reachability, not authenticated inference or reachability during the incident. This weakens a persistent bridge misconfiguration hypothesis but leaves transient forwarding/upstream failure and run-local pressure unresolved.

## Smallest discriminating checks

1. On recurrence, collect synchronized host and same-bridge container getaddrinfo results for api.anthropic.com plus one unrelated hostname, and preserve resolver contents. Prediction: host passes/container fails supports Docker-path trouble; both fail supports host/upstream trouble; only one hostname fails supports a destination-specific DNS problem. A later pass cannot retrospectively identify the cause.
2. Collect pids.current/max/events and memory.current/events plus thread counts during the failing interval. Prediction: limit-event increases or exhausted task counts support resource exhaustion; low counts and no events weigh against it. Do not change resource limits without such evidence.
3. After DNS resolves, one credential-free HTTPS request with a short timeout suffices to separate TLS/route failure from name resolution;404/403 is acceptable transport evidence. Root has already performed this successfully for the current state, so no duplicate probe is needed now.

Keep the finalized STOP and UNKNOWN accounting as registered. DNS attribution does not justify replacing missing terminal usage with zero. Registration requires a named diagnosis and separate prospective identity/freeze before any justified fresh attempt; no successful transport/peer-resume claim follows from this run.

## Evidence hashes

- `run/started.json`: `ae0033daafb5f079a8ea7fd8c5428333d7c6ffc85f5014e456e53b7f80778c94`
- `run/result.json`: `31cc5e7e2edd4085bf0ca4af928fcf5b7ef5e9b226fb8664c9d6914dd8215645`
- `home/.claude/projects/-cell-work/e5525c6b-d917-43a1-bdac-a7678ed64a2f.jsonl`: `d325881c758d0e29f57229a6748951da33b7a32f5bd0f1c2798ce95a1b4d5207`
- `home/.claude/projects/-cell-work/8690f61b-5691-424d-83f0-4f938f64e1d4.jsonl`: `d5beecb4a2e2bfd9def05960b0f85867153c1d85da0c64354095762d332adfcd`
- Root connectivity result: `b0bc188be3d18039d876e8f83be0930488ffc60dc0aa1f68d9c089d2bdfdef69`

## Prospective retry judgment

A fresh s01-v3 operational transport attempt is justified after root's observed connectivity recovery, with identical runtime/protocol and a separate prospective identity/freeze. The exact failed DNS hop remains unknown; that uncertainty does not negate the explicit native name-resolution errors. Preserve v2 as STOP with UNKNOWN residual accounting and all reported cost lower bounds; record the recovery evidence and reason before dispatch, retaining the same stop-on-failure gate. This authorizes neither treating v2 as a pass nor repeatedly rerunning until favorable. No authentication, resolver, or resource-setting change is justified by these observations. Root additionally reports host DNS passing; that check was not independently executed here. Root's reported later23:01KST sleep event cannot explain the13:04UTC (22:04KST) onset.
