"use strict";

function makeWarehouse(input) {
  const defaultLot = {
    id: input.lotId, classCode: input.classCode, units: input.units, status: "pending", shipState: "open",
  };
  return {
    lots: (input.lots || [defaultLot]).map((lot) => ({ status: "pending", shipState: "open", ...lot })),
    receipts: [],
    trays: [],
    trayReleases: [],
    distributions: (input.distributions || []).map((item) => ({ lotId: input.lotId, ...item })),
    recalls: [],
    classLimits: (input.classLimits || [{ classCode: input.classCode, limit: 5, used: 0 }]).map((item) => ({ ...item })),
  };
}

module.exports = { makeWarehouse };
