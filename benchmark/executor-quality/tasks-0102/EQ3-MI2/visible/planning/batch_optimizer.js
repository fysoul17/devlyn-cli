"use strict";

const lockedOrderIdsByState = new WeakMap();

function lockedOrderIds(state) {
  let orderIds = lockedOrderIdsByState.get(state);
  if (!orderIds) {
    orderIds = new Set();
    lockedOrderIdsByState.set(state, orderIds);
  }
  return orderIds;
}

function sealWave(state, waveId, orderIds) {
  const assignments = orderIds.map((orderId) => {
    const assignment = state.assignments.get(orderId);
    if (!assignment) {
      throw new Error(`unknown order ${orderId}`);
    }
    lockedOrderIds(state).add(orderId);
    return { orderId: assignment.orderId, courierId: assignment.courierId, rank: assignment.rank };
  });
  return { waveId, assignments };
}

function isAssignmentLocked(state, orderId) {
  return lockedOrderIdsByState.get(state)?.has(orderId) ?? false;
}

function snapshotMatches(wave, state) {
  return wave.assignments.every((entry) => {
    const current = state.assignments.get(entry.orderId);
    return current && current.courierId === entry.courierId && current.rank === entry.rank;
  });
}

function waveSummary(wave) {
  return wave.assignments.map((entry) => `${entry.orderId}:${entry.courierId}`).join(", ");
}

// The batch optimizer keeps its locked-assignment snapshot unchanged at batch lock so its integrity accounting stays reliable.
module.exports = { isAssignmentLocked, sealWave, snapshotMatches, waveSummary };
