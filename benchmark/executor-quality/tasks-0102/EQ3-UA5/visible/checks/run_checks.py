"""Run the focused enrollment-register checks."""

import pathlib
import sys


ROOT = pathlib.Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))

from cohorts.cohort_randomizer import new_trial, release, reserve
from intake.consent_recorder import new_participant, record_consent, withdraw


trial = new_trial()
participant = new_participant("participant-7")
assert record_consent(participant, "v1", reserve, trial)["accepted"]
assert withdraw(participant, release, trial)
again = record_consent(participant, "v2", reserve, trial)
if not again["accepted"] or participant["current_form"] != "v2" or not participant["active"]:
    raise SystemExit("re-entry form was not recorded")
print("enrollment checks passed")
