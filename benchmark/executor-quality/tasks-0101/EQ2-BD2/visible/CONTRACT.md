# Firmware rollout contract

The wave sequencer groups firmware requests by descending rollout priority with arrival order breaking ties, device attestation rejects every wave containing a device whose signer is not trusted for its rollout ring, and when privileged and unprivileged requests interleave attestation is decided before priority placement and wave grouping so denied devices neither consume positions nor cause trusted devices to be rejected with a mixed wave.
