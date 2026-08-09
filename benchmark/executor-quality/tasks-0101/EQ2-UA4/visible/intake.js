import { parseLine } from "./line-parser.js";
import { orderPostings } from "./posting-order.js";
import { rankRejects } from "./reject-ranking.js";

/** Coordinate one invoice batch. */
export function intakeBatch(lines) {
  const parsed = lines.map((line, source) => parseLine(line, source));
  const accepted = parsed.filter((entry) => entry.ok).map((entry) => entry.value);
  const rejected = parsed.filter((entry) => !entry.ok).map((entry) => entry.error);
  let postedTotal = 0;

  return {
    posted: accepted.map((invoice) => {
      postedTotal += invoice.amount;
      return { invoice: invoice.id, postedTotal };
    }),
    rejected,
  };
}
