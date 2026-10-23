# 0257 amendment 3 — Docker daemon loss during a cell (2026-10-23)

Dated amendment to the frozen [DESIGN.md](DESIGN.md) (r5), the
[registration](registration.md), [amendment 1](amendment-1.md), and
[amendment 2](amendment-2.md). When asked whether to discard and rerun the
cell broken by Docker being off, the owner answered "추천대로".

## Observed failure

At 2026-10-23T09:34:17Z Docker Desktop quit while
`d058-I0185-claude-A-r4` was running; the cause is unknown. Its verdict is
`STOP`, `teardown=FAILED`, `identity.status=MATCH`, and
`owner_status=EXITED_NONZERO`. The teardown error says `Cannot connect to the
Docker daemon`. After Docker returned, the owner container was present in
`Exited (255)` state. DESIGN §Operations otherwise stops the run for this STOP.

## Change

A STOP with `teardown=FAILED` and `Cannot connect to the Docker daemon` in
its teardown error or reason is an infrastructure fault. After the normal
readiness check confirms Docker is available, the driver reads the attempt's
`run/started.json` to identify the owner container name and unique `/tmp`
volume. It lists containers attached to that volume, inspects each, and
requires the recorded owner to be among them. Every such container must have
stopped with PID zero and match the attempt's volume and owner label. The
driver removes them with `docker rm`, verifies that neither the volume nor
the recorded owner name has a remaining container, then removes the recorded
`tmp_volume` with `docker volume rm`. It verifies the volume is gone with
`docker volume ls -q --filter name=^<volume>$` and records the found and
removed containers and removed volume in `driver.log`. If identification,
stopped state, removal, or verification fails, the run stops with the original
verdict intact.

Normal 0233 teardown copies the container's `/tmp` volume to the host before
removing the volume. For a Docker-lost attempt, the daemon was gone before that
collection, so its container `/tmp` is not preserved. The archived attempt
keeps everything already written to the host.

After successful proof, the driver archives the verdict and cell directory as
`.stop-N` and redispatches the cell, as for a quota fault. Only the final
verdict is scored. Archived attempts contribute their wall time and usage to
the slot's reported attempt costs and remain in the mandatory post-run
user-data-harm audit. A STOP with matching identity does not set the harm
latch; identity failures still latch before any archive. Other teardown
failures still stop.

The rule does not read the arm: A and B get the same proof, archive, fresh
rerun and cost charge. It is not proven bias-free, though. An outage
interrupts whichever attempt is running, and longer attempts are more
exposed, so if one arm's failing attempts tend to run longer, replacing
interrupted attempts can shift that arm's final rate. The RESULT reports
every Docker-lost attempt by arm so this can be checked.
The schedule, caps, deadline, scoring, identity rule, and all other registered
controls stay in force.

## Operator steps

Update the run worktree to include this amendment and relaunch the driver
with the existing schedule. No other step is required.
