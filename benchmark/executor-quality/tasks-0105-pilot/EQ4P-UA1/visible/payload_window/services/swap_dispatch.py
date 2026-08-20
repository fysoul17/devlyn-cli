"""Record payload-window handoffs and expose their downstream checks."""

from launch.operations.test_weather_hold import hold_case
from range_safety.trajectory.reservation_consumer import prior_slot_is_retained


def record_swap(launch, previous):
    launch["events"].append(("swap", previous))


def contract_checks(launch, original):
    return (
        prior_slot_is_retained(launch, original),
        hold_case(launch),
    )
