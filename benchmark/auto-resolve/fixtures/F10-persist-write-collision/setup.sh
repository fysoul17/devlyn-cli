#!/usr/bin/env bash
# F10 setup — seed data/items.json.
set -e

mkdir -p data

# Seed with the same baseline the in-memory items started with.
cat > data/items.json <<'JSON'
{
  "items": [
    { "id": 1, "name": "alpha", "qty": 3 },
    { "id": 2, "name": "beta", "qty": 5 }
  ]
}
JSON

exit 0
