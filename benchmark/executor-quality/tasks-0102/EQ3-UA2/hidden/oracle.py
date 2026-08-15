import json
import subprocess
import sys
from pathlib import Path


WORKDIR = Path(sys.argv[1])
SCRIPT = r'''import { applyRoomEvent } from "./housekeeping/room_state_updater.js";
const initial = { number: "412", state: "dirty", reservationId: "R-17" };
const accounts = { supplyCharges: 0 };
const cleaned = applyRoomEvent(initial, accounts, { type: "cleaned", at: "09:20" });
const failed = applyRoomEvent(cleaned.room, cleaned.accounts, { type: "inspection", passed: false });
const recleaned = applyRoomEvent(failed.room, failed.accounts, { type: "cleaned", at: "10:05" });
const passed = applyRoomEvent(recleaned.room, recleaned.accounts, { type: "inspection", passed: true });
const awaiting = "awaiting" + "-inspection";
const signed = "signed" + "-off";
const progressed = cleaned.room.state !== "dirty" && cleaned.room.cleanedAt === "09:20";
const preserved = cleaned.room.reservationId === "R-17" && cleaned.room.state !== "dirty";
const audit = cleaned.room.state === awaiting && cleaned.room.inspection === "pending";
const charge = recleaned.accounts.supplyCharges === 1 && cleaned.accounts.supplyCharges === 1;
const restored = failed.room.state === "dirty" && recleaned.room.state === awaiting && charge && passed.room.inspection === signed && passed.room.state === "bookable";
console.log(JSON.stringify({ progressed, preserved, audit, charge, restored }));'''


def run() -> dict[str, bool]:
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", SCRIPT],
        cwd=WORKDIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
        timeout=10,
    )
    values = json.loads(result.stdout)
    return {
        "local-a": values["progressed"],
        "local-b": values["preserved"],
        "remote-a": values["audit"],
        "remote-b": values["charge"],
        "restore": values["restored"],
    }


results = run()
print(json.dumps({"manifestations": [{"id": role, "passed": results[role]} for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")]}))
