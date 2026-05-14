# F30 - Notes

## Failure Mode

This fixture detects payment-style implementations that pass simple happy-path
tests while double-applying duplicate operations, letting rejected operations
consume available credit, failing to release holds on capture/release, or
mutating input files while computing settlement state.

## Pipeline Phases

It stresses IMPLEMENT and VERIFY. The visible spec names the state transition
rules, idempotency output shape, and exact account summary; hidden verifiers
combine those rules so a one-axis implementation is not enough.

## Why Existing Fixtures Do Not Cover This

F16 covers quote math, F23 covers warehouse allocation rollback, F25 covers cart
promotions, and F28 return authorization was rejected after corrected scoring
showed solo saturation. None focus on duplicate operation idempotency plus
credit-hold mutation, capture/release transitions, and validation immutability.

## Retirement Criteria

Retire or rotate this fixture if both `solo_claude` and the selected pair arm
score near the ceiling for two shipped versions, or if another fixture covers
idempotent financial hold mutation with clearer pair headroom.

## Headroom Status

Retired after headroom run `20260511-f30-headroom-v1`: bare 33 /
solo_claude 98, headroom FAIL because `solo_claude score 98 > 80`.

Do not count F30 as pair-lift evidence. Rework the visible contract or hidden
verifiers before spending pair arms on this idea again.
