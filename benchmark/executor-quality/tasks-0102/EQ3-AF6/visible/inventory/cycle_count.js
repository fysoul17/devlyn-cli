"use strict";

function committedQuantity(day) {
  return day.ingredients.reduce((total, item) => total + item.committed, 0);
}

module.exports = { committedQuantity };
