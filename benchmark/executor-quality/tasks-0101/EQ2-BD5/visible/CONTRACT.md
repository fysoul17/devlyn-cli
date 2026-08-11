# Tenant quota debit contract

Quota debits reduce a tenant's remaining capacity and append an immutable journal row. Tenant authorization is supplied by the scope-check component as a guarded operation stream consumed by the debit writer.

When a tenant debit batch contains an operation outside the actor's tenant scope, every scope decision must complete before the debit writer changes quota state, and any denial or debit failure must leave both remaining capacity and the debit journal exactly as they were before the batch.

A caller may retry a rejected batch from the same capacity and journal state it observed before submission.
