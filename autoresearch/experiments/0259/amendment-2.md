# 0259 amendment 2: grading containers during a Docker file-share hang (2026-10-27)

This is a dated amendment to the frozen [DESIGN.md](DESIGN.md) (r2), the [registration](registration.md) and
[amendment 1](amendment-1.md).

**Timing.** It was written after all 64 final verdicts existed, so completions and assessor calls were known. It was
also written after the failed probe attempts described below. It was written before any probe or witness returned a
result on a measured tree.

## Observed failure

After the last measured verdict (d007's rerun, 2026-10-26T17:19Z), root started `judge.py probe` on the 32 F10 cells. The
first create request was at 17:20:08Z. No attempt returned a probe class. The preserved file holds 64 attempts on 32
cells, two per cell:

- **c001–c019, 38 attempts: `docker run` timed out after 60 s.** Docker Desktop's API log
  ([docker-create-log.txt](results/witness-runs/docker-create-log.txt)) has a `POST /containers/create?name=probe-…`
  request for each of these 38 attempts. None got a reply, and no probe container was ever started. c019's second
  attempt also records a failed `docker rm -f` cleanup at 17:58Z, as the restart began.
- **c020–c032, 26 attempts:** these ran while root was restarting Docker (below). Four (c020, c021) record that the
  daemon was unavailable. Twenty-two (c022–c032) record HTTP 500 from the not-yet-started engine.

Root believed it had stopped the probe run after 15 cells. It had not: the `pkill` pattern did not match the
interpreter's process name. The run finished all 32 cells at about 18:03Z, during the restart.

Root then established the following:
- **The hang depends only on the mount source.**
  - Any bind mount whose source is under `/Users` hangs at create, including `/Users` itself and a fresh `~/.cache`
    directory.
  - Mounts from `/private`, `/Volumes` and `/var/folders` start in about 2 s.
  - A container with no mount runs normally.
- **The hang survived a restart of Docker Desktop.** The first restart attempt left the VM failing with "The storage
  device attachment is invalid". A clean quit and relaunch recovered the VM, but not the `/Users` hang.

The cause is not known. No measured tree was read by any of the 64 attempts.

## Change

1. **The 64 attempts are set aside.** None of them is a probe result, so the probe rerun rule ("a missing or
   `unassessable` result is rerun once on the same tree") does not count them. That run's `probes.json` is preserved
   unchanged as `probes.docker-share-hang.json` in the runtime output, with a copy under
   [results/witness-runs/](results/witness-runs/). The probe then runs fresh on all 32 F10 trees.
2. **The judge mounts from `/private`.** `judge.py` accepts an optional `NX01_0259_JUDGE_SCRATCH` for its temporary
   snapshot copies. It mounts, from the same temporary directory, a sha256-checked copy of the witness file. Root sets
   the variable to a directory under `/private/tmp`.
   - **Unchanged:** the image, flags, user, network, timeout, command, snapshot copy and witness script bytes.
   - **Changed:** the host-side path. Also, `/witness` now holds only the script being run, not the whole witnesses
     directory. Neither the probe nor the D3 witness reads a sibling file.
3. **Everything else is unchanged:** the probe and witness rules, classes, the two-pass rule, the rerun rule, readiness
   and the decision.

The change does not read the arm, any outcome or any tree.
