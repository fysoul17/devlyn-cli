"use strict";

function totalCredits(festival) {
  return festival.creditEntries.reduce((total, entry) => total + entry.amountCents, 0);
}

module.exports = { totalCredits };
