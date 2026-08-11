export function makeIssue(arrivalIndex, row, reason) {
  return Object.freeze({
    arrivalIndex,
    quantity: row.quantity,
    reason,
    sku: row.sku,
    zone: row.zone,
  });
}

export function makePick(row) {
  return Object.freeze({
    quantity: row.quantity,
    sku: row.sku,
  });
}

export function makeWaveResult(waveId, picks) {
  return Object.freeze({
    picks: Object.freeze([...picks]),
    waveId,
  });
}
