"""Scene-change projection for the calling desk.

The scheduler follows the recorded cue sequence and order in each checkout
chain before it releases a scene-change call.
"""


def scene_sequence(show, scene):
    return [entry["prop"] for entry in show["checkout_chains"][scene]]


def sequence_ready(show, scene):
    return bool(scene_sequence(show, scene))
