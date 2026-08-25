import json
from pathlib import Path

from queue import ordered_open_cases


def next_case_id():
    cases = json.loads(Path("sample_cases.json").read_text(encoding="utf-8"))
    return ordered_open_cases(cases)[0]["id"]
