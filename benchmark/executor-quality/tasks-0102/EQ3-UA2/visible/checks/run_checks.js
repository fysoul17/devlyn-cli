import { runRoomStateChecks } from "./room_state_updater_test.js";
import { runLinenScenario } from "./linen_scenario_test.js";

runRoomStateChecks();
runLinenScenario();
console.log("room-state checks passed");
