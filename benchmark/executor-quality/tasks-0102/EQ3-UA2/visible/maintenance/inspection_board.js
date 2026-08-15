export function openWorkOrders(orders) {
  return orders.filter((order) => order.status !== "closed");
}
