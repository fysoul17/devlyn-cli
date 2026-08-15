import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from intake.refill_intake import new_refill_state, submit_refill


def run():
    state = new_refill_state(["lisinopril"], 10)
    first = submit_refill(state, "RX-101", "naproxen", 3)
    again = submit_refill(state, "RX-101", "naproxen", 3)
    assert first["accepted"] is True
    assert again["duplicate"] is True
    assert state["units_left"] == 7
    assert len(state["debits"]) == 1


if __name__ == "__main__":
    run()
    print("checks passed")
