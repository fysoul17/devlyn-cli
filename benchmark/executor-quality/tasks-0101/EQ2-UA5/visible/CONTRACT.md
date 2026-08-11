# Backup rotation contract

A failed rotation restores every physical snapshot slot and catalog entry to its pre-rotation value, completed rotation tokens and snapshot identifiers take effect at most once, and retrying the same plan after that rollback resumes at the clean allocation position so the retention chain and physical slot ownership advance exactly once.

The snapshot applier writes into a fixed-size ring while the catalog owns the
oldest-to-newest retention chain. A write can fail after changing a slot, and
operators retry the same plan after repairing that draft.
