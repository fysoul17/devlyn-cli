"use strict";

function ingredientTotals(day) {
  return day.ingredients.map((item) => ({ name: item.name, available: item.available, committed: item.committed }));
}

module.exports = { ingredientTotals };
