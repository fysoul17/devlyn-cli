"use strict";

const { checkReleasedSlots } = require("./capacity_release_test");
const { checkRepeatedRemoval } = require("./repeated_removal_test");

checkReleasedSlots();
checkRepeatedRemoval();
console.log("assignment checks passed");
