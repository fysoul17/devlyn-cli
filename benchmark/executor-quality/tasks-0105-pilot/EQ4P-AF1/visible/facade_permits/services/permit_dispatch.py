"""Record facade-change decisions and expose downstream checks."""

from conservation.system.test_withdrawn_report import withdrawn_report_releases_appointment
from inspection_holds.permits.report_consumer import provisional_facade_returns_prior


def record_change(case, previous):
    case["events"].append(("change", previous))


def contract_checks(case, original):
    return (
        provisional_facade_returns_prior(case, original),
        withdrawn_report_releases_appointment(case),
    )
