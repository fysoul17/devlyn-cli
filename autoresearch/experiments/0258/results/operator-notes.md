# 0258 operator notes (root's observations, not in `driver.log`)

Recorded by root on 2026-10-25 from commands run during the measured run. These facts are outside the retained driver
log; the log itself shows d027 `rc 3` at 09:51:16Z followed by 52 `skip_finished` lines at 10:06:49Z.

- 09:51Z (before the restart): `not-dispatched-d027-D3-claude-C-r14.json` read
  `{"reason": "output volume has 6606614528 bytes free, below 8589934592"}`. A later 429 refusal of the same cell
  (12:06Z) overwrote it; the file now carries the 429 reason.
- 10:06Z: `sysctl -n kern.boottime` gave `Sun Oct 25 18:59:49 2026` KST (09:59:49Z); `uptime` 6 minutes. The driver PID
  was gone and the Docker socket refused connections. No measured cell directory existed for d027, so no cell was in
  flight.
- After the restart `df -h` showed 29 GiB available on the data volume. Root ran `open -a Docker`, then
  `docker images` showed `devlyn-0256:latest 25d47afd9a3a` (the registered image ID prefix) and `docker ps -a` showed
  no cell or witness container. Root relaunched `driver.py <runtime.json> cells.tsv` from the detached checkout at
  `18c3423a`.
- The restart was not initiated by root. Its cause is not known.
