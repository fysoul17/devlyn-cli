"use strict";

function readyPairCount(harbor) {
  return harbor.pilots.filter((item) => item.status === "ready").length
    * harbor.berths.filter((item) => item.status === "open").length;
}

module.exports = { readyPairCount };
