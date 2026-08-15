"use strict";

function basicTransferWorks(createAllocation, moveSupply) {
  const state = createAllocation({ north: 9, south: 3 }, 4);
  const beforeNorth = state.counts.north;
  const beforeSouth = state.counts.south;
  const quantity = 2;
  const receipt = moveSupply(state, "north", "south", quantity);
  return receipt.moved
    && state.counts.north === beforeNorth - quantity
    && state.counts.south === beforeSouth + quantity;
}

module.exports = { basicTransferWorks };
