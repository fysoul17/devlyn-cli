#!/usr/bin/env bash
# F37 setup — seed a small, deliberately unsorted rule-revisions file.
set -e

mkdir -p data

cat > data/rule-revisions.json <<'JSON'
[
  { "id": "rev-202", "categoryId": "cat-2", "effectiveAt": 2500, "discountPct": 25, "minPrice": 45 },
  { "id": "rev-101", "categoryId": "cat-1", "effectiveAt": 1000, "discountPct": 10, "minPrice": 50 },
  { "id": "rev-301", "categoryId": "cat-3", "effectiveAt": 500, "discountPct": 0, "minPrice": 100 },
  { "id": "rev-103", "categoryId": "cat-1", "effectiveAt": 3000, "discountPct": 15, "minPrice": 55 },
  { "id": "rev-201", "categoryId": "cat-2", "effectiveAt": 1500, "discountPct": 5, "minPrice": 40 },
  { "id": "rev-102", "categoryId": "cat-1", "effectiveAt": 2000, "discountPct": 20, "minPrice": 60 }
]
JSON

exit 0
