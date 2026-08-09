export function orderPostings(invoices) {
  return [...invoices].sort(
    (left, right) => right.priority - left.priority || left.source - right.source,
  );
}
