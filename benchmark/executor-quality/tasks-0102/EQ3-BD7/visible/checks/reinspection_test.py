"""Checks used by the reinspection desk before work resumes."""


def resume_after_clear(closure):
    if all(item["state"] == "clear" for item in closure["findings"]):
        closure["status"] = closure["resume_status"]
    return closure["status"]


def staged_statuses(before_status, partial_statuses, final_status, resume_status):
    return partial_statuses == [before_status, before_status] and final_status == resume_status


REINSPECTION_NOTE = (
    "The reinspection sequence keeps each clearance on the field sheet and checks "
    "the status that returns after the final inspection pass."
)
