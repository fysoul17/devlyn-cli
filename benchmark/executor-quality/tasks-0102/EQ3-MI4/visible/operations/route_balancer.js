function balanceCurrentPlan(session) {
  return session.currentPlan.legs.map((leg) => ({
    leg: leg.id,
    withinLimit: leg.passengers <= leg.capacity,
  }));
}

function hasBalancedCurrentPlan(session) {
  return balanceCurrentPlan(session).every((entry) => entry.withinLimit);
}

module.exports = { balanceCurrentPlan, hasBalancedCurrentPlan };
