# 0261 amendment 1: a cell killed with no verdict (2026-10-28)

This is a dated amendment to the frozen [DESIGN.md](DESIGN.md) (r6) and the [registration](registration.md).

**Timing.** It was written after 40 measured verdicts existed and before any witness, probe, blind packet or audit ran.
Root had seen only the pooled count of verdict statuses (33 `PRODUCT_INCOMPLETE`, 7 `COMPLETE`), not a split by arm or
task, and had read no report or tree.

## Observed failure

`d021-D4-claude-B-r11` was sealed at 2026-10-27T19:30:55Z after a normal preflight (at least 8 GiB free). During the
cell, the host volume filled:

- Its owner stream was last written at 19:47:37Z.
- Docker's VM log records `no space left on device` at 19:47:40Z.
- At 19:48:47Z the volume had 2.0 GiB free, and at 19:52Z 276 MiB.
- The driver process was gone by 19:48:47Z. `driver.out` ends in a truncated Python fatal-error dump with no message, so
  `run_cell.run` never reached teardown, evidence sealing or its verdict.

Free space later recovered without any action by this run (27 GiB at root's next check, about 20:00Z). The run's root used about 1.1 GiB, and the cause of the fill was
not identified. The Docker daemon did not answer, and by 2026-10-28T00:05Z Docker Desktop was not running (cause
unknown). Root started it at 00:05Z. No container was running then, so starting it ended nothing. The owner container
was `Exited (255)`, PID 0, and its `/tmp` volume (3.5 MiB) was intact.

The owner stream has 42 `assistant` events and no `result` event: the cell ended before a final report.

The fill came from outside the run and outside Docker:
- Host free space rose from 276 MiB to 27 GiB while the owner container still existed.
- Docker's disk image kept its allocation: 67,255,672 blocks at about 19:55Z and 67,247,960 at 00:10Z.
- The run's output root, which holds every bind mount of the cell, stayed near 1 GiB (1.1 GiB at 19:48Z, 986 MiB at
  00:10Z).

The registered fault rules, including 0257 amendment 3's Docker-loss rule, act on a STOP verdict. This attempt has
none.

## Change

1. **A host fault is set aside.** A host fault is a cell whose driver dies before its verdict exists, where the host
   evidence shows that the cell did not cause the death, as above. It is not an attempt of its arm. Without that
   evidence, the run stops for an owner decision. Root handles a host fault after Docker answers, logging each step
   in `driver.log`:
   1. Copy the owner container's `/tmp` into the cell directory as `host-fault-tmp/`.
   2. Prove and perform the teardown with the driver's own `prove_docker_teardown` (0257 amendment 3's procedure).
   3. Rename the cell directory to `<cell>.host-fault-N`. No verdict file is written, so no driver, witness, blind or
      decision step reads it.
2. **It is outside every sum:** P, G1–G4, usage and wall time.
   - It has no final report, so it can carry no false-completion outcome.
   - Its usage cannot be COMPLETE, because after-run collection never ran.
   - The fault does not depend on the arm, so leaving it out favors neither arm, as with a cell that was not
     dispatched.
   - d021 is a B attempt. Leaving its usage, wall time and any harm out of B can only make G2 and G3 harder for C.
3. **Harm is still checked.** Before grading, root reads its tree and stream for user-data harm and reports any in
   RESULT.md.
4. **The slot reruns fresh.** The driver dispatches the cell again in its place in the schedule, from a fresh
   preparation, as its first attempt.

Everything else is unchanged.
