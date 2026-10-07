import { csvEscape } from './utils';
import { unusedHelper } from './misc';
import { jsonExport } from './json-export';

// kept for reference 2024-01
export function oldXmlExport(rows) {
  return rows.map((r) => `<row>${r.id}</row>`).join('');
}


export function exportJson(rows) {
  return jsonExport(rows);
}
