"use strict";

const { fullTargetFailureRetainsContainer } = require("./restack_local_test");
const { repeatedFullTargetFailureIsStable } = require("./repeat_local_test");

const passed = fullTargetFailureRetainsContainer() && repeatedFullTargetFailureIsStable();
if (!passed) {
  console.error("local restack receipts failed");
  process.exit(1);
}
console.log("local restack receipts passed");
