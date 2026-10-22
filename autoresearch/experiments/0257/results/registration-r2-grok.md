I'll review `registration.md` against frozen DESIGN r5 and the round-1 findings, read-only, and check whether anything still blocks the measured run.Round-1 findings are resolved. The prediction matches frozen DESIGN r5, the registered account is round 3’s (`02b266ea50d2` / `531f8e153d6b`), and the measured-run launch conditions match the design.

- Codex window moves are attributed to the Claude assessors, and the round-3 deltas match the verdicts (0/1, 1/1, 0/1, 1/3).
- Round-1 codex-B is `EXITED_0` and then `STOP` with `assessment held: account/organization mismatch`.
- Rounds 1 and 2 are excluded from this registration, and a later account switch is a new registration.
- Real B installs on all 16 task trees are in `qual-install/`: I0185 has the skip line, both skills, and no `CLAUDE.md` or `AGENTS.md`; the other trees match the seal. `restore_i0185.py` is a launch step.
- 4 MB and 17 MB times 328 cells are about 1.3 GB and 5.6 GB. The deadline anchor is the round-1 dispatch, `2026-10-22T02:30:14Z`.

No findings.

VERDICT: SHIP
