import json
import pathlib
import subprocess
import sys


root = pathlib.Path(sys.argv[1])
script = r'''
const path = require("node:path");
const root = path.resolve(process.argv[1]);
const editor = require(path.join(root, "editor", "stop_editor.js"));
const routes = require(path.join(root, "operations", "route_balancer.js"));
const helpers = require(path.join(root, "tests", "test_helpers.js"));

function fresh() {
  return helpers.sessionForWeatherService();
}

const first = fresh();
const localReceipt = editor.submitStopEdit(first, helpers.oakEdit());
const localA = localReceipt.accepted === true;
const localB = editor.editorStops(first).some((stop) => stop.id === "oak");

const capacityCase = fresh();
editor.submitStopEdit(capacityCase, helpers.oakEdit());
const remoteA = routes.hasBalancedCurrentPlan(capacityCase);

const queueCase = fresh();
editor.submitStopEdit(queueCase, helpers.oakEdit());
editor.submitStopEdit(queueCase, { id: "entry-18", leg: "north", stop: { id: "pine" }, passengers: 2 });
const queueReceipt = editor.swapBack(queueCase);
const remoteB = JSON.stringify(queueReceipt.applied) === JSON.stringify(["entry-17", "entry-18"])
  && queueCase.currentPlan.legs[0].stops.map((stop) => stop.id).join(",") === "river,oak,pine"
  && routes.hasBalancedCurrentPlan(queueCase);

const restoreCase = fresh();
const original = JSON.stringify(restoreCase.regularPlan);
editor.submitStopEdit(restoreCase, helpers.oakEdit());
editor.submitStopEdit(restoreCase, { id: "entry-18", leg: "north", stop: { id: "pine" }, passengers: 2 });
const firstReturn = editor.swapBack(restoreCase);
const secondReturn = editor.swapBack(restoreCase);
const returnedStopCount = restoreCase.currentPlan.legs[0].stops.filter((stop) => stop.id === "oak").length;
const restore = firstReturn.baseline === original
  && JSON.stringify(restoreCase.regularPlan) === original
  && JSON.stringify(firstReturn.applied) === JSON.stringify(["entry-17", "entry-18"])
  && secondReturn.applied.length === 0
  && returnedStopCount === 1
  && routes.hasBalancedCurrentPlan(restoreCase);

console.log(JSON.stringify([localA, localB, remoteA, remoteB, restore]));
'''
result = subprocess.run(
    ["node", "-e", script, str(root)],
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
values = json.loads(result.stdout)
roles = ["local-a", "local-b", "remote-a", "remote-b", "restore"]
print(json.dumps({"manifestations": [{"id": role, "passed": value} for role, value in zip(roles, values)]}))
