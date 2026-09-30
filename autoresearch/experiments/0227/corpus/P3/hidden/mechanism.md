# P3 mechanism record

- Family: failure-state preservation.
- Mandatory clause: “If annotation evaluation raises during a forced resolution, propagate that exception without changing field types or the class's resolution-cache state; a previously cached class must still be a cache hit on a subsequent unforced call.”
- Trigger: a class already has successfully resolved field types, and a forced refresh encounters an unresolved annotation name.
- Causal code path: the new force path in `resolve_types` eagerly assigns `None` to `__attrs_types_resolved__` before `typing.get_type_hints`. When hint evaluation raises, the final success-marker assignment is never reached and the earlier marker is lost.
- Incorrect behavior: metadata still holds the prior usable types, but the cache no longer recognizes them. A subsequent ordinary call performs failing annotation evaluation again instead of returning the cached class.
- Executable witness: P3-O4 in `oracle.md`.
- Near-miss exclusions: ignoring `force` entirely, failing to forward `include_extras`, partially updating field types, mistaking a base's marker for a child's, and swallowing a resolution exception are different defects. The target is loss of the previous resolution marker after eager invalidation and failed recomputation.
