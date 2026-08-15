"use strict";

const assert = require("node:assert/strict");
const { makeWarehouse } = require("../support/fixtures");
const { receiveLot } = require("../receiver/lot_receiver");

const warehouse = makeWarehouse({ lotId: "LOT-ASH", classCode: "dwarf", units: 31 });
assert.equal(receiveLot(warehouse, "LOT-ASH", 8).accepted, true);
assert.equal(receiveLot(warehouse, "LOT-ASH", 8).accepted, false);
assert.equal(warehouse.receipts[0].receivedAt, 8);
