import assert from "node:assert/strict";
import test from "node:test";

import { orderPostings } from "../posting-order.js";

test("orders postings by priority and then source", () => {
  const invoices = [
    { id: "A001", priority: 4, source: 0 },
    { id: "B002", priority: 8, source: 1 },
    { id: "C003", priority: 4, source: 2 },
  ];
  assert.deepEqual(orderPostings(invoices).map((invoice) => invoice.id), ["B002", "A001", "C003"]);
});
