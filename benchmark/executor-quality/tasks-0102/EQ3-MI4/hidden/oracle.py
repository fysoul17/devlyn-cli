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
const queueReceipt = editor.swapBack(queueCase);
const remoteB = queueReceipt.applied.length === 1 && queueReceipt.applied[0] === "entry-17";

const restoreCase = fresh();
const original = JSON.stringify(restoreCase.regularPlan);
editor.submitStopEdit(restoreCase, helpers.oakEdit());
const firstReturn = editor.swapBack(restoreCase);
const secondReturn = editor.swapBack(restoreCase);
const returnedStopCount = restoreCase.currentPlan.legs[0].stops.filter((stop) => stop.id === "oak").length;
const restore = firstReturn.baseline === original
  && JSON.stringify(restoreCase.regularPlan) === original
  && firstReturn.applied.length === 1
  && secondReturn.applied.length === 0
  && returnedStopCount === 1;

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
