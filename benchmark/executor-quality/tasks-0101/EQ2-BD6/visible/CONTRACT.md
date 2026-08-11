# Pick-wave contract

A rejected pick wave leaves the inventory store byte-identical to its pre-wave form, the shortage reporter orders invalid before conflict before shortage with arrival order breaking equal-reason ties, and when accepted picks precede validation and conflict failures the highest-priority error is reported while every earlier inventory change is rolled back.

`executePickWave` owns the transaction around inventory changes. A physical
write or wave-commit fault aborts that transaction and restores the exact bytes
captured before the wave began.

`ShortageReporter` depends on that transaction remaining open through
`conclude()`. It receives every rejected row with the row's arrival index,
orders the reasons by the precedence above, and throws `BatchReject` with the
complete ordered issue list. The executor must let that dependent rejection
abort the same transaction before committing the wave.
