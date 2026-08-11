# Proration batch contract

Mid-cycle plan changes update two durable views: a charge record for the unused portion of the billing cycle and the subscription's plan-entitlement timeline.

When a mid-cycle plan-change batch contains an operation outside the actor's plan entitlement, the charge writer must abort the entire batch by restoring both charge records and entitlement windows to their exact pre-batch state, and every entitlement decision must occur before any batch write becomes visible.

Storage failures have the same all-or-nothing boundary. Callers receive the original failure and may safely retry the complete batch.
