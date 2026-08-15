"use strict";

function acceptsKind(kind) {
  return ["paper", "glass", "metal"].includes(kind);
}

module.exports = { acceptsKind };
