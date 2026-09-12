# 0150 — Establish native process-lifecycle fixture preconditions

2026-09-12. Resumes the existing allocation after the owner requested unfinished
HANDOFF work. Root implements without resolve; actual independent Fable 5.1 and
Grok 4.6 review each candidate. This closes the Windows CI blocker discovered
during 0149 delivery. A16 and frozen research remain unchanged. No npm release.

## Two observed invalid assumptions

**Signaled process ⇒ absent from Job Object PID list.** The two gated admission
fixtures expected exactly two PIDs immediately after waiting for bootstrap exit.
[Registered baseline](https://github.com/fysoul17/devlyn-cli/actions/runs/34674678317):
40 tests, 60 initial observations, five failures. Every extra PID was the known
bootstrap with a signaled handle (`0`); A and B were live (`258`). Five secondary
fixture-cleanup access-denied errors are preserved separately.

Both tests now establish bootstrap PID disappearance with the existing bounded
`wait_for`, then assert the exact A/B set. The same precondition follows A exit
before the B-only capture assertion. A's delayed removal was not observed;
that extension follows the same violated ordering assumption at its caller.
Production teardown, zero admission limit, buffer growth, capture/wait and
handle-close assertions stay unchanged. No widened count or fixed-delay sleep.

**Wait plus closing fixture handles ⇒ `OpenProcess` fails immediately.** The
[first whole-suite final CI](https://github.com/fysoul17/devlyn-cli/actions/runs/34674979922)
passed those modified tests but failed the unchanged stale-list fixture:
`OpenProcess(gone.pid)` returned handle 860. That log does not identify its
liveness or remaining reference owner. A fixed twenty-run natural diagnostic
returned error 87 throughout; no retry-until-failure was used.

A [controlled real observer handle](https://github.com/fysoul17/devlyn-cli/actions/runs/34675491615)
provides a deterministic counterexample: after the fixture closes its handles,
the first probe still opens the terminated process (`wait == 0`), failing the
old assertion. The observer releases its extra handle immediately after that
probe, without a timed delay. This establishes an invalid fixture assumption,
not the exact historical CI reference holder or mechanism.

The stale-list test now establishes actual error 87 with bounded polling. Every
successful probe must be signaled and is closed in `finally`; a live/reused
process or a different open error fails visibly. The production stale-list
87 branch, different-job identity rejection and unrelated survivor checks stay.
The [process-termination contract](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess)
distinguishes exit from object lifetime; the [job PID-list contract](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_process_id_list)
does not establish the ordering the old fixture assumed. No universal kernel
removal deadline or guarantee against later PID reuse is claimed.

## Verification and limits

| Native execution | Result |
| --- | --- |
| Membership candidate-r0 / final candidate | 40/40 each; zero failures/errors; 9/5 transient bootstrap entries still observed |
| Persistent bootstrap / unexpected member controls | Bounded timeout / exact-set rejection; deliberate failure cleanup errors retained |
| Natural unchanged gone-PID diagnostic | 20/20; original CI symptom not reproduced |
| Controlled retained-reference old / corrected test | Old assertion fails / corrected complete test passes |
| Final gone-PID controls | 20 natural + 1 retained-reference pass; live-process and error-5 injections reject; zero cleanup errors |

[Final native controls](https://github.com/fysoul17/devlyn-cli/actions/runs/34675579169)
bind the exact driver/source hashes. Native samples are component evidence, not
a platform guarantee. Local portability passes in 23.344s (native tests skipped
on macOS). Full local lint passes in 294.374s after an initial installed-copy
mismatch; original failure and an interrupted premature retry are retained.
[Whole POSIX/Windows CI](https://github.com/fysoul17/devlyn-cli/actions/runs/34675579125)
passes the complete behavioral repair. Fresh whole-source Fable 5.1 review is
**PASS_WITH_ISSUES** (103.295s); Grok 4.6 is **PASS** (186.035s), with no
CRITICAL/HIGH findings. Both identified the new live-PID diagnostic's misleading
teardown wording. Root replaced it with fixture-specific text, preserving the
exact condition and `finally` close. The [exact-source live control](https://github.com/fysoul17/devlyn-cli/actions/runs/34675872946)
rejects with that message and no cleanup errors; both fresh delta reviews **PASS**.
Native model identity, prompt/output hashes and final driver bytes are checked.
Root accepts **PASS_WITH_ISSUES**; final PR integration/delivery remains separate.

The existing fixture helper's `python -O` timeout behavior and failure-cleanup
handle closure remain LOW advisories. Canonical CI uses ordinary Python.
Deliberately rejected controls are never counted as successful product teardown.
Temporary diagnostic scripts/workflows are removed from the accepted tree;
failed apparatus setup and cancelled duplicate CI remain in raw history.

**No guesswork / No workaround:** identify actual states and establish required
fixture conditions, preserving all failure evidence. **No overengineering /
Best practice:** reuse bounded fixture waiting; no production helper or flag.
Deleting these precondition checks restores the violated assumptions; the probe
`finally` prevents its own handle from keeping the process object open.
**Worldclass / Production ready:** final acceptance requires independent review
and actual native/full checks. **Optimized:** no harness speed, semantic recall,
model or pair superiority claim follows.

Raw evidence: retained research checkout `.devlyn/0150/`. Existing receipt
`fbe3985ee021a2112645ac15` owns source acceptance, delivery and custody separately;
its pre-scratch allocation is reused without reset or retroactive enrollment.
