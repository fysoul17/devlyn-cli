"use strict";

const assert = require("node:assert/strict");
const { addAssignment, createDispatchState, declineAssignment } = require("../dispatch/courier_assigner");

function runCourierAssignerTest() {
  const state = createDispatchState();
  addAssignment(state, { orderId: "order-17", courierId: "courier-4", rank: 3 });
  declineAssignment(state, "order-17");

  assert.equal(state.assignments.get("order-17").courierId, null);
  assert.deepEqual(state.waitingOrders, [{ orderId: "order-17", rank: 3 }]);
}

module.exports = { runCourierAssignerTest };
