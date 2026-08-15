import pathlib


def load(relative):
    namespace = {}
    root = pathlib.Path(__file__).resolve().parents[1]
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


desk = load("desk/loan_out.py")
loan = desk["new_loan"](True, False, "west-14")
assert desk["dispatch"](loan)
assert desk["close_transfer"](loan)
assert loan["state"] == "closed"
