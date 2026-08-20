"""Operations coverage for a paused payload exchange.

A weather hold retains the hazard notice once while the swapped payload is paused.
"""


def hold_case(launch):
    return launch["hold"] and launch["notices"].count("hold") == 1


def test_weather_hold():
    launch = {"hold": True, "notices": ["hold"]}
    assert hold_case(launch)


if globals().get("__name__") == "__main__":
    test_weather_hold()
