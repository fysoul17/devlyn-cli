# F27 CLI gift card redemption

## Why this fixture exists

F16 showed a valid full-pipeline pair lift when the solo arm implemented the
happy path but missed the exact validation-error contract. F25 was rejected
after an oracle correction made solo pass. F26 was rejected because solo reached
the ceiling.

F27 keeps the useful F16 shape but removes checkout tax complexity: success is
straight integer aggregation, while the risk is the exact failure object after
combining duplicate card redemption rows before balance validation.

## Pair expectation

PLAN must preserve the order of aggregation before validation. IMPLEMENT must
read `data/gift-cards.json` and keep all public amounts in integer cents.
VERIFY should construct an adversarial request where two individually valid
redemptions for the same card become invalid only after combination.

## Isolation

F16 covers quote tax rules. F27 covers non-persistent balance redemption and
exact validation shape after duplicate aggregation.
