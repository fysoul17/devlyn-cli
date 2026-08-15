"""Helpers for the staff-facing damage summary."""


def was_swapped(result):
    return result["swapped"] and result["replacement"] is not None


def scene_matches(result, scene):
    return result["scene"] == scene
