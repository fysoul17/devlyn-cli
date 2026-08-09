# Firmware rollout contract

Device attestation orders firmware requests by descending rollout priority with arrival order breaking ties, rejects every unprivileged request whose signer is not trusted for its rollout ring, and when privileged and unprivileged requests interleave it decides authorization before wave placement so denied devices never consume ordered slots.
