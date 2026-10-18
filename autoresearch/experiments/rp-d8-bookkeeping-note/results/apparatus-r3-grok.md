# apparatus-r3 — grok

I'll review the round-2 notes and commit `c855a7ec` read-only, then check only the dry-run recognition and failed-compound evidence paths.Round-2 left A1/G2 and G1 open. I'll read the push dry-run check and the failure-evidence path in the current code next.A1/G2 and G1 hold in `c855a7ec`. No new HIGH or MEDIUM problem on these paths.

**A1/G2.** The push-only scan in `capture.py:218-234` marks a dry run for an unambiguous `--dry-run` prefix (`len >= 4`, so `--dr` through `--dry-run`; `--d` stays out) and for a short cluster with `n` before the first `o`. `-on`, `-uon`, and `-o -n` stay real pushes: `-o` keeps the rest of the cluster, or the next argument, as the push-option value, and `--` stops the scan. `flags()` at `capture.py:168-180` is unchanged. A dry run leaves `push_command_observed` false, so a sealed success does not set `pushed`.

**G1.** `capture.py:362-363` saves the tool failure before the single-command mask. `capture.py:388` stores that bit on push and remote-creation attempts, and `capture.py:401-404` fills `*_failure_evidence` when every attempt failed. `grading.py:166-170` then accepts agreed `run/stdout` citations, so `pushed` and `remote_created` can become false. An exit-0 compound such as `|| true` has no failure bit, so it stays unresolved and unknown. `capture.py:380-381` still sets either fact true only for one successful command.

No new HIGH or MEDIUM finding.

VERDICT: SHIP
