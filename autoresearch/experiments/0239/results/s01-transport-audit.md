# Short native foreground transport: PASS

2026-10-10. Registered s01-claude-b-short completed on the unchanged B package.
Raw CHECKS_PASS, identity MATCH, usage COMPLETE and teardown CLEAN remain in
the private staged-v1/out-smoke cell. This is forced transport validation,
not spontaneous compliance, useful review, efficiency or candidate adoption.

The native trace, independently checked against the child's retained transcript,
establishes the required order:

| Event | UTC time | stdout line |
| --- | --- | --- |
| Agent explicitly run_in_background:false | 10:51:32.185 | 285 |
| Child's sole Bash call, timeout360000 and false | 10:51:34.462 | 289 |
| Successful terminal gate payload | 10:51:35.528 | 290 |
| Parent receives completed child result | 10:51:36.735 | 293 |
| Parent writes that exact receipt | 10:51:42.484 | 299 |
| Parent commits receipt | 10:52:07.841 | 324 |
| Parent final answer | 10:54:22.183 | 429 |

The native task_started event and child metadata independently identify a
foreground request. The child ran the unchanged exact command once, its gate
elapsed1.0014722920022905s, and its overall reported duration was4541ms. The
child's terminal JSON equals the owner-written/evaluated/committed payload.
Every native assistant message in both streams identifies claude-opus-5-5 and
effort max. Final statistics: spawned1, requestedforeground1, completed1,
background0, killed0; native stderr is empty. No unavailable wait was invented.

Only receipt.json changed. Local commit
faa0a0d7ecc056140b24290371f489be70ddb180 matches the selected snapshot, and the
unchanged public checker passes. Input/prepared/harness/control seals and every
retained evidence-manifest hash match. Actual startup catalogs equal the prior
registered B catalog, including only the expected built-in plugins and no MCP.

Whole owner wall480.062526s, processed input1828901 and output48810 are charged.
Deduplicating each native transcript by message ID and using its terminal
message counters independently reproduces those exact input/output totals;
caches and child usage are included. Native list-price estimates are not billed
money. Existing local portability checks overlapped this deliberately unmeasured
transport run; they completed before any ordinary efficacy call. No independent
reviewer/model call was launched by this study during it. Other user-owned
sessions on the shared host were not stopped or controlled. The1s stimulus does not make480s an efficiency
comparison, and no helper-reading cost is subtracted.

The registered gate for s02 is satisfied. Long foreground lifetime beyond600s
remains untested until s02 finalizes and its own native sequence is audited.
Machine-readable timestamps, hashes, identity and reconciled counters are in
s01-transport-audit.json. The original raw verdict is unchanged.
