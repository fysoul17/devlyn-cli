# Feature flag mutation contract

Authorized flag-change operations sharing an operation key must append one revision and replay that revision across active actor-token rotations, every token must be validated against its current actor and environment grant before the flag's revision chain is inspected or extended, and an expired or out-of-scope token repeating either a fresh or recorded operation must be denied without revealing a prior result or recording an operation marker.

`ActorTokenGateway.mutate_flag(request, token_value)` is the supported mutation path. `apply_flag_mutation` owns the ordering contract used by that gateway: invoke the supplied authorization callback before consulting or extending the append-only chain. An operation key identifies one requested flag revision, independent of which active token for the same actor authorizes it.
