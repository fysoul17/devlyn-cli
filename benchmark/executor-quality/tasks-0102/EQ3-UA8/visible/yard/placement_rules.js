"use strict";

function canPlace(stack) {
  return stack.containers.length < stack.capacity;
}

function placeContainer(stack, containerId) {
  if (!canPlace(stack)) {
    throw new Error("stack-full");
  }
  if (stack.rejectedContainerIds.includes(containerId)) {
    throw new Error("placement-screen-rejected");
  }
  stack.containers.push(containerId);
}

module.exports = { canPlace, placeContainer };
