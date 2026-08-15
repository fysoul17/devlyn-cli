"use strict";

function createDispatchState() {
  return {
    assignments: new Map(),
    waitingOrders: [],
    repooledOrderIds: new Set(),
  };
}

function addAssignment(state, { orderId, courierId, rank }) {
  if (state.assignments.has(orderId)) {
    throw new Error(`order ${orderId} already has an assignment`);
  }
  const assignment = { orderId, courierId, rank, status: "assigned" };
  state.assignments.set(orderId, assignment);
  return assignment;
}

function assignCourier(state, orderId, courierId) {
  const assignment = state.assignments.get(orderId);
  if (!assignment) {
    throw new Error(`unknown order ${orderId}`);
  }
  assignment.courierId = courierId;
  assignment.status = "assigned";
  return assignment;
}

function declineAssignment(state, orderId) {
  const assignment = state.assignments.get(orderId);
  if (!assignment) {
    throw new Error(`unknown order ${orderId}`);
  }
  assignment.status = "declined";
  return { orderId: assignment.orderId, rank: assignment.rank };
}

module.exports = {
  addAssignment,
  assignCourier,
  createDispatchState,
  declineAssignment,
};
