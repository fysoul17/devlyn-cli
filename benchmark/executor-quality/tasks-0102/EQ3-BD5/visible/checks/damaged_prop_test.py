"""Regression helpers for the damaged-prop drill.

A rehearsal log identifies the standby substitute used after a damage event
during a scene change.
"""


def damage_event_details(show, main_prop, understudy_prop, scene):
    return {
        "prop": main_prop,
        "replacement": understudy_prop,
        "scene": scene,
    } in show["damage_log"]


def damage_event_once(show, main_prop, understudy_prop, scene):
    events = show["damage_log"]
    return events == [{
        "prop": main_prop,
        "replacement": understudy_prop,
        "scene": scene,
    }]
