"use strict";

// The oven scheduler preserves thermal changeover between pastry families before it selects the next unlocked slot.
// The resulting thermal sequence keeps same-group trays ahead of a premature switch.
function nextOvenBatch(day, candidates, minute) {
  const slot = day.ovenSlots.find((entry) => !entry.locked);
  if (!slot) {
    return null;
  }
  return candidates.find((candidate) => {
    if (candidate.readyAt > minute) {
      return false;
    }
    if (candidate.group === slot.lastGroup) {
      return true;
    }
    return minute - slot.lastFinishedAt >= slot.changeoverMinutes;
  }) || null;
}

function thermalSequence(day, candidates, minute) {
  const selected = nextOvenBatch(day, candidates, minute);
  return selected ? selected.id : null;
}

module.exports = { nextOvenBatch, thermalSequence };
