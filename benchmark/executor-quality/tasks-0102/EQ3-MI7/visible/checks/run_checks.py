"""Run focused pass-issuer checks without external dependencies."""

import pathlib


def load(relative):
    namespace = {}
    root = pathlib.Path(__file__).parents[1]
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


issuer = load("issuer/pass_issuer.py")
checks = load("checks/close_pass_test.py")
pass_record = issuer["issue_pass"]("pass-local", 240, 4)
result = issuer["close_pass"](pass_record)
if not checks["closed"](result, pass_record):
    raise SystemExit("pass did not close")
if not checks["full_amount"](result, pass_record):
    raise SystemExit("counter amount changed")
print("pass issuer checks passed")
