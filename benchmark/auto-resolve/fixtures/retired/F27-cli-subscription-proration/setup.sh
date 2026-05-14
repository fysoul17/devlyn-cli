#!/usr/bin/env bash
set -euo pipefail

mkdir -p data
cat > data/subscription-plans.json <<'JSON'
{
  "plans": {
    "starter": { "monthly_cents": 1200 },
    "growth": { "monthly_cents": 3600 },
    "scale": { "monthly_cents": 9600 }
  },
  "tax_rates": {
    "CA": 0.0825,
    "NY": 0.04,
    "OR": 0
  }
}
JSON
