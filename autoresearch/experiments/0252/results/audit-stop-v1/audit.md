# 0252 independent accounting STOP audit

**PASS — faithful registered STOP closure. 61 checks; zero HIGH findings.** This is
an accounting, identity, custody, sequence, binding and lifecycle audit. It is not
an efficacy verdict or permission to continue this comparison. Seven native owner
attempts occurred, d01–d07 in the registered order. d08–d24 are NOT_RUN. The OR2
block is incomplete; no efficacy gate was applied and STOP is not an S failure.

The prospective prediction was stated in reviewer commentary before the first
filesystem inspection. `prediction.json` honestly records its later file-save
time provenance; it is not backdated. The independent script imports no frozen
runner and launches no model, owner, evaluator or test. It parses native metadata
and accounting only, hashes custody bytes, and performs State-only Docker and
volume-name inspections.

## Accounting finding

d07's native result reports the following aggregate. A separate reconstruction
from the last record of each `(sessionId, message.id)` in every owner/child JSONL
finds 35 unique messages, of which only 34 have terminal usage:

| Counter | Native aggregate | Terminal-message sum | Arithmetic difference |
| --- | ---: | ---: | ---: |
| Uncached input | 70 | 68 | 2 |
| Cache creation input | 312,517 | 311,279 | 1,238 |
| Cache read input | 4,369,766 | 4,278,841 | 90,925 |
| Total input | 4,682,353 | 4,590,188 | 92,165 |
| Output, including thinking | 252,455 | 246,903 | 5,552 |
| Thinking, already in output | 225,007 | 220,006 | 5,001 |

The missing terminal message is `msg_011CfunbQhY59sLNzUGB5DeQ`, request
`req_011CfunbQSukX6eR7yg1aY6j`, in the native child transcript
`home/.claude/projects/-cell-work/72508a4d-1db7-4ce7-a283-fe5ceb0c674b/subagents/agent-a404df2904b5a0457.jsonl`.
Its records at lines 53–55, ending at `2026-10-11T04:05:09.087Z`, all have
`stop_reason: null`, progress output 8, and no terminal thinking counter. No
native API-error or stream-retry record appears in the audited captures.

The arithmetic difference is not recovered usage and is not attributed to that
message as its final cost. No upstream cause is established. Both raw counter
sets are retained. d07 remains **PARTIAL**; whole input/output/cost remain
**UNKNOWN**. The raw verdict's field named `known_usage_lower_bound` contains the
native aggregate; this audit preserves that raw label without independently
certifying the aggregate as a whole-cost lower bound. Cached input and thinking
are counted once, with thinking already contained in output.

d01/d04/d06 native Codex per-response usage records sum exactly to their final
native cumulative counters (17/14/15 unique response records respectively).
d02/d03/d05 Claude terminal-message sums reconcile exactly to their native
aggregates. Their recorded resource counters are retained below. Outcome labels
are only the original runner descriptions; source, oracles and delivery are not
graded by this audit.

| Attempt | Original runner description, unadjudicated | Usage | Reported input | Reported output | Native owner seconds |
| --- | --- | --- | ---: | ---: | ---: |
| d01 Codex/S | CHECKS_PASS | COMPLETE | 639,167 | 23,386 | 669.6833574170014 |
| d02 Claude/B | PRODUCT_INCOMPLETE | COMPLETE | 3,168,958 | 191,043 | 1719.27477012499 |
| d03 Claude/S | CHECKS_PASS | COMPLETE | 4,600,164 | 118,425 | 1069.8808793750068 |
| d04 Codex/B | CHECKS_PASS | COMPLETE | 545,514 | 24,557 | 708.9588165830064 |
| d05 Claude/S | CHECKS_PASS | COMPLETE | 5,077,003 | 159,308 | 1715.7884819169994 |
| d06 Codex/B | CHECKS_PASS | COMPLETE | 488,997 | 18,422 | 543.0486605830083 |
| d07 Claude/B | STOP: whole-run usage PARTIAL | PARTIAL | 4,682,353 | 252,455 | 2210.522106166987 |

The seven native aggregate observations sum descriptively to 19,202,156 reported
input and 787,596 reported output tokens. The study's whole token cost remains
UNKNOWN; these are neither efficacy scores nor independently certified bounds.
Unmodified native owner wall sums to 8,637.157072167 seconds.

## Identity, custody and stopping

All 773 unique frozen bindings, the original operator binding, registration and
schedule match. All control trees match their manifest (28 oracle, 969 package,
64 public files); those bytes were hashed only. All seven prepared seals match.
All 5,875 file entries in the seven post-teardown evidence manifests match,
with no collection failures. The unchanged prior freeze and 0251 operational
smoke audit were reused after hash checks; no historical smoke or calibration
was rerun.

Observed native identities agree with Claude `claude-opus-5-5` and Codex
`gpt-6-astra`; actual invocation arguments retain `max`, the pinned image and
5,400-second owner watchdog. Native versions are Claude 2.1.296 and Codex 0.162.1.
The recorded account pair and preflight token lifetime meet the registered
minimum for each attempted slot. The fixed auth manifest and credential files
match their sealed hashes. Credential bytes were only streamed through SHA256;
no credential contents were parsed, displayed or renewed.

**d07 did launch a native Claude child.** The raw stream's `Agent` tool call at
line 1441 requests a background general-purpose agent with no model override.
Its sealed child transcript has `isSidechain: true`, agent ID
`a404df2904b5a0457`, and the same session ID as its owner; observed assistant
models are all `claude-opus-5-5`. d02 also has a native child transcript,
`aa95496ce0b2533ed`, included in its reconciled accounting. The frozen
`0234/evidence.py` inventory intentionally excludes owners and native children
from independent `owner_launched` sessions. Therefore
`identity.owner_launched_sessions: []` is compatible with this child activity
and must not be cited as proof that no child ran. Native child activity is
within the retained route; no observable identity gap is established here.

All seven recorded native intervals are serial. Each records clean teardown;
State-only inspection confirms every named container is absent and name-only
inspection confirms every attempt's tmp volume is absent. The original driver
PID 72149 is absent. d07 ended with exit 0 but its runner returned 2/STOP after
accounting, with no checks, delivery or checked snapshot artifact. No d08 launch
prediction, output directory or verdict exists; the rest of the schedule is
likewise NOT_RUN.

The parking and resume records preserve PID 72149 and its scheduler-only
SIGSTOP/SIGCONT. The 620.791736-second hold falls wholly inside d05's uninterrupted
native interval. No duration is subtracted: native owner time remains
1715.7884819169994 seconds, dispatch wall 1721.3958677079936 seconds. The original
imprecise prediction and later explicit clarification are both preserved.

## Exact evidence hashes

Full source-path/hash inventory and individual checks are in `audit.json`.

| Evidence | SHA256 |
| --- | --- |
| registration.md | `2e90d1d98a9ecb1f580786881a262c8b18cd97109d1e91cfb5f5411a1c1b1204` |
| schedule.json | `4bd81b5d2e2ccfa8a2d07566c4bd93103ca716472b64423e4e7fb45daee91d2b` |
| freeze-v1.json | `e157693dea13ec057f19acb205220241a2583590e13243b8168d2f068b6604d8` |
| bindings.json | `e8dfafde4c137db7f082c11243d42c871596a7f43ab35701735b6660c73c2dae` |
| d07 evidence.manifest.json | `6c0aa40e0e5b7f575827bffb01720e32111fc49916a9abc078d640a93f529193` |
| d07 verdict | `18fd88a053919d60ee2a53bf38add99bdb00a3679a31746255d1532680b8315f` |
| d07 run/stdout | `a3f7c3a60e0d13716252a2e867226c943e4b8e683994757a86ee4ef417d54539` |
| d07 owner JSONL | `ae0d7e0bb4e53e15aa6f855dfe60d949035b57d58b714749bd2cb6efc8d36907` |
| d07 native child JSONL | `16b62e46de3804071162f87c9e7cc7118da36f7ec077ce6ffcf924a11d2b8b50` |
| this audit.py | `b69b6e9311bd2501aeb78165c2798bbdbef152b65a736f68b4bea53483fcd58b` |
| this audit.json | `8b0b981c6ffad2c0e1216f938e60bd407cb8a635947367edf5f5c00276dba88d` |
| prediction.json | `d06d39c7433095c748bf3e065089f0b5a168a30361f8bf12ec315cdb85005c30` |

## Limits and disposition

This audit observes native accounting, not provider billing. Invocation metadata
cannot reveal hidden server-side identity, and recorded owner intervals cannot
reconstruct every unrelated historical host process. Live account identity was
not queried again; recorded preflight and frozen adapter enforcement are reused.
Raw captures remain private. No source/oracle/delivery grading or efficacy gate
was performed after STOP. The six earlier descriptions remain unadjudicated.

Under **No guesswork**, the discrepant whole cost remains UNKNOWN. Under
**No workaround** and **Production ready**, the registered accounting STOP closes
0252 immediately, without retry or repair. Under **No overengineering** and
**Optimized**, unchanged checks are reused and no successor study or pair
escalation is created. There are zero HIGH findings against this faithful
closure; publishing a no-child claim, a complete-cost claim, or an efficacy
verdict would fall outside this PASS.
