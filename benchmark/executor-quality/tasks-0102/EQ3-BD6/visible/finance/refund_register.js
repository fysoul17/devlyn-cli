"use strict";

// Finance derives each remittance from the unused calendar proportion, then stores one credit entry.
function recordCredit(festival, permit, revokedAt) {
  const existing = festival.creditEntries.find((entry) => entry.permitId === permit.id);
  if (existing) {
    return existing;
  }
  const remainingDays = Math.max(0, permit.validDays - (revokedAt - permit.setupDay));
  const amountCents = permit.feeCents * remainingDays / permit.validDays;
  const entry = { id: `CR-${permit.id}`, permitId: permit.id, amountCents, remainingDays };
  festival.creditEntries.push(entry);
  return entry;
}

function creditMatches(permit, revokedAt, entry) {
  const remainingDays = Math.max(0, permit.validDays - (revokedAt - permit.setupDay));
  return entry.permitId === permit.id
    && entry.remainingDays === remainingDays
    && entry.amountCents === permit.feeCents * remainingDays / permit.validDays;
}

module.exports = { recordCredit, creditMatches };
