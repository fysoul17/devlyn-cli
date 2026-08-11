#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import subprocess
import sys


workdir = pathlib.Path(sys.argv[1])
runner = r'''import { pathToFileURL } from "node:url";
const rootUrl = pathToFileURL(`${process.argv[1]}/`);
const { BatchReject } = await import(new URL("errors.js", rootUrl).href);
const { InventoryStore } = await import(new URL("inventory_store.js", rootUrl).href);
const { makeIssue } = await import(new URL("models.js", rootUrl).href);
const { executePickWave } = await import(new URL("pick_executor.js", rootUrl).href);
const { ShortageReporter } = await import(new URL("shortage_reporter.js", rootUrl).href);
const scenario = JSON.parse(process.argv[2]);

function capture(action, store, reporter = null) {
  const before = store?.snapshotBytes();
  try {
    const value = action();
    return {
      error: null,
      reporter: reporter?.snapshot() ?? null,
      same: store ? store.snapshotBytes().equals(before) : null,
      value,
    };
  } catch (error) {
    return {
      error: error.name,
      order: error instanceof BatchReject
        ? error.issues.map((issue) => [issue.arrivalIndex, issue.reason, issue.sku])
        : [],
      reason: error.reason ?? null,
      reporter: reporter?.snapshot() ?? null,
      same: store ? store.snapshotBytes().equals(before) : null,
    };
  }
}

let output;
if (scenario === "write") {
  const store = new InventoryStore({ A: 9 });
  output = capture(
    () => executePickWave(store, "w1", [
      { failAfterWrite: true, quantity: 4, sku: "A", zone: "north" },
    ]),
    store,
  );
} else if (scenario === "commit") {
  const store = new InventoryStore({ A: 9, B: 6 });
  output = capture(
    () => executePickWave(
      store,
      "w2",
      [
        { quantity: 4, sku: "A", zone: "north" },
        { quantity: 2, sku: "B", zone: "south" },
      ],
      { failCommit: true },
    ),
    store,
  );
} else if (scenario === "distinct") {
  const reporter = new ShortageReporter();
  const issues = [
    makeIssue(0, { quantity: 4, sku: "A", zone: "north" }, "shortage"),
    makeIssue(1, { quantity: 0, sku: "B", zone: "east" }, "invalid"),
    makeIssue(2, { quantity: 2, sku: "C", zone: "south" }, "conflict"),
  ];
  output = { order: reporter.rank(issues).map((issue) => [issue.arrivalIndex, issue.reason]) };
} else if (scenario === "tie") {
  const reporter = new ShortageReporter();
  const issues = [
    makeIssue(4, { quantity: 1, sku: "A", zone: "north" }, "conflict"),
    makeIssue(3, { quantity: 0, sku: "B", zone: "east" }, "invalid"),
    makeIssue(1, { quantity: 1, sku: "C", zone: "south" }, "conflict"),
  ];
  output = { order: reporter.rank(issues).map((issue) => [issue.arrivalIndex, issue.reason]) };
} else if (scenario === "combined") {
  const reporter = new ShortageReporter();
  const priorStore = new InventoryStore({ E: 1 });
  reporter.recordRejectedWave("prior", [
    makeIssue(0, { quantity: 4, sku: "E", zone: "east" }, "shortage"),
  ], priorStore);
  const store = new InventoryStore({ A: 10, B: 7, C: 2 }, { locked: ["B"] });
  output = capture(
    () => executePickWave(
      store,
      "w3",
      [
        { quantity: 4, sku: "A", zone: "north" },
        { quantity: 2, sku: "B", zone: "east" },
        { quantity: 0, sku: "C", zone: "east" },
        { quantity: 8, sku: "A", zone: "north" },
      ],
      { reporter },
    ),
    store,
    reporter,
  );
} else {
  throw new Error("unknown scenario");
}
process.stdout.write(JSON.stringify(output));
'''


def invoke(scenario: str) -> dict[str, object]:
    completed = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            runner,
            str(workdir),
            json.dumps(scenario),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    if completed.returncode != 0:
        return {}
    value = json.loads(completed.stdout)
    return value if isinstance(value, dict) else {}


write_fault = invoke("write")
axis1_a = write_fault.get("error") == "WriteFault" and write_fault.get("same") is True

commit_fault = invoke("commit")
axis1_b = commit_fault.get("error") == "CommitFault" and commit_fault.get("same") is True

distinct = invoke("distinct")
axis2_a = distinct.get("order") == [
    [1, "invalid"],
    [2, "conflict"],
    [0, "shortage"],
]

tie = invoke("tie")
axis2_b = tie.get("order") == [
    [3, "invalid"],
    [1, "conflict"],
    [4, "conflict"],
]

combined = invoke("combined")
interaction = (
    combined.get("reason") == "invalid"
    and combined.get("order") == [
        [2, "invalid", "C"],
        [1, "conflict", "B"],
        [3, "shortage", "A"],
    ]
    and combined.get("same") is True
    and combined.get("reporter") == {
        "byZone": {"east": 3},
        "waves": ["prior", "w3"],
    }
)

invariant = "A rejected pick wave leaves the inventory store byte-identical to its pre-wave form, the shortage reporter ranks invalid before conflict before shortage with arrival order breaking equal-reason ties, and when accepted picks precede multiple failures the highest-priority error is reported while the reporter accumulates only zone shortages that remain after rollback."
checks = [axis1_a, axis1_b, axis2_a, axis2_b, interaction]
identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(json.dumps({"manifestations": [
    {"id": identifier, "invariant": invariant, "passed": passed}
    for identifier, passed in zip(identifiers, checks, strict=True)
]}))
