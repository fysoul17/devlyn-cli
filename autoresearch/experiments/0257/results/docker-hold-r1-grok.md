**SHIP.**

`Driver.image` holds on a failed `docker load` and still raises after a successful load whose id does not match. While the daemon is down, `driver.run` / `ready` do not reach another Docker call, and the hold does not let a cell start.

No findings.

The between-cell gate is `ready` → `image` (`driver.py:289`). `image_identity` already turns a dead daemon into `False` (`run_cell.py:158`) because `docker image inspect` fails. The only following Docker call is `docker load`, and `CalledProcessError` now logs the first stderr line and returns `False` (`driver.py:212`). `run` sleeps 60 seconds and retries (`driver.py:372`). `dispatch` is not entered, so `prepare.install`, `codex_limits`, and `cell.py`'s `docker()` do not run on this path. A missing `docker` binary is `FileNotFoundError`, which is not the daemon-down failure that raised `CalledProcessError`.

A non-zero load, including a bad tarball or a full disk, is held the same way as a missing tarball (`driver.py:207`): the reason is logged, no cell is dispatched, and the deadline and harm latch still run at the top of the loop. A load that exits 0 and then fails the id check still raises `RuntimeError` (`driver.py:217`). The new test covers the retry; that raise is the unchanged line after the `except`.

