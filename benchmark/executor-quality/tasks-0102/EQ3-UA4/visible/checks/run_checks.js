"use strict";

const { runLateImportCheck } = require("./late_import_test");
const { runRetroAdjustmentCheck } = require("./retro_adjustment_test");

runLateImportCheck();
runRetroAdjustmentCheck();
console.log("payroll checks passed");
