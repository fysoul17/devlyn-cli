import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from assigner.site_assigner import cancel_booking, move_site


if __name__ == "__main__":
    booking = {
        "site": "tent",
        "rates": {"tent": 80, "cabin": 120},
        "availability": {"tent": 2, "cabin": 1},
        "deposit": 80,
        "ledger": [],
        "reversals": 0,
    }
    assert move_site(booking, "cabin")["site"] == "cabin"
    assert booking["deposit"] == 120
    assert booking["availability"] == {"tent": 3, "cabin": 0}
    assert booking["ledger"] == [("move", "tent", "cabin", 40)]
    assert cancel_booking(booking)["cancelled"]
    assert cancel_booking(booking)["cancelled"]
    assert booking["deposit"] == 80
    assert booking["availability"] == {"tent": 2, "cabin": 1}
    assert booking["reversals"] == 1
    print("checks complete")
