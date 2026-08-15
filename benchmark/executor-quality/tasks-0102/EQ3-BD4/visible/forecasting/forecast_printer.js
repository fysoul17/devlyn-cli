"use strict";

function renderForecast(totals) {
  return Object.keys(totals).sort().map((kind) => `${kind}:${totals[kind]}`).join(",");
}

module.exports = { renderForecast };
