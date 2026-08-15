export function arrivalSummary(arrivals) {
  return arrivals.map((arrival) => `${arrival.guest}: ${arrival.room}`).join("\n");
}
