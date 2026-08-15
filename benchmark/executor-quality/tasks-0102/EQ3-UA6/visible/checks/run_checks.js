"use strict";

const { makePortState } = require("../support/fixtures");
const { correctionFor } = require("../porting/request_builder");
const { resubmitPortIn } = require("../porting/port_in_intake");
const { notifyCarrier } = require("../carrier/carrier_notifier");
const { correctionShown } = require("./port_in_intake_test");

const state = makePortState();
const correction = correctionFor("SUB-91", "PR-41", "NorthLink");
const result = resubmitPortIn(state, correction, notifyCarrier);
if (!correctionShown(result, state, correction)) {
  throw new Error("port-in correction is not shown at the desk");
}
console.log("port-in checks passed");
