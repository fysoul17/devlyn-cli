import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ingester.reading_ingester import new_batch, submit_correction


def run():
    batch = new_batch([
        {"meter_id": "M-17", "cumulative": 100, "recorded_at": "08:00"},
        {"meter_id": "M-17", "cumulative": 160, "recorded_at": "12:00"},
    ])
    assert submit_correction(batch, "M-17", 130)
    assert len(batch["readings"]) == 3
    assert batch["readings"][1]["cumulative"] == 160


if __name__ == "__main__":
    run()
    print("checks passed")
