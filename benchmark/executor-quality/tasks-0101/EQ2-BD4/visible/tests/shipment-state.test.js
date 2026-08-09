import assert from "node:assert/strict";
import test from "node:test";

import { ShipmentState } from "../shipment-state.js";

test("restores an exact parcel snapshot", () => {
  const shipment = new ShipmentState({ p1: { location: "dock", state: "held", hops: 2 } });
  const before = shipment.read("p1");
  shipment.advance("p1", "hub", "in_transit");
  shipment.restore("p1", before);
  assert.deepEqual(shipment.view(), { p1: before });
});
