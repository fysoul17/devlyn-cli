import json
from pathlib import Path

from records import approved_total


def render_sample_report():
    records = json.loads(Path("sample_records.json").read_text(encoding="utf-8"))
    return f"Approved dispatch amount: {approved_total(records)}"
