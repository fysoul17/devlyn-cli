Round 4 (narrow confirmation) of a read-only apparatus review in the devlyn-cli repository (do not edit files, run nothing live).

Read results/apparatus-r3-astra.md and apparatus-r3-verification.json, then the changes in commit c636fb87 (capture.py, test_capture.py, test_grading.py).

Check only: the git push scan consumes values of -o and of unambiguous prefixes of --push-option/--repo/--receive-pack/--exec before dry-run detection; help is push-scoped; a dry run is recognised only when certainly present and any unclassified push argument leaves the push unresolved; setting pushed true still requires a single sealed successful command; flags() is unchanged; no new HIGH or MEDIUM problem. Do not reopen anything else.

Report findings with severity, file:line and a concrete fix. End with exactly one final line: `VERDICT: SHIP` or `VERDICT: REVISE`.
