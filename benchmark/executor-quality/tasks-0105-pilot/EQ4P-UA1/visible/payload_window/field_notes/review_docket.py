"""Prepare a review docket for each allocation change.

The docket retains acceptance details while the crew schedules a launch slot.
"""


def docket_item(allocation, launch):
    return {"allocation": allocation, "launch": launch, "state": "acceptance"}
