# d01 native lifecycle and independent usage audit

Completed-cell, read-only audit, 2026-10-10. **The background child completed and
its findings were consumed before delivery. C's prescribed foreground/native-wait
mechanism was not demonstrated. Whole retry cost cannot be independently
reconstructed: preserve the raw native total and an UNKNOWN interrupted-stream
residual.** No d02 comparison, model/Docker call, rerun or raw/frozen edit occurred.

Cell root `R` is
`/Users/aipalm/.local/share/nx01/0239-live/staged-v1/out-development/d01-claude-c`.
`O` is `R/run/stdout`. Native parent `P` is
`R/home/.claude/projects/-cell-work/2b0944a9-5361-4eef-9b3d-aaa21a34ae20.jsonl`;
native child `K` is its sibling directory
`2b0944a9-5361-4eef-9b3d-aaa21a34ae20/subagents/agent-a1abcac1b0c0dcbae.jsonl`.
The [machine-readable audit](d01-native-audit.json) records exact paths, SHA256s,
line numbers, per-message counters, differences and UNKNOWN values.

Raw result remains **CHECKS_PASS**, source and delivery pass, identity MATCH,
EXITED_0, CLEAN; owner **3477.738696790999 seconds**, native reported input
**25,986,453**, output **411,981**, raw completeness **COMPLETE**. Delivery binds
commit `635ae29d07aadec822122a7a852b0f2a78f4dc93` to its checked source. No costs
are subtracted or substituted. Root separately audits all source/seal/commit
integrity; this audit binds only the files it cites.

## Actual lifecycle

All timestamps below come from native event fields, not filesystem mtimes.

| Boundary | Native evidence | UTC time |
| --- | --- | --- |
| Guide read requested / returned | O:12 / O:13 | 11:14:37.864 / 11:14:37.902 |
| Agent call, background flag omitted | O:1952 | 11:49:53.463 |
| Actual background start | O:1954 `is_backgrounded:true` | Event itself has no timestamp |
| Child final answer, `end_turn` | K:89 | 12:04:14.918 |
| Native child marked completed | O:2823 `end_time=1791633855023` | 12:04:15.023 |
| Terminal result delivered | O:2824 **system/task_notification**, completed | Event itself has no timestamp |
| Manager repair / loader call-shape repair | O:2980 / O:2982 | 12:06:56.677 / 12:06:58.650 |
| Review-driven test update | O:2998 | 12:07:29.533 |
| Local commit call / successful result | O:3232 / O:3233 | 12:11:00.672 / 12:11:00.743 |
| Parent final response | O:3314 | 12:12:26.092 |

O:13 returned the candidate sentence requiring children before final response
using explicit foreground or a supported native wait. This is verified exposure
before launch, not proof that the sentence caused the eventual outcome.
O:1952's actual Agent inputs contain neither `run_in_background` nor a model/effort
override. O:1954 and the final native stats independently establish background
execution. Every retained parent/child inference identifies Opus5.5 and max effort.

The owner continued its own work (public text O:1962), informed the reviewer of
concurrent merge/loader changes (O:2518), and asked it to finish the current
experiment and report (O:2764). Four `ListAgents {}` calls at O:2689,2728,2800,2820
returned status immediately; **they are not an explicit foreground or blocking
native wait**. A report was subsequently delivered through O:2824, not through an
invented assistant notification. The child had run 861.550 seconds according to
native notification statistics (launch argument timestamp to end timestamp:
861.560 seconds). The parent remained active and committed 405.720 seconds after
that recorded completion, then finalized 491.069 seconds after it.

O:3315 records one requested-unset child, one started in background, one completed,
zero failed and zero parent/user/system kills. Stderr is empty. There is no
post-final print-ceiling kill in this cell. This shows successful lifetime ordering
in one background execution; it does not validate spontaneous foreground selection,
a supported wait invocation, a C/B difference or an efficiency benefit.

## Independently reconciled usage and its limit

Deduplicate native transcript snapshots by `message.id` within each carrier and
retain its final terminal version. Every distinct message has final integer
uncached/cache-read/cache-creation/output counters and a terminal stop reason.
Per-ID maximum counters equal the final-version sums. Parent snapshots are all
terminal; the child's 24 provisional snapshots resolve to terminal versions of
the same 18 IDs. No API-error/synthetic assistant message, conflicting request ID
or stdout-only assistant ID supplies the remaining cost. Do not count provisional
copies again.

| Carrier | Terminal IDs | Uncached input | Cache read | Cache creation | Output | Thinking, already within output |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Parent P | 78 | 160 | 23,862,961 | 361,360 | 325,873 | 262,197 |
| Child K | 18 | 40 | 1,479,011 | 141,834 | 86,103 | 64,333 |
| Independent terminal sum | 96 | 200 | 25,341,972 | 503,194 | 411,976 | 326,530 |
| Final native modelUsage, O:3315 | — | 202 | 25,410,377 | 575,874 | 411,981 | 326,530 |
| Aggregate minus terminal sum | — | 2 | 68,405 | 72,680 | 5 | 0 |

Processed input sums uncached, cache read and cache creation once: independent
terminal total **25,845,366**, native aggregate **25,986,453**, difference
**141,087**. Reasoning is already included in output, never added a second time.
Native `usage` at O:3315 is the parent aggregate; subtracting it from `modelUsage`
exactly reproduces K in every bucket, including thinking. **Child usage is fully
reconciled; the difference belongs to the parent accounting boundary.** The
notification's `total_tokens=145780` is not used as cumulative child accounting.

P:72 records `ECONNRESET` at **11:33:17.536Z**, retry attempt1. Before O:979's
native `api_retry`, O:945–978 emitted 34 parent thinking-progress estimates,
50 rising to 4150; estimates restart after the retry. This attempt has no retained
assistant message ID or terminal per-request usage. The successful retried parent
message later has its own complete terminal counters. Last-version versus maximum
counter handling cannot recover the interrupted attempt.

The aggregate-only excess is consistent with retained provisional accounting for
that attempt, but no separate carrier proves that attribution or its final output.
**4150 is a native progress estimate, not an exact final/billable count.** It cannot
be added, subtracted, or declared the number of missing tokens. The known
aggregate-minus-transcript difference and unknown additional interrupted-stream
usage are different quantities. UNKNOWN residual values remain null, not zero.

The frozen parser uses final `modelUsage`; therefore its raw COMPLETE accurately
describes the parser's accepted native aggregate and it drops none of those
reported counters. P:486's cost-state agrees with that aggregate, but its
`hasUnknownModelCost:false` concerns native pricing and does not supply a missing
stream-final usage record. **Independent whole-attempt completeness is not
established.** There is a concrete accounting reconstruction limitation, not proof
of a particular missing-token amount. Retain the larger native total in full.
Native list-price cost is $17.9294954 (`costBasis:list`), not a provider invoice or
observed subscription charge.

## Findings that actually reached repairs

The child reported nothing above LOW (K:89 / O:2824). Retained experiments and
subsequent edits support a narrower conclusion than treating all suggestions as
required defects:

- **Useful valid-input counterexample:** K:80 showed accepted near-parser-limit
  JSON followed by a repaired shallow file still causing `RecursionError` from
  JSON-serialization equality under a deeper caller stack. P:127 had installed
  that equality; O:2980 replaced it with structural stack comparison. P:407's
  retained rerun shows callback depths2,3,5 now return generations `[1,2,2,2]`.
  Format.md:5–8 and reload.md:10–14 ground error/recovery obligations, although
  this is the reviewer's explicitly contrived LOW case, not a typical deployment.
- **Call-shape compatibility:** K:83's one-argument canonical stand-in failed;
  O:2982 preserves the root call's original arity, and P:407 shows it working.
  An imported internal helper is not in exported `__all__`, so strict patched
  stand-in compatibility is not independently guaranteed by “preserve exported
  APIs.” The variadic merge stand-in issue was retained and disclosed.
- **Injected loader cases:** K:77 demonstrated non-JSON serialization errors and
  list-dependency aliasing; O:2980/O:2998 repaired/covered them, with P:407's rerun
  showing improvement. Non-JSON values and list dependencies lie outside the
  documented JSON/Resolved tuple contract. These are observed robustness changes,
  not automatically required correctness gains.
- **Grounded coverage:** O:2998 combines nested object values and relative includes
  in the new diamond test after the reviewer identified that gap. It strengthens
  coverage without proving another implementation bug was found.

Pre-existing NaN/Infinity acceptance, type-sensitive generation interpretations,
variadic helper calls and extreme-depth design tradeoffs remained disclosed.
No present audit reran these experiments. Useful review-to-repair evidence is
retained independently of whether C caused safer lifetime management.

## Registration consequence and recommendation

[Registration](../registration.md:33) permits d02 after d01 finalizes and is
accounted for. Lines85–89 require complete retry/failure input and reasoning,
mark missing usage UNKNOWN and forbid cost subtraction. Lines68–69 disallow
benefit resting on an unexplained accounting difference; lines112–113 close an
affected apparatus attempt and require a new identity/rule for a new version.
The ordinary-pair outcome clauses themselves are written for after the pair;
the present hold rests on its earlier accounting prerequisite and apparatus rule.

**Recommendation: close this affected C comparison without adoption and leave d02
not dispatched.** Preserve source/delivery success, useful review, safe background
ordering, all native reported cost, and UNKNOWN failed-stream residual. Do not
rerun C to obtain clean costs. Executing B as lifecycle-only would require a new
prospective scope/rule, and is not the smallest necessary continuation for a
candidate whose explicit launch/wait mechanism was not exercised here.

Before prospective0238, raw COMPLETE alone must not pass the accounting gate when
native progress is followed by retry/abort without terminal usage closing that
attempt. Preserve reported aggregates, mark the unresolved residual UNKNOWN and
stop resource comparison. A retry with fully reconstructible final accounting is
not automatically invalid. This is a recommendation for new versioned apparatus;
no frozen accounting source or old verdict is changed here.
