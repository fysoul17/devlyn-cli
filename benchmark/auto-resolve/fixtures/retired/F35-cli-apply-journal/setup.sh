#!/usr/bin/env bash
# F35 setup — seed inventory and the replay journal.
set -e

mkdir -p data

cat > data/inventory.json <<'JSON'
{
  "widget": 10,
  "gadget": 4,
  "gizmo": 0
}
JSON

cat > data/journal.json <<'JSON'
{
  "applied": ["op-900"]
}
JSON

exit 0
