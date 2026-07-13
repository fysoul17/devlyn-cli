"""The plans a customer can subscribe to. Prices are integer cents per month."""

PLANS = {
    "starter": {"name": "Starter", "monthly_price_cents": 999},
    "team": {"name": "Team", "monthly_price_cents": 1999},
    "studio": {"name": "Studio", "monthly_price_cents": 4900},
}


def monthly_price_cents(plan_key):
    """Return the monthly price of `plan_key`, in integer cents."""
    if plan_key not in PLANS:
        raise KeyError("unknown plan: %r" % (plan_key,))
    return PLANS[plan_key]["monthly_price_cents"]
