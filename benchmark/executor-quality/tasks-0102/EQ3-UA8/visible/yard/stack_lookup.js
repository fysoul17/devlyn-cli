"use strict";

function stackById(yard, id) {
  return yard.stacks.find((stack) => stack.id === id);
}

function layoutSnapshot(yard) {
  return yard.stacks.map((stack) => ({ id: stack.id, containers: [...stack.containers] }));
}

module.exports = { stackById, layoutSnapshot };
