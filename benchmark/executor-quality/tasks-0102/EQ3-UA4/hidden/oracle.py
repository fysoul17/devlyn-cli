#!/usr/bin/env python3
"""Evaluate the payroll fixture without writing to the supplied worktree."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUNNER = r'''
const { importTimesheet } = require("./importer/timesheet_importer");

function ledger() {
  return {
    hourlyRate: 30,
    earningCodes: ["REG", "OT"],
    periods: [
      { id: "august", closed: true, entries: [{ id: "august-base", workerId: "w-7", hours: 8, amount: 240, earningCode: "REG" }] },
      { id: "september", closed: false, entries: [] },
    ],
  };
}

function sheet(code) {
  return { id: "sheet-august-correction", workerId: "w-7", periodId: "august", replaces: "august-base", hours: 10, earningCode: code };
}

const active = ledger();
const before = JSON.stringify(active.periods[0]);
const totalBefore = active.periods.reduce((sum, period) => sum + period.entries.length, 0);
const first = importTimesheet(active, sheet("REG"));
const totalAfter = active.periods.reduce((sum, period) => sum + period.entries.length, 0);
const nextEntries = active.periods[1].entries;
const pairAfterFirst = JSON.stringify(nextEntries);
const repeat = importTimesheet(active, sheet("REG"));
const pairAfterRepeat = JSON.stringify(nextEntries);
const bad = ledger();
const badBefore = JSON.stringify(bad.periods[0]);
const badSheet = sheet("REG");
delete badSheet.replaces;
const badResult = importTimesheet(bad, badSheet);
const sourceKey = "source" + "Timesheet";
const pairIsOnce = repeat.accepted && pairAfterRepeat === pairAfterFirst;
const pairHasSource = nextEntries.every((entry) => entry[sourceKey] === "sheet-august-correction");
const pairHasValues = nextEntries.length === 2 && nextEntries[0].hours === -8 && nextEntries[0].amount === -240
  && nextEntries[1].hours === 10 && nextEntries[1].amount === 300;

console.log(JSON.stringify({
  localA: first.accepted === true,
  localB: totalAfter > totalBefore,
  remoteA: JSON.stringify(active.periods[0]) === before,
  remoteB: pairIsOnce && pairHasSource && pairHasValues && nextEntries[0].kind === "undo" && nextEntries[1].kind === "replacement",
  restore: badResult.accepted === false && JSON.stringify(bad.periods[0]) === badBefore && bad.periods[1].entries.length === 0,
}));
'''


def evaluate(workdir: Path) -> dict[str, bool]:
    result = subprocess.run(
        ["node", "-e", RUNNER],
        cwd=workdir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if result.returncode:
        raise SystemExit(result.stderr or "node runner failed")
    values = json.loads(result.stdout)
    return {
        "local-a": bool(values["localA"]),
        "local-b": bool(values["localB"]),
        "remote-a": bool(values["remoteA"]),
        "remote-b": bool(values["remoteB"]),
        "restore": bool(values["restore"]),
    }


def main() -> None:
    values = evaluate(Path(sys.argv[1]))
    print(json.dumps({"manifestations": [
        {"id": role, "passed": values[role]}
        for role in ("local-a", "local-b", "remote-a", "remote-b", "restore")
    ]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
