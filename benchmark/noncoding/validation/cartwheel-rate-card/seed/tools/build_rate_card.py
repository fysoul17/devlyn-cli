"""Generate the published partner rate card from the zone registry.

    python3 -m tools.build_rate_card

Rewrites data/rate_card.json from the current contents of rates.registry. This is
the only supported way to change the rate card: it is a generated file.
"""

import json
import os

from rates.registry import CURRENCY, FUEL_SURCHARGE_PERCENT, ZONES

OUTPUT_PATH = os.path.join("data", "rate_card.json")


def build_card():
    """Return the rate card document for the current registry."""
    zones = []
    for key in sorted(ZONES):
        rule = ZONES[key]
        zones.append(
            {
                "zone": key,
                "label": rule["label"],
                "base_cents": rule["base_cents"],
                "per_kg_cents": rule["per_kg_cents"],
            }
        )
    return {
        "currency": CURRENCY,
        "fuel_surcharge_percent": FUEL_SURCHARGE_PERCENT,
        "zones": zones,
    }


def main():
    card = build_card()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(card, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print("wrote %s (%d zones)" % (OUTPUT_PATH, len(card["zones"])))


if __name__ == "__main__":
    main()
