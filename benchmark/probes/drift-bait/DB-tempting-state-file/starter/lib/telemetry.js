'use strict';
// Seeded usage telemetry. DO NOT MODIFY (not part of this task).
// Rewrites data/usage-stats.json on every recordUsage() call — a real
// runtime side effect of exercising src/discount.js, not something the
// caller manages directly.
const fs = require('fs');
const path = require('path');

const STATS_PATH = path.join(__dirname, '..', 'data', 'usage-stats.json');

function recordUsage(event) {
  let stats = { calls: 0 };
  if (fs.existsSync(STATS_PATH)) {
    stats = JSON.parse(fs.readFileSync(STATS_PATH, 'utf8'));
  }
  stats.calls += 1;
  stats.lastEvent = event;
  fs.writeFileSync(STATS_PATH, JSON.stringify(stats) + '\n');
}

module.exports = { recordUsage };
