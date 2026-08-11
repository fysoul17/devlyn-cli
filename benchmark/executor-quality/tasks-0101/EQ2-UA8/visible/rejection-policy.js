export const REASON_ORDER = Object.freeze([
  "poll_closed",
  "ineligible",
  "overvote",
  "unknown_choice",
]);

export function rankRejections(rejections) {
  return [...rejections];
}

export function chooseRejection(rejections) {
  return rankRejections(rejections)[0] ?? null;
}
