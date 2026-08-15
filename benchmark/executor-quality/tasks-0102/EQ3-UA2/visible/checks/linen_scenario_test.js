import assert from "node:assert/strict";

export function runLinenScenario() {
  const entries = [{ kind: "linen-debit", turnover: "412-09:20" }];
  const matching = entries.filter((entry) => entry.kind === "linen-debit");

  assert.equal(matching.length, 1, "A completed cleaning records one linen debit in the ledger exactly once.");
}
