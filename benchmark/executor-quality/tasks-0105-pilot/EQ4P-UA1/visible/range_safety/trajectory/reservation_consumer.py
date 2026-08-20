"""Range trajectory consumer for a pending payload exchange.

A trajectory reservation remains active until range acceptance records the
swapped payload. The original allocation is therefore recoverable during a hold.
"""


def prior_slot_is_retained(launch, original):
    return (
        launch["hold"]
        and not launch["range_ok"]
        and launch.get("prior_slot") == original
        and launch["allocation"] == original
        and not launch["slot_open"]
    )
