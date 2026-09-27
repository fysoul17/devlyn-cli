# 0225 replay — result

Registered in [0225](../../iterations/0225-resolve-cost-cuts.md) ("Replay (after step 2)" and "Replay mechanics"). The driver is [`replay.py`](replay.py) and the frozen manifest is [`replay-manifest.json`](replay-manifest.json) (commit `50fed13d`, pushed before the first call). Raw outputs are in `~/.local/share/nx01/0225-replay/`.

## Adjudication criteria (committed while round s6-04-r0 was running, before any result was read)

A binding HIGH counts as retained when an authenticated seat's HIGH/CRITICAL in that round (`score.json` `binding`: parsed from the output of a seat whose role evidence the merge retained) names the **same mechanism**, whatever its wording, id or file:line. The mechanism is the code path plus the failure, taken from the archived finding:

1. **s6-04 r1** (archived `spec-compliance.unbounded-writer-readiness`, `tests/test_types/test_File.py:98`): the FIFO test's wait for the writer to become ready (the readiness handshake, a wait, join or open) has no timeout, so the probe can hang forever. A finding about some other unbounded wait (for example the reader side only) does not count.
2. **s6-04 r2** (archived `spec.timeout-cleanup`, `test_File.py:76`): timeout or error cleanup cannot terminate a reader thread blocked on the FIFO open/read, so the thread survives cleanup.
3. **s6-16 r0** (archived `spec.rollback-marker-restoration`, `bin/devlyn.js:754`): the install marker is published (`writeInstallMarker` / rename to `markerPath`) before a later failure, and rollback neither removes nor restores it.
4. **s6-16 r1** (archived `spec.preserve-preexisting-content`, `writeInstallMarker`): a pre-existing file at the marker's temporary path makes the exclusive write fail with EEXIST, and cleanup then deletes that pre-existing file.
5. **s6-07 r0** (archived `spec-compliance.lock-release`, `bin/devlyn.js:782`): lock release is attempted once (`rmdirSync(lock)`), so one transient failure leaves the owned lock behind and blocks later installs.

A finding that names the right code but a different failure, or the right failure at a different path, does not count.

**Input BLOCKED.** An input BLOCKED is any harness row or early refusal whose cause is the judges' input (`score.json` `harness_rows`, `stops`, `input_flags`), or an authenticated seat's BLOCKED/coverage finding whose stated cause is a missing, unreadable or mismatched input. A seat BLOCKED that states a genuine product evidence gap (per the rubric's coverage rule) is not an input BLOCKED. An infra failure (limit, network, CLI crash) is recorded as such and counts against the pass: the only repeat is the registration's whole-replay repeat.

Each decision records the candidate row verbatim, and Astra verifies it.
