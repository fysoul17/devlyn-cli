"""Small display helpers for the checkout counter."""


def display_count(show):
    return len(show["ledger"])


def display_scene(scene):
    return scene.replace("-", " ").title()
