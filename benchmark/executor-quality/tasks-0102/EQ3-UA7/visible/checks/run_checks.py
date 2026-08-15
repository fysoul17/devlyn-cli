"""Run the desk-level ticket checks from the task root."""

import pathlib
import runpy


ROOT = pathlib.Path(__file__).resolve().parents[1]
tagger = runpy.run_path(str(ROOT / "triage" / "severity_tagger.py"))
case = tagger["open_case"]("CLM-218")
reviews = [
    {"id": "field-17", "severity": "elevated", "confidence": 23},
    {"id": "audit-84", "severity": "moderate", "confidence": 91},
]
result = tagger["tag_severity"](case, reviews)
assert result["changed"] and case["severity"] == "moderate" and case["state"] == "closed"
print("desk checks passed")
