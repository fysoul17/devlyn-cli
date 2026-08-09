import assert from "node:assert/strict";
import test from "node:test";

import { ShipmentState } from "../shipment-state.js";
import { TrackingJournal } from "../tracking-journal.js";

test("skips a completed batch", () => {
  const manifest = new ShipmentState({ p1: { location: "dock", state: "ready", hops: 0 } });
  const journal = new TrackingJournal();
  const legs = [{
    eventId: "scan-1",
    parcelId: "p1",
    to: "hub",
    state: "in_transit",
    failAfterMove: false,
  }];
  assert.equal(journal.applyBatch(manifest, "batch-1", legs).ok, true);
  assert.equal(journal.applyBatch(manifest, "batch-1", legs).skipped, true);
  assert.equal(journal.view().entries.length, 1);
});
