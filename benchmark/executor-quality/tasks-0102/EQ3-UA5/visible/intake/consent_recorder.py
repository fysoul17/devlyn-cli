"""Front-desk consent entry for the enrollment register."""


def new_participant(identifier):
    return {
        "id": identifier,
        "current_form": None,
        "first_form": None,
        "active": False,
        "slot": None,
    }


def record_consent(participant, form_version, reserve, trial):
    if participant["current_form"] is not None:
        return {"accepted": False, "reason": "previous form remains"}
    participant["current_form"] = form_version
    participant["active"] = True
    participant["slot"] = reserve(trial, participant["id"], form_version)
    return {"accepted": True, "form": form_version}


def withdraw(participant, release, trial):
    if not participant["active"]:
        return False
    participant["active"] = False
    return True
