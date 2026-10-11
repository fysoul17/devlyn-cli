# Integration verification

PASS on upstream `85004d8b3424488cb65bd593ea2d7354998ddb87` (4.2.4). All twelve bound input files stayed byte-identical throughout verification; canonical and installed helper/doc mirrors agree. No source edits or model calls.

| Check | Result | Wall seconds |
| --- | --- | ---: |
| Locked npm ci, Node20.19.0/npm10.8.2 | PASS; package metadata unchanged | 0.344 |
| Six targeted cleanup regressions on macOS | 4 passed, 2 Linux-only skips | 1.855 |
| Actual packed installer PackageTests | 71/71 passed | 31.681 |
| Installer menu | 15/15 passed | 3.804 |
| Full Linux task-complete helper | 72/72 passed, zero skips | 36.107 |
| Required structural lint | PASS, including macOS helper 70 passed + 2 Linux-only skips | 210.371 |
| Expanded ideate loop integration | 68/68 passed | 452.816 |

Both staged and working-tree diff whitespace checks returned 0. Linux used the pinned image with `--init --pids-limit 256 --network none --user 0:0`, readonly source and no credentials. Its container was removed after completion. No test process remains. The loop suite includes new upstream custody resume and drain reporting regressions.

The packed artifact SHA-256 was `6a4690f33552ab64f9abed64686dd2dc416c743b50896b36e2e74f20e13b5322`. Predictions, exact commands, timestamps, raw stdout/stderr, source hashes and limitations are retained beside this report. Concurrent-suite timings are not product performance measurements.
