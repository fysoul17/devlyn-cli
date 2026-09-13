# 0160 — Wait for native bootstrap cessation

2026-09-13. Root resumes the user's “계속 진행” and directly repairs the
Windows enrollment failure observed during0159 delivery. Frozen0159 remains
INCOMPLETE_INFRASTRUCTURE; this is a separate product defect, not a comparison rerun.

## Why and prediction

Pre-flight0: remove a real process-ownership failure in task cleanup.
Mission1: reliable single-task execution requires owned processes to cease before
successful teardown. No model/pair superiority claim follows.

At baseline8d8c59a2f85d316a7212a8dea693e2731c7f5f30, bootstrap enrollment fails
before the process joins its Job Object. Parent teardown calls `poll`, `kill`,
then `Popen.wait`. CPython3.12.10 `kill` may catch access denied and cache an exit
code while the process handle is still unsignaled; `wait` then returns the cached
code. Job member enumeration cannot cover this unenrolled process.
The [CPython source](https://github.com/python/cpython/blob/v3.12.10/Lib/subprocess.py)
identifies that path; `poll` itself checks the native signal and is not the defect.

Before running, root registered200 native enrollment observations: a non-null
cached code together with independent `WAIT_TIMEOUT` after `wait` would support
the hypothesis. No retry-until-failure or altered historical scoring.

## Evidence and repair

[Native baseline](https://github.com/fysoul17/devlyn-cli/actions/runs/34727859268):
200 samples,31 cached codes after kill,30 unsignaled handles after wait,
24 cessation assertion failures and12 secondary fixture-cleanup access-denied
errors. Some processes finished between observations. Counts describe this
instrumented sample, not production incidence or historical scheduling.
This is distinct from0150's PID-list/object-lifetime fixture preconditions.

Replace cached `Popen.wait` with the standard `_winapi.WaitForSingleObject` binding
on the retained child handle. Keep the existing5-second bound, explicit
`subprocess.TimeoutExpired`, kill attempt and finally-close. Native wait failures
raise through the binding. Existing job-member barriers and POSIX behavior stay.
The tracked installed mirror has the identical fix.

[Native candidate](https://github.com/fysoul17/devlyn-cli/actions/runs/34728035598):
the registered200 observations have zero cessation failures and zero cleanup
errors. A new real-process regression deliberately supplies a cached code while
the handle is unsignaled: original source fails both cessation and required
timeout assertions; candidate passes both, including handle closure. This
controlled state checks the barrier; natural observations independently establish
its producer. Both original and candidate source hashes were verified.

Local portability passes35 tests with17 native-only skips. Independent actual
Fable5.1 design review supports the replacement; Grok4.6's requested native
smoking gun is satisfied. Root retains existing explicit kill-error behavior;
the observed cached-code repair does not establish cleanup after arbitrary API
failure. Final source review, full checks and delivery evidence are recorded
separately under `.devlyn/0160/` and `.devlyn/0160-delivery/`.

**No guesswork / No workaround:** measured native signal, no test sleep or
weakened assertion. **No overengineering / Optimized:** replace the existing wait;
no extra phase, retry loop or router. **Best practice:** use CPython's native API
binding. **Worldclass / Production ready:** explicit timeout/error, real-process
regression and independent review. Deleting the new wait restores the measured
failure; deleting the regression loses cached-code and timeout coverage.
Temporary diagnostic scripts/workflows are removed from the accepted tree;
their commits and raw results remain recoverable. No npm release.
