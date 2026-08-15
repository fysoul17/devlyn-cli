"use strict";

function invalidQuantityIsRejected(createAllocation, moveSupply) {
  const state = createAllocation({ north: 6, south: 4 }, 2);
  const before = { ...state.counts };
  const receipt = moveSupply(state, "north", "south", 7);
  return !receipt.moved
    && state.counts.north === before.north
    && state.counts.south === before.south;
}

module.exports = { invalidQuantityIsRejected };
