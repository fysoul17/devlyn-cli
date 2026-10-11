# 4.2.5 integration verification

PASS on upstream `d1f170ed3bd57441b95ea525156e80644543acb1` (4.2.5), with the nine accepted product deltas. All twelve bound input files and source HEAD stayed unchanged. This is integration evidence; the earlier 4.2.4 native experiments retain their own version.

| Check | Result |
| --- | --- |
| Locked Node20.19.0/npm10.8.2 installation | PASS, metadata unchanged |
| Six focused cleanup regressions on macOS | 4 pass, 2 Linux-only skips |
| Actual packed installer | 72/72 PASS |
| Installer menu | 15/15 PASS |
| Full Linux completion helper | 73/73 PASS, zero skips |
| Required lint | PASS; includes macOS helper 71 pass +2 Linux-only skips, contract4, queue9, acceptance13 |
| Full ideate loop integration | 71/71 PASS |
| Working/index diff checks | PASS |

The Linux run used the pinned image, no network or credentials, --init and PID256. The self-removing container exited0. Native study owners were stopped throughout verification. Review and tests ran concurrently; these test timings are not product model-performance measurements. Original commands, predictions, timestamps, stdout/stderr and before/after input hashes remain beside this report. The original manifest precedes this report and is preserved unchanged; the separate evidence-copy manifest additionally binds this report.
