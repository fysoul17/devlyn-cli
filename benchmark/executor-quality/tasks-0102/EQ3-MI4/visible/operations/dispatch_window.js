function serviceWindow(plan) {
  return plan.legs.map((leg) => ({ leg: leg.id, stopCount: leg.stops.length }));
}

module.exports = { serviceWindow };
