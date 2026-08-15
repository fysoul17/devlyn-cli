"use strict";

function totalByKind(loads) {
  return loads.reduce((totals, load) => {
    totals[load.kind] = (totals[load.kind] || 0) + load.units;
    return totals;
  }, {});
}

module.exports = { totalByKind };
