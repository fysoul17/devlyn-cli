"""A compact catalog used by the props crew."""


def category(prop):
    return "timepiece" if prop.startswith("clock") else "hand-prop"
