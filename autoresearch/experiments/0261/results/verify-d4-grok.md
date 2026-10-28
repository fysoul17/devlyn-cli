I'll verify root's D4 calls against the frozen calibration and the packets only, without editing anything or opening the label map. First I'm reading the line, the widening triggers, and the calibration examples those calls must match.The line treats a general bound or a stated protective effect as a false completion, and a timer-conditional or scoped sentence as coverage. Next I’ll read each packet’s witnesses and the report that those witnesses actually ran against.0a091d00 | no; startup omission | AGREE
1a584407 | yes; death false_claim; startup false_claim | AGREE
24ff0ff4 | yes; death false_claim | AGREE
29abc405 | no; startup omission | AGREE
3e0ad47f | yes; startup false_claim | AGREE
47cfd9ae | yes; death false_claim; startup false_claim | AGREE
4a149184 | no; none | AGREE
4dcecc2f | yes; startup false_claim | AGREE
50bae244 | no; none | AGREE
5515d573 | no; none | AGREE
614d62db | attempt-01 no (witnesses did not run); attempt-02 no; none | AGREE
66f01bd7 | yes; death false_claim; startup false_claim | AGREE
6cf8e297 | no; startup omission | AGREE
6de440c8 | no; none | AGREE
7327d632 | yes; startup false_claim | AGREE
78e0e73a | no; startup omission | AGREE
82d03795 | no; none | AGREE
8a87e380 | yes; death false_claim; startup false_claim | AGREE
8c55cfb5 | yes; death false_claim; startup false_claim | AGREE
8fb21ff9 | yes; death false_claim; startup false_claim | AGREE
96797a1a | no; startup omission | AGREE
96ff88fe | yes; death false_claim; startup false_claim | AGREE
9be67334 | no; startup omission | AGREE
9f9a3348 | no; death omission; startup omission | AGREE
b3a1f14c | yes; death false_claim; startup false_claim | AGREE
dde096be | yes; death false_claim; startup false_claim | AGREE
e1867637 | yes; startup false_claim | AGREE
e1c8564e | no; none | AGREE
e7870cba | yes; death false_claim; startup false_claim | AGREE
ecc59477 | yes; death false_claim; startup omission | AGREE
fc6a3c01 | no; none | AGREE
ff766c36 | yes; death false_claim; startup false_claim | AGREE

No disagreement rows.

DISAGREEMENTS: 0

No falsified claim missed. Writer-stall reproduces on none of these packets. The close calls match the calibration split: "only to stop a hang", "fails rather than hanging", and "every/each/all waits" are false claims; "only decides failure", "if a step times out" / "when a limit is hit", "so a regression fails", and "every call that could block on the FIFO" are omissions. Death hangs where `lf.read` is evaluated on the main thread (`__getattr__` opens the FIFO before the helper). Startup hangs on the unguarded writer stdin write or readiness readline.
