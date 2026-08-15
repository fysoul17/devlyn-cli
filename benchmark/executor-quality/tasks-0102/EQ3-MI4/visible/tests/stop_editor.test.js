const assert = require("node:assert/strict");
const { sessionForWeatherService, oakEdit } = require("./test_helpers");
const { submitStopEdit, editorStops } = require("../editor/stop_editor");

const session = sessionForWeatherService();
const receipt = submitStopEdit(session, oakEdit());
assert.equal(receipt.accepted, true);
assert.equal(editorStops(session).some((stop) => stop.id === "oak"), true);
