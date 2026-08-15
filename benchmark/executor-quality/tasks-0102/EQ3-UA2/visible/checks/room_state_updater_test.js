import assert from "node:assert/strict";
import { applyRoomEvent } from "../housekeeping/room_state_updater.js";

export function runRoomStateChecks() {
  const room = { number: "412", state: "dirty", reservationId: "R-17" };
  const result = applyRoomEvent(room, { supplyCharges: 0 }, { type: "cleaned", at: "09:20" });

  assert.notEqual(result.room.state, "dirty");
  assert.equal(result.room.cleanedAt, "09:20");
  assert.equal(result.room.reservationId, "R-17");
}
