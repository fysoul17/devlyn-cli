"use strict";

const assert = require("node:assert/strict");
const { createFuelLog } = require("../fuel-log/fuel_log_writer");

const log = createFuelLog();
log.recordDelivery({ id: "receipt-18", liters: 36, odometer: 32100 });
const correction = log.correctFuelEntry("receipt-18");
assert.equal(correction.kind, "reversal");
assert.equal(correction.liters, -36);
