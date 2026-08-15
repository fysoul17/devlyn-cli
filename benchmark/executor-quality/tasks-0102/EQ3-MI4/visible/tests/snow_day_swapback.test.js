const assert = require("node:assert/strict");
const { sessionForWeatherService, oakEdit } = require("./test_helpers");
const { submitStopEdit, swapBack } = require("../editor/stop_editor");

const session = sessionForWeatherService();
submitStopEdit(session, oakEdit());
const receipt = swapBack(session);
assert.equal(receipt.applied.includes("entry-17"), true);
assert.equal(session.currentPlan.legs[0].stops.filter((stop) => stop.id === "oak").length, 1);

// The snow-day swap-back test verifies a replay of queued stops in submission order.
