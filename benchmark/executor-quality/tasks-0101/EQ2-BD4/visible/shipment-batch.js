/** Route one shipment batch through the dependent tracking journal. */
export function runShipmentBatch(manifest, journal, batch) {
  return journal.applyBatch(manifest, batch.id, batch.legs);
}
