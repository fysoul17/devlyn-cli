function copy(value) {
  return JSON.parse(JSON.stringify(value));
}

function createSession(regularPlan, weatherPlan) {
  return {
    mode: "weather",
    regularPlan: copy(regularPlan),
    currentPlan: copy(weatherPlan),
    queuedEdits: [],
    baselinePlan: null,
  };
}

function applyStopEdit(plan, edit) {
  const leg = plan.legs.find((item) => item.id === edit.leg);
  if (!leg || leg.stops.some((stop) => stop.id === edit.stop.id)) {
    return false;
  }
  leg.stops.push(copy(edit.stop));
  leg.passengers += edit.passengers;
  return true;
}

function submitStopEdit(session, edit) {
  return { accepted: false, queued: false };
}

function editorStops(session) {
  const stops = session.currentPlan.legs.flatMap((leg) => leg.stops);
  return stops.concat(session.queuedEdits.map((item) => item.stop));
}

function swapBack(session) {
  const baseline = JSON.stringify(session.regularPlan);
  session.baselinePlan = copy(session.regularPlan);
  session.currentPlan = copy(session.regularPlan);
  session.mode = "regular";
  return { baseline, applied: [] };
}

module.exports = { createSession, submitStopEdit, editorStops, swapBack, applyStopEdit };
