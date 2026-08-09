/** Apply one physical shipment leg and return its tracking receipt. */
export function applyLeg(manifest, leg) {
  const before = manifest.read(leg.parcelId);
  manifest.advance(leg.parcelId, leg.to, leg.state);

  if (leg.failAfterMove) {
    throw new Error(`leg failed after move: ${leg.eventId}`);
  }

  return {
    eventId: leg.eventId,
    parcelId: leg.parcelId,
    from: before.location,
    fromState: before.state,
  };
}
