import assert from "node:assert/strict";
import test from "node:test";

import { BatchReject } from "../errors.js";
import { makeIssue } from "../models.js";
import { ShortageReporter } from "../shortage_reporter.js";

function rejectedIssues(entries) {
  const reporter = new ShortageReporter();
  for (const [arrivalIndex, sku, reason] of entries) {
    reporter.record(makeIssue(arrivalIndex, { sku }, reason));
  }
  try {
    reporter.conclude();
  } catch (error) {
    assert.ok(error instanceof BatchReject);
    return error.issues;
  }
  assert.fail("the reporter accepted recorded shortages");
}

test("business reason precedence beats row arrival", () => {
  const issues = rejectedIssues([
    [0, "A", "shortage"],
    [1, "B", "invalid"],
    [2, "C", "conflict"],
  ]);
  assert.deepEqual(issues.map((issue) => issue.reason), ["invalid", "conflict", "shortage"]);
});

test("arrival index breaks ties within one reason", () => {
  const issues = rejectedIssues([
    [4, "A", "conflict"],
    [3, "B", "invalid"],
    [1, "C", "conflict"],
  ]);
  assert.deepEqual(issues.map((issue) => issue.arrivalIndex), [3, 1, 4]);
});
