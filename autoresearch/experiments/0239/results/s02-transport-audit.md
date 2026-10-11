# Long native foreground transport: PASS

2026-10-10. The registered long smoke succeeded without changing the native
post-final ceiling or Bash environment. This proves transport only; the explicit
caller instruction cannot establish spontaneous compliance or an instruction
efficiency gain. The forced 610-second workload remains fully charged.

| Event | UTC time | stdout line |
| --- | --- | --- |
| Agent explicitly foreground | 10:58:23.362 | 147 |
| First exact Bash call, timeout360000, false | 10:58:26.193 | 151 |
| First successful terminal result | 11:03:31.283 | 164 |
| Second exact Bash call, timeout360000, false | 11:03:34.265 | 166 |
| Second successful terminal result | 11:08:39.344 | 179 |
| Parent receives completed child result | 11:08:42.052 | 182 |
| Parent writes the returned receipt | 11:09:24.153 | 243 |
| Parent commits the receipt | 11:11:18.278 | 347 |
| Parent final response | 11:12:54.647 | 410 |

The child ran each unchanged command once and in order. Native gate durations
are 305.0030178040033s and 305.0004345569978s; the native child duration is
618678ms. Explicit Agent and Bash launch fields plus task_started metadata
identify foreground execution. The child returned a terminal answer and its
payload equals the saved/evaluated/committed receipt. Final native statistics
show one requested foreground child, one completion, no background start and
no kill. Native stderr is empty.

Every native assistant message in parent and child identifies Opus5.5/max.
Independent terminal-message usage summation matches the recorded totals:
1779956 processed input, 43851 output, including caches/child usage; whole
owner wall is 1043.267465s. No waiting or inspection time is subtracted. Other
user sessions on the shared host were not controlled; this study launched no
independent model/reviewer call during the owner. The local portability jobs
ended early in this unmeasured transport run, before the ordinary comparison.

Only receipt.json changed. Commit b91ea0cea93f6f1ae8d4b2a6fb3ac049f41c7314
matches the evaluated snapshot. Raw CHECKS_PASS, identity MATCH, usage COMPLETE,
clean teardown, all705evidence hashes and unchanged input/prepared/control seals
are verified. Startup catalogs equal s01 and the prospectively frozen B/C
expectations. s02-transport-audit.json retains the derivation and raw verdict;
audit_transport.py is post-run analysis of the already registered criteria,
not a changed source oracle or historical regrade.

Both transport gates now pass. development-dispatch-gate.json records root's
decision to start only the fixed ordinary C/B diagnostic under
freeze-development-v1.json. Neither smoke adopts the candidate.
