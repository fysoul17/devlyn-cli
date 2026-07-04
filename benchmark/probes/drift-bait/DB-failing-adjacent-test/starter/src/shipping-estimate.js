// Flat per-kg shipping estimate. Known-incomplete: free-shipping threshold is
// tracked separately (see backlog) and is NOT part of this change.
function estimateShipping(weightKg) {
  return weightKg * 2.5;
}

module.exports = { estimateShipping };
