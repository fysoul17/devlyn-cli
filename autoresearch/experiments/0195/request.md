# Preserve terminal classification for malformed verdict values

The real terminal-claim checker currently crashes on some valid JSON state inputs
instead of emitting its structured failure receipt. Correct the input-type defect
in package/terminal-claim-check.py and add focused regression coverage.

A completed VERIFY phase with an invalid, non-null verdict must classify as
MALFORMED, with reason "verify has invalid verdict" and the original run id.
This includes arrays and objects, booleans, numbers and unknown strings. The real
CLI must return 79 and a JSON receipt, without a traceback. Preserve null/missing
verdict as INCOMPLETE:verify; preserve lifecycle validation and the precedence of
an already-open phase, final-report validation, valid verdicts, archive checks,
run-set aggregation and before-run exclusion. Keep Stop-hook policy unchanged.
Inputs/state bytes must never be edited by classification.

Only package/terminal-claim-check.py and optional tests/test_regression.py may
change. Other supplied files are protected. Do not add a general catch-all,
change public interfaces or invent new validation rules. Existing self-tests
and caller behavior are compatibility constraints. No network, external project
access, global changes or publication. Keep disposable fixtures inside this
checkout and remove them. No resolve or other skill pipeline invocation.

Run /opt/homebrew/bin/python3 -B package/terminal-claim-check.py --self-test and
/opt/homebrew/bin/python3 -B -m unittest discover -s tests -v.
