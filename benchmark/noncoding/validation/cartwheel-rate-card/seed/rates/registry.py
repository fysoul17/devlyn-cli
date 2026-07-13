"""Source of truth for Cartwheel Freight zones and rate rules.

Every price we quote and every rate card we publish is derived from the values in
this module. Nothing here is read from disk at runtime.
"""

CURRENCY = "USD"

# Per zone:
#   label        human-readable name used on the published rate card
#   base_cents   flat handling charge for any shipment into the zone
#   per_kg_cents linear charge per whole kilogram of billable weight
ZONES = {
    "ZONE_A": {"label": "Metro", "base_cents": 450, "per_kg_cents": 120},
    "ZONE_B": {"label": "Regional", "base_cents": 650, "per_kg_cents": 180},
    "ZONE_C": {"label": "National", "base_cents": 900, "per_kg_cents": 240},
}

# Applied to the base + weight subtotal of every quote, half-up rounded to cents.
FUEL_SURCHARGE_PERCENT = 6
