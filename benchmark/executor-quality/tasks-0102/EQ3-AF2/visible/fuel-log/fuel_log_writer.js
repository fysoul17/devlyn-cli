"use strict";

function createFuelLog() {
  const entries = [];

  return {
    entries,
    recordDelivery(delivery) {
      const entry = { kind: "delivery", ...delivery };
      entries.push(entry);
      return entry;
    },
    correctFuelEntry(deliveryId) {
      const delivery = entries.find((entry) => entry.kind === "delivery" && entry.id === deliveryId);
      if (!delivery) {
        throw new Error("Unknown delivery");
      }
      delivery.liters = 0;
      return delivery;
    },
    recordService(service) {
      const entry = { kind: "service", ...service };
      entries.push(entry);
      return entry;
    },
  };
}

module.exports = { createFuelLog };
