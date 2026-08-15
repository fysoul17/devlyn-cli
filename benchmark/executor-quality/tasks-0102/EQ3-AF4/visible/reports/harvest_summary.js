"use strict";

function summarizeLots(lots) {
  return Object.values(lots).filter((lot) => !lot.rejected).length;
}

module.exports = { summarizeLots };
