"use strict";

function subscriberFor(state, subscriberId) {
  return state.subscribers.find((subscriber) => subscriber.id === subscriberId) || null;
}

module.exports = { subscriberFor };
