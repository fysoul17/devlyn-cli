"""Money helpers.

Every amount in Ledgerloom is an integer number of cents. Nothing in billing is
allowed to carry money as a float: cents are exact, floats are not.
"""


def round_half_up(numerator, denominator):
    """Divide two ints, rounding to the nearest whole unit, ties away from zero.

    Integer arithmetic only — no float ever appears:

        round_half_up(5, 2)   == 3      # 2.5 -> 3, the tie rounds up
        round_half_up(125, 2) == 63     # 62.5 -> 63
        round_half_up(1, 3)   == 0

    Negative numerators round away from zero as well: round_half_up(-5, 2) == -3.
    """
    if not isinstance(numerator, int) or not isinstance(denominator, int):
        raise TypeError("round_half_up works on ints only")
    if denominator <= 0:
        raise ValueError("denominator must be positive")

    if numerator >= 0:
        return (2 * numerator + denominator) // (2 * denominator)
    return -((2 * -numerator + denominator) // (2 * denominator))


def format_cents(amount_cents):
    """Render integer cents for a human: 1234 -> '$12.34'."""
    if not isinstance(amount_cents, int):
        raise TypeError("amount_cents must be an int number of cents")
    sign = "-" if amount_cents < 0 else ""
    whole, cents = divmod(abs(amount_cents), 100)
    return "%s$%d.%02d" % (sign, whole, cents)
