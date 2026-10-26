VERDICT: SHIP
FINDINGS:
- [LOW] `autoresearch/experiments/0260/results/operator/judge.py:95` — After a finished `docker start -a`, a failed `docker rm -f` raises and discards that cell, including a real probe class or witness exit already held in memory. Create failures are not recorded, earlier cells stay written, `rm` is attempted on every path, and a start timeout is still stored as `unassessable` or exit 2. Record the completed start, attach the cleanup error, and raise only for create failures.
- [LOW] `autoresearch/experiments/0260/test_apparatus.py:863` — The marker test no longer checks that exits 2 and 1 stay `unresolved`, or that the daemon stderr is kept on exit 2. Restore both assertions.
