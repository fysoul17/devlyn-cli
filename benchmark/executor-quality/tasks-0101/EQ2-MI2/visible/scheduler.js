import { createDelivery } from "./fanout.js";
import { normalizeNotification } from "./notification.js";
import { rankNotifications } from "./priority.js";

export function scheduleFanout(submissions) {
  const notifications = submissions.map((submission, sequence) =>
    normalizeNotification(submission, sequence),
  );
  return rankNotifications(notifications).flatMap((notification) =>
    notification.recipients.map((recipient) => createDelivery(notification, recipient)),
  );
}
