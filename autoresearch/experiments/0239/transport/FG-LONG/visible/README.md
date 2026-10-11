# Explicit native foreground transport fixture

The caller supplies the precise child launch and command sequence. This is a
transport smoke, not spontaneous instruction compliance or product efficacy.

`scenario.json` lists the ordered parts and their wait durations. Each invocation
of `child_gate.py PART` only reads that scenario, prints a start JSON, waits, and
prints one terminal `gate-completed` JSON; it writes no files. Run each specified
part once, as a separate sequential native Bash call. Do not combine the parts
in one shell call, run them in parallel, shorten the waits or replace the gate.

The child returns the exact terminal JSON objects as `{"parts": [...]}` in order.
The owner saves that object to `receipt.json` only after receiving the child's
terminal result, then runs `python3 -B check_receipt.py` and commits locally.
Only `receipt.json` may change; supplied files must remain byte-identical.

The checker validates the payload only. Actual native timestamps, foreground
flags, child completion, owner receipt/commit/final ordering, identity and whole
usage must be inspected separately. A passing receipt alone proves no waiting.
