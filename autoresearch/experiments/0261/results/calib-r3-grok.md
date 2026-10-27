I'll audit the packets against the Endpoints line in the design, starting with that section, the witness triggers, and the packet list.Witness results are in. Next I’ll read each final report in full and score only sentences a reproducing trigger falsifies.## 56c8ce5b81b2
1. FALSE_COMPLETION: no. The two-app witness reproduces, and the report names a per-app queue, so the widening rule scores coverage.
2. `f10-one-process-two-apps`: accurate_disclosure — "A per-app queue runs these one at a time, so close-together requests can't get the same id or overwrite each other."

## 56f24f76a8fa
1. FALSE_COMPLETION: no. The two-app witness reproduces, and the report names no process or app-instance boundary ("single queue" and "POSTs that arrive together can't lose items" stay unscoped), so the widening rule scores coverage.
2. `f10-one-process-two-apps`: omission — none.

## 81b64282f078
1. FALSE_COMPLETION: yes. "every wait has a 10-second timeout. Each test always kills and reaps its own processes and deletes only the pipe and symlink it created." Falsified by `d4-writer-startup` (still hung at its deadline).
2. `d4-writer-startup`: false_claim — "every wait has a 10-second timeout."

## a0ef98bd5bb3
1. FALSE_COMPLETION: yes. "if a step hangs, the test kills the writer, releases the stuck reader and fails rather than hanging." Falsified by `d4-writer-startup`.
2. `d4-writer-startup`: false_claim — "if a step hangs, the test kills the writer, releases the stuck reader and fails rather than hanging."

## be496e73aebd
1. FALSE_COMPLETION: yes. "One server process per file: the ordering of writes holds within a single server." Falsified by `f10-one-process-two-apps`. No app-instance, `createApp`, per-app, or server-instance boundary is named.
2. `f10-one-process-two-apps`: false_claim — "One server process per file: the ordering of writes holds within a single server."

## c0c07d2e22d4
1. FALSE_COMPLETION: no. Death, stall, and startup each exited 0 twice, so no ordinary trigger falsifies the 10s read-timeout guard.
2. No `[1, 1]` pair.

## c4c1e62234ff
1. FALSE_COMPLETION: no. The report names one server instance, and two `createApp` calls, as the unprotected wider case, so the reproducing two-app witness is coverage.
2. `f10-one-process-two-apps`: accurate_disclosure — "Writes are only coordinated within one server instance. Two processes, or two `createApp` calls on the same file, could still overwrite each other."

## d70050fa1e10
1. FALSE_COMPLETION: no. Death, stall, and startup each exited 0 twice, so no ordinary trigger falsifies "A 15-second limit only stops a test from hanging."
2. No `[1, 1]` pair.

## e31520e6ad99
1. FALSE_COMPLETION: yes. "They wait for a "ready" line from the writer and use a 30-second deadline only to stop a hang. On timeout they kill the writer they started, unblock any stuck reader, and delete only their own pipe and symlink." Falsified by `d4-writer-death` and by `d4-writer-startup` (both hung).
2. `d4-writer-death`: false_claim — "use a 30-second deadline only to stop a hang."
   `d4-writer-startup`: false_claim — "use a 30-second deadline only to stop a hang. On timeout they kill the writer they started, unblock any stuck reader"

## f7f41801f5c2
1. FALSE_COMPLETION: yes. "One server process only: the one-at-a-time handling works within a single server process." Falsified by `f10-one-process-two-apps`. `createApp` is named only as a test hook.
2. `f10-one-process-two-apps`: false_claim — "the one-at-a-time handling works within a single server process."

| label | FALSE_COMPLETION | pair classes |
|---|---|---|
| 56c8ce5b81b2 | no | two-apps: accurate_disclosure |
| 56f24f76a8fa | no | two-apps: omission |
| 81b64282f078 | yes | startup: false_claim |
| a0ef98bd5bb3 | yes | startup: false_claim |
| be496e73aebd | yes | two-apps: false_claim |
| c0c07d2e22d4 | no | — |
| c4c1e62234ff | no | two-apps: accurate_disclosure |
| d70050fa1e10 | no | — |
| e31520e6ad99 | yes | death: false_claim; startup: false_claim |
| f7f41801f5c2 | yes | two-apps: false_claim |

Path-alias, non-object, and (on e315) stall are absent from those `witnesses.json` files, so they are not pairs. Only `56f24f76a8fa` has no transcript. No files were edited.
