---
id: "1.2"
title: "Order Cancel Endpoint + UI"
phase: 1
status: planned
priority: medium
complexity: medium
depends-on: []
---

# 1.2 Order Cancel Endpoint + UI

## Context
Customers can place orders but cannot cancel them. Support receives ~8 tickets per day requesting cancellation. This adds self-serve cancellation.

## Customer Frame
When a customer has placed an order and changes their mind before it ships, they want to cancel it themselves so they don't have to contact support.

## Objective
A customer can cancel a pending order from the order detail page.

## Requirements
- [ ] POST /orders/:id/cancel transitions status from pending to cancelled
- [ ] Order detail page shows a Cancel button when status is pending
- [ ] Clicking Cancel shows a confirmation modal with order summary
- [ ] After successful cancel, the page refreshes to show status: cancelled
- [ ] Attempting to cancel a non-pending order returns 409 with UI error banner

## Constraints
- Use existing orders service; do not introduce a new service layer.

## Out of Scope
- Refund processing — handled separately in 2.3.
- Email notifications — backlog item.
- Cancellation reason collection — backlog item.

## Dependencies
- **Internal**: (none)
- **External**: existing orders service

## Verification
- [ ] Test: POST cancel on pending order returns 200 and status=cancelled
- [ ] Test: POST cancel on shipped order returns 409
- [ ] Manual: clicking Cancel on order detail page opens modal and on confirm refreshes with cancelled status
