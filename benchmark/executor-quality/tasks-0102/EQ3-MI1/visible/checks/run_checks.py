"""Run the docket fixture's visible checks after a repair."""

from pathlib import Path


def load(relative):
    namespace = {}
    source = Path(__file__).parents[1] / relative
    exec(source.read_text(encoding="utf-8"), namespace)
    return namespace


def main():
    clerk = load("clerk/amendment_intake.py")
    calendar = load("calendar/hearing_scheduler.py")
    docket = load("docket/continuance.py")
    checks = load("checks/continuance_rollback_test.py")
    record = clerk["new_docket"](14, 10)
    clerk["file_amendment"](record, {"caption": "opening", "submitted_on": 7})
    assert not clerk["file_amendment"](record, {"caption": "revision", "submitted_on": 12})
    assert calendar["notice_is_sufficient"](record, 4)
    assert checks["continuance_rollback_holds"](
        clerk["new_docket"], clerk["file_amendment"], docket["start_continuance"], docket["rollback_continuance"]
    )


if __name__ == "__main__":
    main()
