const precedence = new Map([
  ["format", 0],
  ["account", 1],
  ["amount", 2],
]);

export function rankRejects(rejects) {
  return [...rejects].sort(
    (left, right) =>
      precedence.get(left.reason) - precedence.get(right.reason) || left.source - right.source,
  );
}
