import assert from "node:assert/strict";
import test from "node:test";

import { runShipmentBatch } from "../shipment-batch.js";
import { ShipmentState } from "../shipment-state.js";
import { TrackingJournal } from "../tracking-journal.js";

test("routes a batch through tracking", () => {
  const manifest = new ShipmentState({ p1: { location: "dock", state: "ready", hops: 0 } });
  const journal = new TrackingJournal();
  const result = runShipmentBatch(manifest, journal, {
    id: "batch-1",
    legs: [{
      eventId: "scan-1",
      parcelId: "p1",
      to: "hub",
      state: "in_transit",
      failAfterMove: false,
    }],
  });
  assert.deepEqual(result.applied, ["scan-1"]);
  assert.equal(journal.view().entries[0].to, "hub");
});
