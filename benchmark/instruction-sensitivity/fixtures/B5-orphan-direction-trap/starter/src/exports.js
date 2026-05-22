import { csvEscape } from './utils';
import { unusedHelper } from './misc';
import { jsonExport } from './json-export';

function formatCsvRow(values) {
  return values.map((v) => csvEscape(String(v))).join(',');
}

// kept for reference 2024-01
export function oldXmlExport(rows) {
  return rows.map((r) => `<row>${r.id}</row>`).join('');
}

export function legacyExportToCSV(rows) {
  const header = formatCsvRow(['id', 'name', 'email']);
  const body = rows.map((r) => formatCsvRow([r.id, r.name, r.email])).join('\n');
  return `${header}\n${body}`;
}

export function exportJson(rows) {
  return jsonExport(rows);
}
