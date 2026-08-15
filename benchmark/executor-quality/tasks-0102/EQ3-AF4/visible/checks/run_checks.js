"use strict";

const { pickedBinsAreReadyForReceiving } = require("./pick_recorder_test");
const { rejectedLotScenario } = require("./rejected_lot_test");

pickedBinsAreReadyForReceiving();
rejectedLotScenario();
console.log("harvest checks passed");
