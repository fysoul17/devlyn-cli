"use strict";

const assert = require("node:assert/strict");
const { createFuelLog } = require("../fuel-log/fuel_log_writer");

const log = createFuelLog();
log.recordDelivery({ id: "receipt-17", liters: 48, odometer: 32000 });
log.correctFuelEntry("receipt-17");
assert.equal(log.entries.length, 2);
assert.equal(log.entries[0].liters, 48);
