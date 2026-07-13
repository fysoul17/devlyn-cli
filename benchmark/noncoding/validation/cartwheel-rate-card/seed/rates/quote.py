"""Pricing for a single Cartwheel Freight shipment."""

from rates.registry import FUEL_SURCHARGE_PERCENT, ZONES


def quote_cents(zone, weight_kg):
    """Return the total price, in integer cents, of shipping `weight_kg` to `zone`.

    subtotal  = base_cents + per_kg_cents * weight_kg
    surcharge = subtotal * FUEL_SURCHARGE_PERCENT / 100, half-up rounded to a cent
    total     = subtotal + surcharge
    """
    if zone not in ZONES:
        raise ValueError("unknown zone: %r" % (zone,))
    if weight_kg < 0:
        raise ValueError("weight_kg must not be negative")

    rule = ZONES[zone]
    subtotal = rule["base_cents"] + rule["per_kg_cents"] * weight_kg
    surcharge = (subtotal * FUEL_SURCHARGE_PERCENT + 50) // 100
    return subtotal + surcharge


def zone_labels():
    """Return {zone key: label} for every zone we can price."""
    return {key: rule["label"] for key, rule in ZONES.items()}
