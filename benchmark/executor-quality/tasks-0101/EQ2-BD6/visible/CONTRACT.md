# Pick-wave contract

A rejected pick wave leaves the inventory store byte-identical to its pre-wave form, the shortage reporter ranks invalid before conflict before shortage with arrival order breaking equal-reason ties, and when accepted picks precede multiple failures the highest-priority error is reported while the reporter accumulates only zone shortages that remain after rollback.

`executePickWave` owns the transaction around inventory changes. A physical
write or wave-commit fault aborts that transaction and restores the exact bytes
captured before the wave began.

`ShortageReporter` owns a persistent zone ledger. It receives every rejected
row with the row's arrival index, ranks the complete issue list, and records
only shortage quantities still missing from inventory after a rejected wave
has been rolled back. The executor must restore inventory before handing the
rejected wave to this dependent component; otherwise earlier tentative picks
inflate the reporter's accumulated shortage state.
