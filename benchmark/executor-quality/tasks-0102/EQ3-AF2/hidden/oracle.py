import json
import subprocess
import sys
from pathlib import Path


def run_case(workdir: Path) -> dict[str, bool]:
    program = r'''
const path = require("node:path");
const root = process.argv[1];
const { createFuelLog } = require(path.join(root, "fuel-log", "fuel_log_writer.js"));
const { auditFuelSeries } = require(path.join(root, "audit", "odometer_auditor.js"));
const { closeServiceVisit } = require(path.join(root, "operations", "service_intake.js"));

function makeLog() {
  const log = createFuelLog();
  log.recordDelivery({ id: "receipt-17", liters: 48, odometer: 32000 });
  return log;
}

const first = makeLog();
const correction = first.correctFuelEntry("receipt-17");
const localA = first.entries.length === 2 && first.entries[0].liters === 48;
const localB = correction.kind === "reversal" && correction.liters === -48;

const audited = makeLog();
audited.correctFuelEntry("receipt-17");
closeServiceVisit(audited, 32100);
const remoteA = auditFuelSeries(audited.entries).variance === 0;

const repeated = makeLog();
repeated.correctFuelEntry("receipt-17");
repeated.correctFuelEntry("receipt-17");
closeServiceVisit(repeated, 32100);
const reversals = repeated.entries.filter((entry) => entry.kind === "reversal");
const remoteB = reversals.length === 1;
const restore = remoteA && remoteB && auditFuelSeries(repeated.entries).variance === 0;

process.stdout.write(JSON.stringify({ localA, localB, remoteA, remoteB, restore }));
'''
    result = subprocess.run(
        ["node", "-e", program, str(workdir)],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr)
    return json.loads(result.stdout)


def main() -> None:
    values = run_case(Path(sys.argv[1]).resolve())
    roles = ("local-a", "local-b", "remote-a", "remote-b", "restore")
    keys = ("localA", "localB", "remoteA", "remoteB", "restore")
    print(json.dumps({"manifestations": [
        {"id": role, "passed": bool(values[key])} for role, key in zip(roles, keys)
    ]}))


if __name__ == "__main__":
    main()
