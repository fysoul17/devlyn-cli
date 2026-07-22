"""
P1 - Requirement 1 (chainability, both call orders) + Requirement 6
(ValueError validation matrix: wrong type, <=0, non-integral, bool).
Pre-implementation baseline: Job.max_runs does not exist, so this is
expected to fail with AttributeError on the first call.
"""
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
import schedule


def job_fn():
    pass


def fail(message: str) -> None:
    sys.stderr.write(message + "\n")
    sys.exit(2)


# Requirement 1: chainable setter usable anywhere in the fluent chain,
# in both orders, and returns the Job instance itself.
schedule.clear()
j1 = schedule.every(5).seconds.max_runs(3)
if j1 is None:
    fail("max_runs(n) must return the Job instance")
j1_after_do = j1.do(job_fn)
if j1_after_do is not j1:
    fail("do() must still return the same Job instance")

schedule.clear()
j2 = schedule.every().max_runs(3).seconds
if j2 is None:
    fail("max_runs(n) must return the Job instance (pre-unit order)")
j2_after_do = j2.do(job_fn)
if j2_after_do is not j2:
    fail("do() must still return the same Job instance (pre-unit order)")

# Requirement 6: n must be int >= 1; anything else raises ValueError
# at .max_runs(...) call time (not at .do() or run time), with an
# inspectable error payload (not a bare/silent exception).
invalid_values = [0, -1, -5, 2.5, "3", None, 1.0, True, False]
for bad in invalid_values:
    schedule.clear()
    try:
        schedule.every().seconds.max_runs(bad)
    except ValueError as exc:
        payload = str(exc)
        if not payload.strip():
            fail(f"ValueError for max_runs({bad!r}) must carry a non-empty payload")
        sys.stderr.write(f"max_runs({bad!r}) correctly raised ValueError: {payload}\n")
        continue
    except Exception as exc:
        fail(f"max_runs({bad!r}) raised {type(exc).__name__}, not ValueError: {exc}")
    else:
        fail(f"expected ValueError for max_runs({bad!r}) but none was raised")

print("PROBE_P1_OK")
