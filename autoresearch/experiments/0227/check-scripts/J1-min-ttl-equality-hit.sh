#!/bin/sh
# 0227 check (J1): has(key, { minTTL }) returns true with status 'hit' when remaining TTL equals minTTL. Exit 0 = clause holds.
set -eu
cd "$1"
npm run prepare >/dev/null 2>&1
exec node --input-type=module <<'JS'
import assert from 'node:assert/strict'
import { LRUCache } from './dist/esm/node/index.js'

let now = 100
const c = new LRUCache({
  max: 4,
  ttl: 100,
  ttlResolution: 0,
  perf: { now: () => now },
})
c.set('a', 'A')
now = 175
assert.equal(c.getRemainingTTL('a'), 25)
const status = {}
assert.equal(c.has('a', { minTTL: 25, status }), true)
assert.equal(status.has, 'hit')
assert.equal(c.has('a', { minTTL: 25 }), true)
JS
