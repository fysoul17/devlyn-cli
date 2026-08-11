import assert from "node:assert/strict";
import test from "node:test";

import { InventoryStore } from "../inventory_store.js";
import { makeIssue } from "../models.js";
import { ShortageReporter } from "../shortage_reporter.js";

function rankedIssues(entries) {
  const reporter = new ShortageReporter();
  const issues = entries.map(([arrivalIndex, sku, reason]) => (
    makeIssue(arrivalIndex, { quantity: 1, sku, zone: "receiving" }, reason)
  ));
  return reporter.rank(issues);
}

test("business reason precedence beats row arrival", () => {
  const issues = rankedIssues([
    [0, "A", "shortage"],
    [1, "B", "invalid"],
    [2, "C", "conflict"],
  ]);
  assert.deepEqual(issues.map((issue) => issue.reason), ["invalid", "conflict", "shortage"]);
});

test("arrival index breaks ties within one reason", () => {
  const issues = rankedIssues([
    [4, "A", "conflict"],
    [3, "B", "invalid"],
    [1, "C", "conflict"],
  ]);
  assert.deepEqual(issues.map((issue) => issue.arrivalIndex), [3, 1, 4]);
});

test("rejected waves accumulate shortages by zone", () => {
  const reporter = new ShortageReporter();
  const store = new InventoryStore({ A: 2, B: 1 });
  reporter.recordRejectedWave("wave-a", [
    makeIssue(0, { quantity: 5, sku: "A", zone: "north" }, "shortage"),
  ], store);
  reporter.recordRejectedWave("wave-b", [
    makeIssue(0, { quantity: 3, sku: "B", zone: "north" }, "shortage"),
  ], store);

  assert.deepEqual(reporter.snapshot(), {
    byZone: { north: 5 },
    waves: ["wave-a", "wave-b"],
  });
});
