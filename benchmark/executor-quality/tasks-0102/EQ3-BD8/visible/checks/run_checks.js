"use strict";

const assert = require("node:assert/strict");
const { makeWarehouse } = require("../support/fixtures");
const { receiveLot } = require("../receiver/lot_receiver");
const { receiptFor } = require("../receiver/receipt_index");

const warehouse = makeWarehouse({ lotId: "LOT-CEDAR", classCode: "heritage", units: 44 });
const first = receiveLot(warehouse, "LOT-CEDAR", 17);
const second = receiveLot(warehouse, "LOT-CEDAR", 17);
assert.equal(first.accepted, true);
assert.equal(first.receiptId, receiptFor(warehouse, "LOT-CEDAR").id);
assert.equal(second.accepted, false);
assert.equal(warehouse.receipts.length, 1);
console.log("receiver checks passed");
