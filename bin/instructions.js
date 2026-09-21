const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const legacyTemplates = require('./instruction-templates.json');

const BEGIN = '<!-- devlyn:instructions:begin';
const END = '<!-- devlyn:instructions:end -->';
const LEGACY = /^devlyn-cli installs |^# Devlyn Agent Instructions\r?$|^This contract serves one goal: any capable engine|^Engine roles: orchestrator =/m;
const normalize = (text) => text.replace(/\r\n/g, '\n');
const digest = (text) => crypto.createHash('sha256').update(text).digest('hex');

class InstructionError extends Error {}

function managedBlock(template, eol) {
  const body = 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
    + normalize(template).replace(/\n?$/, '\n');
  return `${BEGIN} sha256=${digest(body)} -->\n${body}${END}\n`.replace(/\n/g, eol);
}

function matchedEnd(text, start, template) {
  let end = start;
  for (let n = 0; n < template.length && end < text.length; n++, end++) {
    if (text[end] === '\r' && text[end + 1] === '\n') end++;
  }
  return digest(normalize(text.slice(start, end))) === template.sha256 ? end : null;
}

// A digest is ownership evidence; a familiar heading alone is not.
function legacyRanges(text, templates) {
  const starts = [...new Set([0, ...(text.startsWith('\uFEFF') ? [1] : []),
    ...Array.from(text.matchAll(/^# (?:Codex )?Project Instructions\r?$/gm), (m) => m.index)])].sort((a, b) => a - b);
  const ranges = [];
  for (const start of starts) {
    for (const template of templates) {
      let end = matchedEnd(text, start, template);
      let custom = '';
      if (end === null && template.body) {
        const prefix = text.slice(start, starts.find((offset) => offset > start));
        const body = /^## North Star\r?$/m.exec(prefix);
        const header = template.preamble.slice(0, template.preamble.indexOf('\n\n') + 2);
        if (body && normalize(prefix).startsWith(header)) {
          const bodyStart = start + body.index;
          end = matchedEnd(text, bodyStart, template.body);
          // Remove only an exact original preamble; preserve an edited one in full.
          const preambleEnd = matchedEnd(text, start, { length: template.preamble.length, sha256: digest(template.preamble) });
          custom = text.slice(preambleEnd ?? start, bodyStart);
        }
      }
      if (end !== null) {
        const existing = ranges.find((range) => range.start === start && range.end === end);
        if (!existing) ranges.push({ start, end, custom });
        // Releases may share a body. Prefer the exact owned preamble, if found.
        else if (custom.length < existing.custom.length) existing.custom = custom;
      }
    }
  }
  return ranges;
}

function retainFile(file, bytes) {
  for (const directory of [path.dirname(path.dirname(file)), path.dirname(file)]) {
    const stat = fs.lstatSync(directory, { throwIfNoEntry: false });
    if (stat && !stat.isDirectory()) {
      throw new InstructionError(`Instruction recovery needs a real directory: ${directory}. Move it aside and rerun installation.`);
    }
    if (!stat) fs.mkdirSync(directory);
  }
  const ignore = path.join(path.dirname(file), '.gitignore');
  if (!fs.existsSync(ignore)) fs.writeFileSync(ignore, '*\n', { flag: 'wx', mode: 0o600 });
  if (fs.existsSync(file)) {
    if (!fs.lstatSync(file).isFile() || !fs.readFileSync(file).equals(bytes)) {
      throw new InstructionError(`Instruction recovery file differs; preserved it: ${file}. Move it aside before retrying.`);
    }
  } else {
    fs.writeFileSync(file, bytes, { flag: 'wx', mode: 0o600 });
  }
}

function updateInstructions(name) {
  const templatePath = path.join(__dirname, '..', name);
  const template = fs.readFileSync(templatePath, 'utf8');
  if (template.includes(BEGIN) || template.includes(END)) {
    throw new Error(`Packaged instruction template contains managed markers: ${templatePath}`);
  }
  const dest = path.join(process.cwd(), name);
  const stat = fs.lstatSync(dest, { throwIfNoEntry: false });
  const sourceStat = fs.statSync(templatePath);
  if (stat?.isFile() && stat.dev === sourceStat.dev && stat.ino === sourceStat.ino) {
    console.log(`  → Using source ${name}; packaged template left unchanged`);
    return false;
  }
  const exists = Boolean(stat);
  // Do not replace a shared instruction symlink or follow it outside the project.
  if (stat && !stat.isFile()) {
    throw new InstructionError(`Instruction file must be a regular file; preserved: ${dest}. Move it aside and rerun, then merge your shared rules outside the managed block.`);
  }
  const before = exists ? fs.readFileSync(dest) : Buffer.alloc(0);
  let current;
  try {
    current = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(before);
  } catch (cause) {
    throw new InstructionError(`${name} must be UTF-8; original preserved. Convert its encoding and rerun installation.`, { cause });
  }
  const eol = current.match(/\r?\n/)?.[0] || '\n';
  const block = managedBlock(template, eol);
  const recovery = path.join(process.cwd(), '.devlyn', 'instructions');
  const conflict = (reason) => {
    const incoming = path.join(recovery, `${name}.${digest(block)}.incoming`);
    const backup = path.join(recovery, `${name}.${digest(before)}.backup`);
    const guide = path.join(recovery, `${name}.${digest(before)}.${digest(block)}.merge.md`);
    retainFile(backup, before);
    retainFile(incoming, Buffer.from(block));
    retainFile(guide, Buffer.from(`# Merge ${name}\n\n`
      + `Installation stopped: ${reason}. The original file is unchanged.\n\n`
      + `- Backup before this install attempt: ${backup}\n- New Devlyn defaults: ${incoming}\n- File to update: ${dest}\n\n`
      + `1. Compare the backup and new defaults side by side. Identify all project-specific additions and edits; do not discard them.\n`
      + `2. Update ${name} with exactly one complete managed block from the new defaults. Keep project-specific rules outside that block; they take precedence. Resolve conflicting rules explicitly. Do not copy the new defaults over the whole file.\n`
      + `3. Review the result, then rerun the same install command (for example, npx devlyn-cli). Other selected agents may still need installation.\n\n`
      + `To undo this manual merge, restore that backup to ${dest}. Earlier backups are retained too.\n`));
    throw new InstructionError(`${name} needs merge (${reason}).\n`
      + `Original preserved: ${dest}\nBackup: ${backup}\nNew defaults: ${incoming}\n`
      + `Merge instructions: ${guide}\n`
      + `Keep custom rules outside the managed block, then rerun the same install command.\n`
      + `Installation is incomplete; earlier selected agents may already have been updated.`);
  };
  let content;
  if (current.includes(BEGIN) || current.includes(END)) {
    const starts = [...current.matchAll(/^\uFEFF?<!-- devlyn:instructions:begin sha256=([a-f0-9]{64}) -->\r?\n/gm)];
    const ends = [...current.matchAll(/^<!-- devlyn:instructions:end -->(?:\r?\n|$)/gm)];
    if (starts.length !== 1 || ends.length !== 1
        || current.split(BEGIN).length !== 2 || current.split(END).length !== 2) {
      return conflict('ambiguous managed markers');
    }
    const start = starts[0];
    const end = ends[0];
    const bodyStart = start.index + start[0].length;
    if (end.index < bodyStart || digest(normalize(current.slice(bodyStart, end.index))) !== start[1]) {
      return conflict('managed defaults were edited');
    }
    content = current.slice(0, start.index + (start[0].startsWith('\uFEFF') ? 1 : 0)) + block + current.slice(end.index + end[0].length);
  } else {
    const normalized = normalize(template);
    const bodyStart = normalized.indexOf('## North Star\n');
    const preamble = normalized.slice(0, bodyStart);
    const body = normalized.slice(bodyStart);
    const ranges = legacyRanges(current, [
      { length: normalized.length, sha256: digest(normalized),
        ...(bodyStart > 0 ? { preamble, body: { length: body.length, sha256: digest(body) } } : {}) },
      ...(legacyTemplates[name] || []),
    ]);
    if (ranges.length > 1) return conflict('multiple legacy templates');
    if (ranges.length === 1) {
      const { start, end, custom } = ranges[0];
      if (LEGACY.test(current.slice(0, start) + custom + current.slice(end))) {
        return conflict('edited legacy introduction or extra template text');
      }
      content = current.slice(0, start) + custom + block + current.slice(end);
    } else {
      if (LEGACY.test(current)) {
        return conflict('unrecognized or edited legacy template');
      }
      content = current + (current ? eol + eol : '') + block;
    }
  }
  const bytes = Buffer.from(content);
  if (bytes.equals(before)) return false;
  if (exists) {
    const backup = path.join(recovery, `${name}.${digest(before)}.backup`);
    retainFile(backup, before);
    console.log(`  → Saved previous ${name}: ${backup}`);
  }
  const temp = `${dest}.${crypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temp, bytes, { flag: 'wx', mode: exists ? stat.mode & 0o777 : 0o644 });
    if (exists) fs.chmodSync(temp, stat.mode & 0o777);
    if (fs.existsSync(dest) !== exists || (exists && !fs.readFileSync(dest).equals(before))) {
      throw new InstructionError(`${name} changed during installation; preserved it. Rerun installation.`);
    }
    fs.renameSync(temp, dest);
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
  }
  console.log(`  → Updated Devlyn defaults in ${name}; project-specific instructions preserved`);
  return true;
}

module.exports = { updateInstructions, InstructionError };
