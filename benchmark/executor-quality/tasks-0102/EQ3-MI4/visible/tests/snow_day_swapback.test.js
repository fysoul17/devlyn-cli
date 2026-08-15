const assert = require("node:assert/strict");
const { sessionForWeatherService, oakEdit } = require("./test_helpers");
const { submitStopEdit, swapBack } = require("../editor/stop_editor");

const session = sessionForWeatherService();
const regularBefore = JSON.stringify(session.regularPlan);
submitStopEdit(session, oakEdit());
submitStopEdit(session, { id: "entry-18", leg: "north", stop: { id: "pine" }, passengers: 2 });
const receipt = swapBack(session);
assert.deepEqual(receipt.applied, ["entry-17", "entry-18"]);
assert.equal(session.currentPlan.legs[0].stops.filter((stop) => stop.id === "oak").length, 1);
assert.equal(session.currentPlan.legs[0].stops.filter((stop) => stop.id === "pine").length, 1);
assert.equal(JSON.stringify(session.regularPlan), regularBefore);

// The snow-day swap-back test verifies a replay of queued stops in submission order while preserving the regular plan byte-for-byte.
