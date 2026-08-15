"use strict";

const assert = require("node:assert/strict");
const { makeGreenhouse } = require("../support/fixtures");
const { updateSetpoint } = require("../editor/setpoint_editor");

const greenhouse = makeGreenhouse({ sensorState: "ready" });
const zone = greenhouse.zones[0];
const requested = greenhouse.profiles[1];
const result = updateSetpoint(greenhouse, zone.id, requested.id);

assert.equal(result.updated, true);
assert.deepEqual(greenhouse.editReceipts, [{ zoneId: zone.id, profileId: requested.id }]);
