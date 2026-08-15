"use strict";

function makePortState() {
  return {
    clock: 52,
    requests: [{
      id: "PR-41",
      number: "+15550000041",
      subscriberId: "sub-7",
      desiredCarrier: "NorthLink",
      status: "cancelled",
      rollbackUntil: 60,
      originalMapping: { subscriptionId: "sub-7", carrier: "MetroWave", route: "prior-route" },
    }, {
      id: "PR-58",
      number: "+15550000058",
      subscriberId: "sub-8",
      desiredCarrier: "SkyBridge",
      status: "cancelled",
      rollbackUntil: 60,
      originalMapping: { subscriptionId: "sub-8", carrier: "HarborTel", route: "archive-route" },
    }],
    numberMap: {
      "+15550000041": { subscriptionId: "pending-77", carrier: "TransitTel", route: "temporary-route" },
      "+15550000058": { subscriptionId: "pending-88", carrier: "Switchline", route: "staging-route" },
    },
    notifications: [
      { portRequestId: "PR-41", carrier: "NorthLink" },
      { portRequestId: "PR-58", carrier: "SkyBridge" },
    ],
    subscribers: [{ id: "sub-7", name: "Taylor Reed" }],
  };
}

module.exports = { makePortState };
