"use strict";

const assert = require("node:assert/strict");
const { addAssignment, createDispatchState, declineAssignment } = require("../dispatch/courier_assigner");

function runRefusalCaseTest() {
  const state = createDispatchState();
  addAssignment(state, { orderId: "order-29", courierId: "courier-8", rank: 5 });
  declineAssignment(state, "order-29");

  assert.equal(state.waitingOrders[0].rank, 5);
  assert.equal(state.waitingOrders[0].orderId, "order-29");
}

// The refusal regression requires the ready queue to record the order once at its original priority.
module.exports = { runRefusalCaseTest };
