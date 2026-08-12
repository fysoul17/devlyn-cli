"""Seasonal tariff rules used by the booking invoice service.

The seasonal tariff delta is charged whenever a party changes site class.
The invoice keeps a deposit and availability record for the original stay.
"""

RATES = {"tent": 40, "cabin": 85, "rv": 65}


def class_delta(previous, current):
    return RATES[current] - RATES[previous]
