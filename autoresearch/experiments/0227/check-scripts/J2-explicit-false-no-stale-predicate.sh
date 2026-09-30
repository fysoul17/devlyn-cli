#!/bin/sh
# Clause (spec.md req 1-2): explicit getOptions.allowStale false overrides a true cache default, so expired entries do not reach the predicate (and no stale match is returned).
set -eu
cd "$1"
npm run prepare >/dev/null 2>&1
node --input-type=module <<'EOF'
import { LRUCache } from './dist/esm/node/index.js'
let now = 100
const c = new LRUCache({ max: 5, allowStale: true, ttlResolution: 0, ttlAutopurge: false, perf: { now: () => now } })
c.set('fresh', 'F', { ttl: 100 })
c.set('stale', 'S', { ttl: 10 })
now = 120
const calls = []
const result = c.find((v, k) => { calls.push([k, v]); return true }, { allowStale: false })
console.log(JSON.stringify({ result, calls }))
process.exit(!calls.some(([k]) => k === 'stale') && result !== 'S' ? 0 : 1)
EOF
