"use strict";

function pluralize(count, label) {
  return `${count} ${label}${count === 1 ? "" : "s"}`;
}

module.exports = { pluralize };
