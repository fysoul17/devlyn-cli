function canonical(value) {
  if (Array.isArray(value)) {
    return value.map(canonical);
  }
  if (value !== null && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, child]) => [key, canonical(child)]),
    );
  }
  return value;
}

export function encodeState(value) {
  return Buffer.from(`${JSON.stringify(canonical(value))}\n`, "utf8");
}

export function decodeState(bytes) {
  const value = JSON.parse(bytes.toString("utf8"));
  if (value === null || Array.isArray(value) || typeof value !== "object") {
    throw new TypeError("inventory state must be an object");
  }
  return value;
}
