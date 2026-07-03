#!/usr/bin/env bash
# F34 setup — seed accounts and the concurrency-tracking gateway.
set -e

mkdir -p data lib

cat > data/accounts.json <<'JSON'
{
  "acct-a": 100,
  "acct-b": 0,
  "acct-c": 50,
  "acct-d": 10
}
JSON

cat > lib/gateway.js <<'JS'
'use strict';
// Seeded authorization gateway. DO NOT MODIFY (fixture contract).
// Latency is deterministic per transfer id (trailing digits = milliseconds),
// so authorization completion order can differ from file order. Tracks how
// many authorizations are in flight at once and how many calls were made.
const fs = require('fs');
const path = require('path');

const STATS_PATH = path.join(__dirname, '..', 'data', 'gateway-stats.json');
let inFlight = 0;
let highWater = 0;
let calls = 0;

function writeStats() {
  fs.writeFileSync(STATS_PATH, JSON.stringify({ calls, high_water: highWater }) + '\n');
}

async function authorize(transfer) {
  calls += 1;
  inFlight += 1;
  if (inFlight > highWater) highWater = inFlight;
  writeStats();
  const digits = String(transfer && transfer.id ? transfer.id : '').replace(/\D/g, '');
  const ms = digits ? (Number(digits) % 100) || 5 : 5;
  await new Promise((resolve) => setTimeout(resolve, ms));
  inFlight -= 1;
  writeStats();
  return { authorized: true };
}

module.exports = { authorize };
JS

exit 0
