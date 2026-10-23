**SHIP**

No HIGH, MEDIUM, or LOW findings.

The proof only removes a container that `docker ps --filter volume=<recorded tmp_volume>` listed, whose inspect `Id` matches that line, whose `Mounts` contain that volume, whose label is `devlyn.task=0233`, and whose `State.Running` is false and `Pid` is 0 (`driver.py:318-332`). Any other container on the list aborts before `docker rm`. `docker rm` is not `-f`, and `docker volume rm` still runs only after a second volume listing and a name listing are empty (`driver.py:333-337`). A container that still mounts the volume fails `volume rm`. The recorded name comes from this attempt's `run/started.json` `create_argv` (`--name` once, and the exact `type=volume,src=<tmp_volume>,dst=/tmp` element). That file is written by `0233/cell.py:157-159` before start and is not under the container's mounts.

Archive happens only after `prove_docker_teardown` returns (`driver.py:370-378`). A failed proof calls `stop` and leaves `verdict-<cell>.json` in place (`driver.py:339-341`). The quota branch still archives without this proof; its reason is `shared account fault during execution:`, which `run_cell.py:298-303` uses only when teardown was already `CLEAN`. The fresh `rc == 2` path does not archive (`driver.py:397-402`); the next `ready()` pass does.

`latch_for` runs before proof and archive (`driver.py:356-373`). A `STOP` with `identity.status=MATCH` does not latch, including `teardown=FAILED` (`driver.py:185-191`). `MISMATCH`, `UNVERIFIED`, and launched `UNKNOWN` latch and `assert_active` raises before any `docker rm` or rename.

`slot_cost` charges an archived attempt when `teardown==FAILED` and the daemon sentence is in `teardown_error` or `reason` (`decide.py:140-143`), then adds the final attempt. `run_cell.py:288-322` stores that sentence only in `reason` (`teardown failed: ` plus the cell's `teardown_error`) and still sets `teardown=FAILED`. Both `docker_fault` (`driver.py:61-64`) and `slot_cost` see that form. Completion still comes only from the final verdict (`decide.py:167-169`, `204`).

`amendment-3.md` matches this order, the lost `/tmp` copy (`0233/cell.py:175-179` never reaches `preserve_tmp` if inspect cannot reach the daemon), the latch rule, and the other-teardown stop. The rule does not read the arm. A and B share one proof, one archive, and one cost charge, so a daemon stop does not favor either arm. For the observed `MATCH` verdict, relaunch after Docker is back is the only operator step: `ready()` reaches `image()` only when `docker image inspect` works.

