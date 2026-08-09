export function rankNotifications(notifications) {
  return [...notifications].sort(
    (left, right) => right.priority - left.priority || left.sequence - right.sequence,
  );
}
