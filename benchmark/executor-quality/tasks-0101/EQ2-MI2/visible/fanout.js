export function createDelivery(notification, recipient) {
  return {
    id: notification.id,
    recipient,
    priority: notification.priority,
    body: notification.body,
  };
}
