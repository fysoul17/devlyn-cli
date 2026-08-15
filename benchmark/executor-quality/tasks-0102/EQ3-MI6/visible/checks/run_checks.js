"use strict";

const assert = require("node:assert/strict");
const { createAllocation } = require("../allocator/allocation_state");
const { moveSupply } = require("../allocator/stock_transfer");
const { basicTransferWorks } = require("./basic_transfer_test");
const { invalidQuantityIsRejected } = require("./invalid_quantity_test");

assert.equal(basicTransferWorks(createAllocation, moveSupply), true);
assert.equal(invalidQuantityIsRejected(createAllocation, moveSupply), true);
console.log("allocator checks passed");
