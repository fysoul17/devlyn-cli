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

function capture(action, store) {
  const before = store?.snapshotBytes();
  try {
    const value = action();
    return { error: null, same: store ? store.snapshotBytes().equals(before) : null, value };
  } catch (error) {
    return {
      error: error.name,
      order: error instanceof BatchReject
        ? error.issues.map((issue) => [issue.arrivalIndex, issue.reason, issue.sku])
        : [],
      reason: error.reason ?? null,
      same: store ? store.snapshotBytes().equals(before) : null,
    };
  }
}

let output;
if (scenario === "write") {
  const store = new InventoryStore({ A: 9 });
  output = capture(
    () => executePickWave(store, "w1", [{ failAfterWrite: true, quantity: 4, sku: "A" }]),
    store,
  );
} else if (scenario === "commit") {
  const store = new InventoryStore({ A: 9, B: 6 });
  output = capture(
    () => executePickWave(
      store,
      "w2",
      [{ quantity: 4, sku: "A" }, { quantity: 2, sku: "B" }],
      { failCommit: true },
    ),
    store,
  );
} else if (scenario === "distinct") {
  const reporter = new ShortageReporter();
  reporter.record(makeIssue(0, { sku: "A" }, "shortage"));
  reporter.record(makeIssue(1, { sku: "B" }, "invalid"));
  reporter.record(makeIssue(2, { sku: "C" }, "conflict"));
  output = capture(() => reporter.conclude());
} else if (scenario === "tie") {
  const reporter = new ShortageReporter();
  reporter.record(makeIssue(4, { sku: "A" }, "conflict"));
  reporter.record(makeIssue(3, { sku: "B" }, "invalid"));
  reporter.record(makeIssue(1, { sku: "C" }, "conflict"));
  output = capture(() => reporter.conclude());
} else if (scenario === "combined") {
  const store = new InventoryStore({ A: 9, B: 7, C: 2, D: 1 }, { locked: ["B"] });
  output = capture(
    () => executePickWave(store, "w3", [
      { quantity: 4, sku: "A" },
      { quantity: 2, sku: "B" },
      { quantity: 0, sku: "C" },
      { quantity: 3, sku: "D" },
    ]),
    store,
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
axis2_a = distinct.get("reason") == "invalid" and distinct.get("order") == [
    [1, "invalid", "B"],
    [2, "conflict", "C"],
    [0, "shortage", "A"],
]

tie = invoke("tie")
axis2_b = tie.get("reason") == "invalid" and tie.get("order") == [
    [3, "invalid", "B"],
    [1, "conflict", "C"],
    [4, "conflict", "A"],
]

combined = invoke("combined")
interaction = (
    combined.get("reason") == "invalid"
    and combined.get("order") == [
        [2, "invalid", "C"],
        [1, "conflict", "B"],
        [3, "shortage", "D"],
    ]
    and combined.get("same") is True
)

invariant = "A rejected pick wave leaves the inventory store byte-identical to its pre-wave form, the shortage reporter orders invalid before conflict before shortage with arrival order breaking equal-reason ties, and when accepted picks precede validation and conflict failures the highest-priority error is reported while every earlier inventory change is rolled back."
checks = [axis1_a, axis1_b, axis2_a, axis2_b, interaction]
identifiers = ["axis1-a", "axis1-b", "axis2-a", "axis2-b", "interaction"]
print(json.dumps({"manifestations": [
    {"id": identifier, "invariant": invariant, "passed": passed}
    for identifier, passed in zip(identifiers, checks, strict=True)
]}))
