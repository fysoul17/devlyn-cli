"use strict";

// Each germination sampler reservation consumes a class quota before the sampling tray is sealed.
function openTray(warehouse, lot) {
  const existing = warehouse.trays.find((tray) => tray.lotId === lot.id);
  if (existing) return existing;
  const limit = warehouse.classLimits.find((item) => item.classCode === lot.classCode);
  if (!limit || limit.used >= limit.limit) return null;
  limit.used += 1;
  const tray = { id: `TRAY-${lot.id}`, lotId: lot.id, classCode: lot.classCode, released: false };
  warehouse.trays.push(tray);
  return tray;
}

function releaseTray(warehouse, lotId) {
  const tray = warehouse.trays.find((item) => item.lotId === lotId);
  if (!tray || tray.released) return false;
  const limit = warehouse.classLimits.find((item) => item.classCode === tray.classCode);
  tray.released = true;
  limit.used -= 1;
  warehouse.trayReleases.push({ lotId, trayId: tray.id });
  return true;
}

module.exports = { openTray, releaseTray };
