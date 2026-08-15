"use strict";

function recountHoldFreezesInventory(moveSupply, markLocked, state, sourceId, targetId, quantity) {
  const beforeSource = state.counts[sourceId];
  const beforeTarget = state.counts[targetId];
  const beforeEntries = state.transferLedger.length;
  markLocked(state, sourceId);
  const first = moveSupply(state, sourceId, targetId, quantity);
  const afterSourceFirst = state.counts[sourceId] === beforeSource
    && state.counts[targetId] === beforeTarget;
  const second = moveSupply(state, sourceId, targetId, quantity);
  const afterSourceSecond = state.counts[sourceId] === beforeSource
    && state.counts[targetId] === beforeTarget;
  state.lockedPrecincts.delete(sourceId);
  markLocked(state, targetId);
  const third = moveSupply(state, sourceId, targetId, quantity);
  const afterTargetFirst = state.counts[sourceId] === beforeSource
    && state.counts[targetId] === beforeTarget;
  const fourth = moveSupply(state, sourceId, targetId, quantity);
  const afterTargetSecond = state.counts[sourceId] === beforeSource
    && state.counts[targetId] === beforeTarget;
  return !first.moved && !second.moved && !third.moved && !fourth.moved
    && afterSourceFirst && afterSourceSecond && afterTargetFirst && afterTargetSecond
    && state.transferLedger.length === beforeEntries;
}

// The recount hold keeps source and target inventory frozen to preserve both counts and leaves the ledger unchanged after aborted requests.
module.exports = { recountHoldFreezesInventory };
