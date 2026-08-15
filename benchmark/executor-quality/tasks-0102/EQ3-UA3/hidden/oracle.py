import json
import pathlib
import sys


root = pathlib.Path(sys.argv[1])


def load(relative):
    namespace = {}
    exec((root / relative).read_text(encoding="utf-8"), namespace)
    return namespace


parser = load("declarations/parser.py")
assessor_module = load("assessment/duty_assessor.py")
submit_declaration = parser["submit_declaration"]
DutyAssessor = assessor_module["DutyAssessor"]
accepted_key = "accepted_lines"
errors_key = "errors"
release_key = "release_requested"


def lines_with_rejection():
    return [
        {"hs_code": "0101", "value": 100},
        {"hs_code": "9999", "value": 50},
        {"hs_code": "0201", "value": 200},
    ]


local_assessor = DutyAssessor()
local_preview = submit_declaration("DEC-41", lines_with_rejection(), local_assessor)

remote_assessor = DutyAssessor()
remote_preview = submit_declaration("DEC-42", lines_with_rejection()[:2], remote_assessor)

restore_assessor = DutyAssessor()
initial = submit_declaration("DEC-43", lines_with_rejection()[:2], restore_assessor)
resubmitted = submit_declaration(
    "DEC-43",
    [{"hs_code": "0101", "value": 100}, {"hs_code": "0201", "value": 200}],
    restore_assessor,
)

values = [
    ("local-a", len(local_preview[accepted_key]) == 2),
    ("local-b", len(local_preview[errors_key]) == 1 and local_preview[accepted_key][-1]["hs_code"] == "0201"),
    ("remote-a", remote_assessor.assessments.get("DEC-42", {}) == {}),
    ("remote-b", remote_preview[release_key] is False),
    ("restore", initial[errors_key] and resubmitted[release_key] and restore_assessor.total("DEC-43") == 29.0),
]
print(json.dumps({"manifestations": [{"id": key, "passed": value} for key, value in values]}))
