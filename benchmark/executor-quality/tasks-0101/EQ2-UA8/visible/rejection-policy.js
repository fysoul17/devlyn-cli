export const REASON_PRIORITY = Object.freeze({
  poll_closed: 0,
  ineligible: 1,
  overvote: 2,
  unknown_choice: 3,
});

export function rankRejections(rejections) {
  return [...rejections].sort(
    (left, right) => left.arrivalIndex - right.arrivalIndex,
  );
}

export function chooseRejection(rejections) {
  return rankRejections(rejections)[0] ?? null;
}
