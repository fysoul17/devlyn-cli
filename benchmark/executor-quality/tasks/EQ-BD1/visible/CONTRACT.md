# Checkout integration contract

`rates.normalize_quotes` supplies the delivery choices consumed by `checkout.build_checkout`.

Checkout options are presented by earliest delivery estimate, and equal estimates are broken by service code, independent of carrier response order.

Every carrier response contains `service_code`, `eta_days`, and `price_cents`.
