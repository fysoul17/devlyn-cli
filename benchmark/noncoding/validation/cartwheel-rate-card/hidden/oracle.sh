#!/usr/bin/env bash
# Mechanical pass/fail check for the Cartwheel Freight task.
# Usage: oracle.sh [repo_root]   (defaults to $PWD)
set -u

ROOT="${1:-$PWD}"
cd "$ROOT" || { echo "FAIL: cannot enter repo root: $ROOT" >&2; exit 1; }

fail() { echo "FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------- leg 1: suite
python3 - <<'PY' || fail "test discovery collected no tests"
import sys, unittest
suite = unittest.defaultTestLoader.discover("tests")
count = suite.countTestCases()
print("discovered %d test(s)" % count)
sys.exit(0 if count >= 1 else 1)
PY

python3 -m unittest discover -s tests >/dev/null 2>&1 || fail "the test suite does not pass"

# ------------------------------------------- leg 2: registry, pricing, card
python3 - <<'PY' || fail "task outcomes not satisfied (see messages above)"
import json
import sys

import rates.registry as registry
from rates.quote import quote_cents
from tools.build_rate_card import build_card

errors = []

zone_d = registry.ZONES.get("ZONE_D")
if zone_d != {"label": "International", "base_cents": 1500, "per_kg_cents": 320}:
    errors.append("registry ZONE_D is %r" % (zone_d,))

if registry.FUEL_SURCHARGE_PERCENT != 9:
    errors.append(
        "registry FUEL_SURCHARGE_PERCENT is %r, expected 9"
        % (registry.FUEL_SURCHARGE_PERCENT,)
    )

for zone, weight, expected in (("ZONE_D", 10, 5123), ("ZONE_A", 2, 752)):
    try:
        got = quote_cents(zone, weight)
    except Exception as exc:  # noqa: BLE001
        errors.append("quote_cents(%r, %r) raised %r" % (zone, weight, exc))
        continue
    if got != expected or type(got) is not int:
        errors.append(
            "quote_cents(%r, %r) is %r (%s), expected int %d"
            % (zone, weight, got, type(got).__name__, expected)
        )

try:
    with open("data/rate_card.json", encoding="utf-8") as handle:
        card = json.load(handle)
except Exception as exc:  # noqa: BLE001
    errors.append("data/rate_card.json is not readable JSON: %s" % (exc,))
    card = None

if card is not None:
    if card.get("fuel_surcharge_percent") != 9:
        errors.append(
            "published rate card fuel_surcharge_percent is %r, expected 9"
            % (card.get("fuel_surcharge_percent"),)
        )

    zones = {entry.get("zone"): entry for entry in card.get("zones", [])}
    if sorted(zones) != ["ZONE_A", "ZONE_B", "ZONE_C", "ZONE_D"]:
        errors.append(
            "published rate card lists zones %r, expected all four zones"
            % (sorted(zones),)
        )

    published_d = zones.get("ZONE_D")
    expected_d = {
        "zone": "ZONE_D",
        "label": "International",
        "base_cents": 1500,
        "per_kg_cents": 320,
    }
    if published_d != expected_d:
        errors.append(
            "published rate card ZONE_D entry is %r, expected %r"
            % (published_d, expected_d)
        )

    # The published card must be exactly what the generator writes for the
    # registry as it now stands: a card generated from a stale registry fails here.
    if card != build_card():
        errors.append(
            "data/rate_card.json does not match the generator's output for the "
            "current registry (stale rate card)"
        )

for message in errors:
    print("  - " + message, file=sys.stderr)
sys.exit(1 if errors else 0)
PY

echo "PASS"
