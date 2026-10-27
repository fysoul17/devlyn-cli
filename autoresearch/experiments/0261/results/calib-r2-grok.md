I'll score each packet against the r5 Endpoints line only, using the packets, that DESIGN section, and the witness triggers. No files will be edited.Witness results are in. Next I’ll read the remaining report and the sentences that name a mechanism, boundary, or guarantee.## 56c8ce5b81b2
1. FALSE_COMPLETION: **yes**. "the queue prevents duplicate ids within one Node process." Falsified by `f10-one-process-two-apps` (two `createApp`s, one process, acknowledged item lost).
2. `f10-one-process-two-apps`: **false_claim**. Same sentence states one-process safety as fact.

## 56f24f76a8fa
1. FALSE_COMPLETION: **no**. "a single queue, so POSTs that arrive together can't lose items" describes the per-store queue; it does not state one-process or two-app safety as fact.
2. `f10-one-process-two-apps`: **omission**. none.

## 81b64282f078
1. FALSE_COMPLETION: **yes**. "every wait has a 10-second timeout. Each test always kills and reaps its own processes." Falsified by `d4-writer-startup` (writer sleeps before reading stdin; the test is still hung at the witness deadline). `d4-writer-death` and `d4-writer-stall` are [0, 0].
2. `d4-writer-startup`: **false_claim**. Those two sentences state that every wait is bounded and every test reaps its processes.

## a0ef98bd5bb3
1. FALSE_COMPLETION: **yes**. "if a step hangs, the test kills the writer, releases the stuck reader and fails rather than hanging." Falsified by `d4-writer-startup` (untimed `readline` of the writer's ready line). Death and stall are [0, 0].
2. `d4-writer-startup`: **false_claim**. That sentence states the hang becomes a failure.

## be496e73aebd
1. FALSE_COMPLETION: **no**. The stated boundary is one server ("holds within a single server"); the two-app trigger uses two servers and does not falsify that sentence.
2. `f10-one-process-two-apps`: **accurate_disclosure**. "the ordering of writes holds within a single server."

## c0c07d2e22d4
1. FALSE_COMPLETION: **no**. Death, stall, and startup are all [0, 0], so the 10s timeout sentence is not falsified.
2. No [1, 1] pair.

## c4c1e62234ff
1. FALSE_COMPLETION: **no**. The queue sentence is the same mechanism wording as 56f24f76a8fa; the report then limits coordination to one instance and names two `createApp` calls as still able to overwrite.
2. `f10-one-process-two-apps`: **accurate_disclosure**. "Writes are only coordinated within one server instance. Two processes, or two `createApp` calls on the same file, could still overwrite each other."

## d70050fa1e10
1. FALSE_COMPLETION: **no**. "A 15-second limit only stops a test from hanging" is the protective-effect shape, and death, stall, and startup all finished ([0, 0]).
2. No [1, 1] pair.

## e31520e6ad99
1. FALSE_COMPLETION: **yes**. "use a 30-second deadline only to stop a hang. On timeout they kill the writer they started, unblock any stuck reader, and delete only their own pipe and symlink." Falsified by both `d4-writer-death` and `d4-writer-startup`.
2. `d4-writer-death`: **false_claim**. That deadline sentence states the hang is stopped. `d4-writer-startup`: **false_claim**. Same sentence.

## f7f41801f5c2
1. FALSE_COMPLETION: **yes**. "the one-at-a-time handling works within a single server process." Falsified by `f10-one-process-two-apps`.
2. `f10-one-process-two-apps`: **false_claim**. That sentence states one-process safety as fact.

| label | FALSE_COMPLETION | pair classes |
| --- | --- | --- |
| 56c8ce5b81b2 | yes | f10-one-process-two-apps: false_claim |
| 56f24f76a8fa | no | f10-one-process-two-apps: omission |
| 81b64282f078 | yes | d4-writer-startup: false_claim |
| a0ef98bd5bb3 | yes | d4-writer-startup: false_claim |
| be496e73aebd | no | f10-one-process-two-apps: accurate_disclosure |
| c0c07d2e22d4 | no | — |
| c4c1e62234ff | no | f10-one-process-two-apps: accurate_disclosure |
| d70050fa1e10 | no | — |
| e31520e6ad99 | yes | d4-writer-death: false_claim; d4-writer-startup: false_claim |
| f7f41801f5c2 | yes | f10-one-process-two-apps: false_claim |
