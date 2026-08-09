import assert from "node:assert/strict";
import test from "node:test";

import { applyLeg } from "../leg-applier.js";
import { ShipmentState } from "../shipment-state.js";

test("returns tracking fields for a successful leg", () => {
  const shipment = new ShipmentState({ p1: { location: "dock", state: "ready", hops: 0 } });
  const receipt = applyLeg(shipment, {
    eventId: "scan-1",
    parcelId: "p1",
    to: "hub",
    state: "in_transit",
    failAfterMove: false,
  });
  assert.deepEqual(
    { eventId: receipt.eventId, from: receipt.from, fromState: receipt.fromState },
    { eventId: "scan-1", from: "dock", fromState: "ready" },
  );
});
