# Linux cleanup observation proposal

2026-10-10. **Proposed only; canonical and installed product files unchanged.**
No model calls, network-dependent tests, task/runtime changes or historical
regrading. The scratch copy is under the owned 0237 completion receipt.

## Finding and smallest fix

The d03 causal evidence is in [cleanup-zombie-audit.md](cleanup-zombie-audit.md).
A real, isolated Linux reproduction confirms that an unreaped single-thread
child of PID 1 has `State: Z`, `Threads: 1`, inaccessible `/proc/PID/fd`, and
missing cwd at uid 501. The original helper raises `WritersUnobservable`.
That process cannot write; the refusal creates an unnecessary cleanup recovery
step.

A second real control prevents an unsafe shortcut: a leader that calls
`pthread_exit` remains `Z` while a sibling writes. At uid 501 the original
helper refuses on fd permission denial. At uid 0 it sees `fd=[]`, encounters
missing cwd, and **incorrectly returns success while the heartbeat grows**.
Skipping every Z process or checking cwd before fds would be unsafe. Linux
explicitly documents that leader termination makes the process fd interface
unavailable even when other threads survive. [Linux proc_pid_fd(5)](https://man7.org/linux/man-pages/man5/proc_pid_fd.5.html)

[cleanup-zombie-proposal.patch](cleanup-zombie-proposal.patch) adds 18 net
production lines and six regression tests to `task-complete.py`:

- After permission denial, continue only when one fresh status read proves
  exact `State: Z (zombie)` **and** `Threads: 1`.
- When cwd is missing, require fresh `Threads: 1`, then **continue checking the
  already enumerated file descriptors**. Multiple/unknown threads retain.
- Unreadable/malformed evidence retains; actual process disappearance during
  the existing missing-process path remains tolerated.

The shared status reader serves those two observed failure paths. No process
termination, owner-descendant exemption, kernel-thread exemption, configuration
bypass, cleanup shortcut or new root instruction is added. The owner’s explicit
`--writers-stopped`, directory identity, mount, symlink and Git custody gates
remain unchanged.

## Causal controls and validation

Predictions were persisted before their experiments. Raw outputs, scripts and
hashes are retained in
[cleanup-zombie-proposal-evidence/manifest.json](cleanup-zombie-proposal-evidence/manifest.json).
All Docker tests use the same immutable image recorded there and Linux
`6.10.14-linuxkit`.

| Real control | Original | Proposed |
| --- | --- | --- |
| uid 501: ordinary unreaped zombie, Z/1 | Unobservable refusal | Observation succeeds |
| uid 501: Z leader/2 threads, growing writer | Retained | Retained |
| uid 0: Z leader/2 threads, growing writer | **Incorrectly permitted** | Retained |
| uid 501 and 0: ordinary live cwd holder | Active writer | Active writer |
| uid 501 and 0: live nondumpable fd holder | Not separately run | Unobservable refusal |
| All fixture children reaped | Observation succeeds | Observation succeeds |

Real CLI tests additionally establish that an ordinary zombie permits owned
scratch cleanup only with the explicit owner assertion, while the threaded
zombie preserves the growing artifact. Mocked edge controls cover missing or
unreadable status, denied living processes, missing cwd with no fds, missing cwd
with an active fd, multiple threads, and vanishing individual fds/processes.

- Before the fix, the new positive test failed with the original fd
  `PermissionError` → `WritersUnobservable`; the two negative tests passed.
- Proposed focused host tests: 6 passed, 4.761 s.
- Proposed uid 0 focused CLI/edge tests: 3 passed, 0.936 s.
- Proposed complete Linux suite: **71 passed, 54.380 s**, including all 65
  existing tests and six additions.
- Both real uid 501/uid 0 probe scripts exited 0. `git apply --check` passed.

The first full-suite container used Python as PID 1 and `pids-limit=128`.
After 21 successful tests, 50 fixture setups failed with Git fork/thread
resource exhaustion. Those failures are retained. Orphan accumulation is an
inference because that removed container’s final PID inventory was not saved.
The unchanged suite passed with Docker `--init` and the same PID limit; the
intentional unreaped children remain owned by the test process, so init cannot
remove the regression stimulus.

A separate read-only VM host-PID control found 170 kernel threads. With ptrace
read permission all had observable cwd; the predicted missing-cwd kernel-thread
example was **not observed**. Without that permission, the first kernel thread
already produces the existing permission-denial refusal. No compatibility
claim about all Linux hosts follows. The single-thread missing-cwd/no-fds
control is synthetic and preserves the existing observable-handle contract;
it is not presented as an observed kernel-thread case.

## Identity, races and limits

A single opened proc status file remains bound to its process; it does not
switch to a later process merely because the numeric PID is reused. The probe
opened a proc directory, reaped its child, and observed `ESRCH` on a relative
status lookup, consistent with the kernel contract. Actual PID reuse was not
forced. [Linux proc filesystem documentation](https://docs.kernel.org/filesystems/proc.html#process-specific-subdirectories)

The proof follows failed access, rather than caching a state before fd
observation. State and thread count come from the same opened status file.
Linux defines `Threads` as the number of threads in the containing process.
A Z leader alone is insufficient; Z plus a one-thread group has no surviving
thread to write. [Linux proc_pid_status(5)](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)

This preserves the existing observation boundary, not an atomic process lease:
a new process/thread or fd can appear after a scan. The owner must still stop
its actual writers and attest to that. Permission-denied status that vanishes
before terminal evidence conservatively retains. Broader hidepid, different
kernels and all host security configurations were not exercised.

Canonical and `.agents` helper SHA-256 remains
`bf4301f4e298305d14ec162a68a36ee6430050e3a2eaf7ab55eb99b5ee49f835`.
Proposed copy SHA-256 is
`60e101dd720348207a6001432a2b6f66f3c861846b1e768af5456804a402ac8a`.
No shipping decision or model-efficiency lift is claimed by these controls.
