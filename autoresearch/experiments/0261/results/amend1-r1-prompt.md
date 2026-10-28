You are a read-only reviewer for a pre-registered A/B experiment in this repository. Do not modify any file. Do not
read anything under ~/.local/share/nx01 or any cell output: the run is blind until grading, and you must stay blind.

Experiment: autoresearch/experiments/0261/ (DESIGN.md r6 is frozen; registration.md lists frozen identities).
Apparatus: driver.py, run_cell.py, decide.py, blind.py, results/operator/judge.py in that directory.
Precedents: autoresearch/experiments/0257/amendment-3.md (Docker loss during a cell, STOP verdict archived as .stop-N
and rerun), 0259/amendment-1.md and 0259/amendment-2.md (format and timing conventions).

New file to review: autoresearch/experiments/0261/amendment-1.md (untracked; written during the measured run).

What happened, in short: during measured cell d021-D4-claude-B-r11 the host volume filled, Docker's VM logged "no space
left on device", and the driver process died with no verdict written. 40 measured verdicts exist. Root already acted
under the amendment: it copied the owner container's /tmp volume into the cell directory, ran the driver's own
prove_docker_teardown (logged as docker_teardown_proven, one exited owner container and its volume removed), renamed
the cell directory to d021-D4-claude-B-r11.host-fault-1, logged host_fault and host_fault_set_aside events, and
relaunched the unchanged driver at the registration commit, which skipped the 40 finished cells and dispatched d021
fresh. No witness, probe, blind packet or audit has run.

Review questions:
1. Is the amendment consistent with DESIGN.md's readiness rule, its "one outcome per slot" rule, the registered fault
   rules and 0257 amendment 3? Name any rule it silently overrides.
2. Is setting the attempt aside (outside P, G1-G4, usage and wall time) unbiased or conservative? Is the exogeneity
   condition ("host evidence shows the cell did not cause the death") well defined and actually met by the evidence
   listed? Could it bias toward ADVANCE if a later C cell dies the same way?
3. Does any apparatus code read, glob or break on a `<cell>.host-fault-N` directory, or on a missing verdict for a
   slot that is later re-run (check decide.py, blind.py, judge.py, driver.py, run_cell.py, prepare.py)?
4. Is the timing and blindness statement honest and sufficient?
5. Anything wrong, unclear or removable in the text.

Answer with a verdict line `VERDICT: SHIP` or `VERDICT: REVISE`, then findings, each tagged HIGH, MEDIUM or LOW with
the file and line and a concrete fix. Keep it short.
