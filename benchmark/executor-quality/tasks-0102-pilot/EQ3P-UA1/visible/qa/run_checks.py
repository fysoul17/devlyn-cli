import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from assigner.site_assigner import move_site


if __name__ == "__main__":
    assert move_site({"site": "tent"}, "cabin")["site"] == "cabin"
    print("checks complete")
