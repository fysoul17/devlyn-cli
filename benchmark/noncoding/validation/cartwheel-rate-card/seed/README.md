# Cartwheel Freight — rates service

Prices a shipment for a destination zone and publishes the partner rate card.

## Layout

- `rates/registry.py` — source of truth: the zone table and the fuel surcharge.
- `rates/quote.py` — `quote_cents(zone, weight_kg)`, prices a shipment in cents.
- `tools/build_rate_card.py` — regenerates `data/rate_card.json` from the registry.
- `data/rate_card.json` — **generated**. Published to partner carriers. Never edit
  it by hand; run the generator instead.

## Common commands

```
python3 -m tools.build_rate_card          # refresh the published rate card
python3 -m unittest discover -s tests     # run the suite
```
