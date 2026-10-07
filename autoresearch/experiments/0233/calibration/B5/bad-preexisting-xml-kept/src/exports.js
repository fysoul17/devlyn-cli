import { unusedHelper } from './misc';
import { jsonExport } from './json-export';


export function exportJson(rows) {
  return jsonExport(rows);
}
