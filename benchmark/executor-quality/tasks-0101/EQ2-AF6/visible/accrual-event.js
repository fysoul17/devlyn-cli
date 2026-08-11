export function createAccrualEvent({ eventId, cycleId, points }) {
  if (typeof eventId !== "string" || eventId.length === 0) {
    throw new TypeError("eventId is required");
  }
  if (typeof cycleId !== "string" || cycleId.length === 0) {
    throw new TypeError("cycleId is required");
  }
  if (!Number.isSafeInteger(points) || points <= 0) {
    throw new TypeError("points must be a positive integer");
  }
  return Object.freeze({ eventId, cycleId, points });
}
