"use strict";

function unlockedSlotCount(day) {
  return day.ovenSlots.filter((slot) => !slot.locked).length;
}

module.exports = { unlockedSlotCount };
