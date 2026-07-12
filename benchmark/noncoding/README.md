# Non-coding admission kernel

This directory contains the disjoint calibration namespace for the `pud-1`
packet-to-executor instrument. `manifest.json` is the only fixture inventory.

`scripts/run-packet-attempt.py` validates the frozen fixture and packet, creates
an opaque workspace under `~/.local/share/nx02`, invokes the explicitly selected
Terra or isolated Sonnet seat, then records the hidden oracle's raw stdout,
stderr, exit code, wall time, and provenance. An attempt is `resolve`, `fail`, or
`INVALID`; invalid attempts never enter calibration counts.

`scripts/run-calibration.sh` runs a randomly interleaved T0 or T1 cohort and
records its replay seed. It refuses a dirty `benchmark/noncoding` tree so the
manifest's `runner_commit_sha` binds the measured runner. Do not run calibration
during the BUILD step.

The checked-in fixture packets and hidden inputs are frozen before T0. If T0 or
T1 fails, report the instrument dead; do not retune these fixtures.
