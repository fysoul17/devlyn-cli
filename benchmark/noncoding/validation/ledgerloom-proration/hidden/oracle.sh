#!/usr/bin/env bash
# Mechanical pass/fail check for the Ledgerloom task.
# Usage: oracle.sh [repo_root]   (defaults to $PWD)
set -u

ROOT="${1:-$PWD}"
cd "$ROOT" || { echo "FAIL: cannot enter repo root: $ROOT" >&2; exit 1; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------- leg 1: suite
python3 - <<'PY' || fail "test discovery collected no tests"
import sys, unittest
suite = unittest.defaultTestLoader.discover("tests")
count = suite.countTestCases()
print("discovered %d test(s)" % count)
sys.exit(0 if count >= 1 else 1)
PY

python3 -m unittest discover -s tests >/dev/null 2>&1 || fail "the test suite does not pass"

# -------------------------------------------- leg 2: proration rules and invoice
python3 - <<'PY' || fail "task outcomes not satisfied (see messages above)"
import hashlib
import pathlib
import sys

errors = []

# The task forbids touching billing/money.py: round_half_up must stay exactly as it is.
MONEY_SHA = "0946a2979e77f2e7a88dbca713f68793d287dd8399b7b198b0a04b9fcdf57a9d"
money_sha = hashlib.sha256(pathlib.Path("billing/money.py").read_bytes()).hexdigest()
if money_sha != MONEY_SHA:
    errors.append("billing/money.py was modified (sha256 %s, expected %s)" % (money_sha, MONEY_SHA))

try:
    from billing.proration import prorate_cents
except Exception as exc:  # noqa: BLE001
    print("  - billing.proration.prorate_cents is not importable: %r" % (exc,), file=sys.stderr)
    sys.exit(1)

# (a) integer cents only: no Decimal anywhere in the module.
source = pathlib.Path("billing/proration.py").read_text(encoding="utf-8")
if "decimal" in source.lower():
    errors.append("billing/proration.py mentions Decimal; money must stay int cents")

# (b) worked examples, (c) half-up ties, (d) clamping
CASES = [
    ((999, 10, 30), 333),
    ((1999, 7, 31), 451),
    ((125, 1, 2), 63),      # 62.5 -> 63, the tie rounds up
    ((101, 1, 2), 51),      # 50.5 -> 51, the tie rounds up
    ((1000, 45, 30), 1000),  # clamped: never more than the full charge
    ((1000, -3, 30), 0),     # clamped: never negative
    ((500, 0, 30), 0),
]
for args, expected in CASES:
    try:
        got = prorate_cents(*args)
    except Exception as exc:  # noqa: BLE001
        errors.append("prorate_cents%r raised %r" % (args, exc))
        continue
    if got != expected:
        errors.append("prorate_cents%r == %r, expected %r" % (args, got, expected))
    elif type(got) is not int:
        errors.append(
            "prorate_cents%r returned a %s (%r); it must be an int number of cents"
            % (args, type(got).__name__, got)
        )

# (e) input validation
try:
    prorate_cents(999, 10, 0)
except ValueError:
    pass
except Exception as exc:  # noqa: BLE001
    errors.append("prorate_cents(999, 10, 0) raised %r, expected ValueError" % (exc,))
else:
    errors.append("prorate_cents(999, 10, 0) did not raise ValueError")

try:
    prorate_cents(9.99, 10, 30)
except TypeError:
    pass
except Exception as exc:  # noqa: BLE001
    errors.append("prorate_cents(9.99, 10, 30) raised %r, expected TypeError" % (exc,))
else:
    errors.append("prorate_cents(9.99, 10, 30) did not raise TypeError")

# the prorated invoice line
from billing.invoice import Invoice

invoice = Invoice("acme")
try:
    invoice.add_prorated_line("Team plan", 1999, 7, 31)
except Exception as exc:  # noqa: BLE001
    errors.append("Invoice.add_prorated_line raised %r" % (exc,))
else:
    if invoice.lines != [("Team plan", 451)]:
        errors.append(
            "after add_prorated_line the lines are %r, expected [('Team plan', 451)]"
            % (invoice.lines,)
        )
    invoice.add_line("Studio plan", 4900)
    total = invoice.total_cents()
    if total != 5351 or type(total) is not int:
        errors.append(
            "invoice total is %r (%s), expected the int 5351"
            % (total, type(total).__name__)
        )

for message in errors:
    print("  - " + message, file=sys.stderr)
sys.exit(1 if errors else 0)
PY

echo "PASS"
