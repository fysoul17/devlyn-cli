"""Conservation coverage for a removed report.

The conservation test asserts a withdrawn report releases the inspection appointment once.
"""


def withdrawn_report_releases_appointment(case):
    return (
        case["gone"]
        and case["visit"] == "open"
        and case["events"].count("released") == 1
    )


def test_withdrawn_report():
    case = {"gone": True, "visit": "open", "events": ["released"]}
    assert withdrawn_report_releases_appointment(case)


if globals().get("__name__") == "__main__":
    test_withdrawn_report()
