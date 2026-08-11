const ALLOWED_KEY_ALGORITHMS = new Set(["rsa-3072", "ecdsa-p256"]);

const DEFECT_PRIORITY = {
  unsupported_key: 0,
  identity_change: 1,
  missing_dns_name: 2,
  malformed_dns_name: 3,
};

const DNS_NAME = /^(?:\*\.)?[a-z0-9]+(?:[.-][a-z0-9]+)+$/;

export function collectCsrDefects(csr, currentSubject) {
  const defects = [];
  if (!ALLOWED_KEY_ALGORITHMS.has(csr.keyAlgorithm)) {
    defects.push({
      reason: "unsupported_key",
      field: "keyAlgorithm",
      position: csr.dnsNames?.length ?? 0,
    });
  }

  const dnsNames = Array.isArray(csr.dnsNames) ? csr.dnsNames : [];
  if (dnsNames.length === 0) {
    defects.push({ reason: "missing_dns_name", field: "dnsNames", position: 0 });
  }
  dnsNames.forEach((dnsName, position) => {
    if (typeof dnsName !== "string" || !DNS_NAME.test(dnsName)) {
      defects.push({
        reason: "malformed_dns_name",
        field: `dnsNames[${position}]`,
        position,
      });
      return;
    }
    if (!currentSubject.dnsNames.includes(dnsName)) {
      defects.push({
        reason: "identity_change",
        field: `dnsNames[${position}]`,
        position,
      });
    }
  });
  return defects;
}

export function rankCsrDefects(defects) {
  return [...defects].sort(
    (left, right) => left.reason.localeCompare(right.reason)
      || right.position - left.position,
  );
}
