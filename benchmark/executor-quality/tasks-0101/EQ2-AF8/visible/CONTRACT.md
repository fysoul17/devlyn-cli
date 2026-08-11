# Certificate renewal contract

Certificate renewal must authorize certificate ownership and an open renewal window before CSR review, CSR defects rank unsupported-key before identity-change before missing-DNS-name before malformed-DNS-name with CSR source order breaking same-reason ties, and an unauthorized malformed renewal must return the renewal denial without recording a CSR rejection, reserving a serial, or storing a certificate.

Renewal authorization requires an active certificate owned by the requesting account and a request day within its inclusive renewal window. Every denial returns `{ "ok": false, "error": "renewal_denied" }` without revealing which authorization check failed.

An authorized CSR may retain only names from the current certificate and must use `rsa-3072` or `ecdsa-p256`. A rejected CSR records exactly the selected defect. Successful issuance reserves a serial, stores the replacement certificate, and commits that serial in one issuance chain.
