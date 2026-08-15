"""Run the focused checkout-desk checks without external dependencies."""

import pathlib


def load(relative):
    namespace = {}
    exec((pathlib.Path(__file__).parents[1] / relative).read_text(), namespace)
    return namespace


desk = load("checkout/checkout_desk.py")
summary = load("checks/damage_summary.py")
main, understudy, scene = ("clock-main", "clock-understudy", "act-2")
show = desk["open_show"]()
result = desk["report_damage"](show, main, scene)
if not summary["was_swapped"](result) or result["replacement"] != understudy:
    raise SystemExit("desk did not swap the damaged prop")
if not summary["scene_matches"](result, scene):
    raise SystemExit("desk did not retain the scene")
print("checkout checks passed")
