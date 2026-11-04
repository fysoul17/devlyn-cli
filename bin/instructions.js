const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const legacyTemplates = require('./instruction-templates.json');
const cleanupHistory = require('./cleanup-history.json');

const BEGIN = '<!-- devlyn:instructions:begin';
const END = '<!-- devlyn:instructions:end -->';
const LEGACY = /^devlyn-cli installs |^# Devlyn Agent Instructions\r?$|^This contract serves one goal: any capable engine|^Engine roles: orchestrator =/m;
const normalize = (text) => text.replace(/\r\n/g, '\n');
const digest = (text) => crypto.createHash('sha256').update(text).digest('hex');

class InstructionError extends Error {}

function managedBody(template) {
  return 'Project-specific instructions outside this managed block take precedence over these defaults.\n\n'
    + normalize(template).replace(/\n?$/, '\n');
}

function managedBlock(template, eol = '\n') {
  const body = managedBody(template);
  return `${BEGIN} sha256=${digest(body)} -->\n${body}${END}\n`.replace(/\n/g, eol);
}

function sessionDefaults(template) {
  return 'The following Devlyn instructions are defaults for this session. Explicit user and native owner/project instructions take precedence, except a Devlyn managed block (devlyn:instructions markers), which these defaults replace. They change no other engine instructions or permissions.\n\n'
    + normalize(template);
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
  const bom = text.startsWith('\uFEFF') ? 1 : 0;
  const starts = [...new Set([0, ...(bom ? [1] : []),
    ...instructionParagraphs(text.slice(bom))
      .filter((p) => p.level === 1 && /^# (?:Codex )?Project Instructions\r?\n/.test(p.text))
      .map((p) => p.start + bom)])];
  const ranges = [];
  for (const start of starts) {
    for (const template of templates) {
      const end = matchedEnd(text, start, template);
      if (end !== null && !ranges.some((range) => range.start === start && range.end === end)) ranges.push({ start, end });
    }
  }
  return ranges;
}

// Keep complete paragraphs (including fenced examples and comments) intact.
// Matching includes the heading path, so the same words in another section
// are not evidence that Devlyn owns them.
function instructionParagraphs(text) {
  return scanInstructions(text).paragraphs;
}

function scanInstructions(text) {
  const paragraphs = [];
  let pending = '', fence = null, comment = false, html = null, start = 0;
  const flush = () => {
    if (pending) paragraphs.push({ text: pending, start });
    start += pending.length;
    pending = '';
  };
  for (const line of text.match(/[^\n]*\n|[^\n]+$/g) || []) {
    if (!fence && !comment && !html && (/^(?:#{1,6} |(?:[-*+]|\d+[.)]) )/.test(line)
        || (/^#{1,6} [^\n]+\r?\n$/.test(pending) && !/^\r?\n$/.test(line)))) flush();
    pending += line;
    const marker = /^( {0,3})(`{3,}|~{3,})/.exec(line)?.[2];
    if (!comment && marker) {
      if (!fence) fence = marker;
      else if (marker[0] === fence[0] && marker.length >= fence.length
          && /^ {0,3}(?:`+|~+)\s*$/.test(line)) fence = null;
    }
    if (!fence) {
      let markup = '', cursor = 0;
      for (const marker of line.matchAll(/<!--|-->/g)) {
        if (!comment) markup += line.slice(cursor, marker.index);
        comment = marker[0] === '<!--';
        cursor = marker.index + marker[0].length;
      }
      if (!comment) markup += line.slice(cursor);
      const opening = /^ {0,3}<([a-z][\w:-]*)\b[^>]*>/i.exec(markup);
      if (!html && opening && !/\/>$/.test(opening[0])
          && !/^(?:area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$/i.test(opening[1])) {
        html = { tag: opening[1].toLowerCase(), depth: 0 };
      }
      if (html) {
        for (const tag of markup.matchAll(/<(\/?)([a-z][\w:-]*)\b[^>]*>/gi)) {
          if (tag[2].toLowerCase() === html.tag && !/\/>$/.test(tag[0])) html.depth += tag[1] ? -1 : 1;
        }
        if (html.depth <= 0) html = null;
      }
    }
    if (!fence && !comment && !html && /^\r?\n$/.test(line)) flush();
  }
  flush();
  const headings = [];
  for (const [index, paragraph] of paragraphs.entries()) {
    const value = normalize(paragraph.text).replace(/\n+$/, '');
    const heading = /^(#{1,6}) ([^\n]+)$/.exec(value);
    if (heading) {
      paragraph.level = heading[1].length;
      while (headings.length && headings.at(-1).level >= paragraph.level) headings.pop();
    }
    paragraph.parents = headings.map((h) => h.index);
    paragraph.key = digest(JSON.stringify([headings.map((h) => h.title), value]));
    if (heading) headings.push({ level: paragraph.level, title: value, index });
  }
  return { paragraphs, quoting: Boolean(fence || comment || html) };
}

function customInstructions(text, name) {
  const known = new Set(legacyTemplates.paragraphs[name] || []);
  const bom = text.startsWith('\uFEFF') ? '\uFEFF' : '';
  const paragraphs = instructionParagraphs(text.slice(bom.length));
  const keep = new Set();
  let legacy = false;
  for (const [index, paragraph] of paragraphs.entries()) {
    if (paragraph.level === 1) {
      const next = paragraphs.findIndex((p, i) => i > index && p.level === 1);
      const section = paragraphs.slice(index, next < 0 ? undefined : next);
      legacy = /^# (?:Codex )?Project Instructions\r?\n|^# Devlyn Agent Instructions\r?\n/.test(paragraph.text)
        && section.some((p) => !/^\s*(?:`{3}|~{3}|<!--)/.test(p.text) && LEGACY.test(p.text));
    }
    if (!legacy || !known.has(paragraph.key)) {
      keep.add(index);
      for (const parent of paragraph.parents) keep.add(parent);
    }
  }
  return bom + paragraphs.filter((_, index) => keep.has(index)).map((p) => p.text).join('');
}

// Only the complete appended bytes are owned, including the separator added by old installers.
// A heading inside a fenced example is not an installed instruction block.
function removeEvaluatorBlocks(text) {
  const headings = new Set(instructionParagraphs(text).filter((p) => p.level === 1).map((p) => p.start));
  const ranges = [];
  for (const match of text.matchAll(/\r?\n\r?\n---\r?\n\r?\n(?=# Devlyn Agent Instructions\r?\n)/g)) {
    if (!headings.has(match.index + match[0].length)) continue;
    for (const template of cleanupHistory.evaluators) {
      const end = matchedEnd(text, match.index, template);
      if (end !== null) { ranges.push({ start: match.index, end }); break; }
    }
  }
  for (const { start, end } of ranges.reverse()) text = text.slice(0, start) + text.slice(end);
  return text;
}

// Devlyn defaults in an instruction file: a managed block, or stock paragraphs of a template
// that a release before managed blocks copied in whole.
function holdsDevlynDefaults(name, text) {
  return text.includes(BEGIN) || customInstructions(text, name) !== text;
}

// The range a release provably wrote, or null: one block whose bytes still match its own digest
// and that no example quotes, or one whole template without markers. Anything else is the owner's.
function devlynCopy(name, text, template) {
  if (text.includes(BEGIN) || text.includes(END)) {
    const starts = [...text.matchAll(/^(\uFEFF?)<!-- devlyn:instructions:begin sha256=([a-f0-9]{64}) -->\r?\n/gm)];
    const ends = [...text.matchAll(/^<!-- devlyn:instructions:end -->(?:\r?\n|$)/gm)];
    if (starts.length !== 1 || ends.length !== 1 || text.split(BEGIN).length !== 2 || text.split(END).length !== 2) return null;
    const [start] = starts, [end] = ends;
    const body = start.index + start[0].length, first = start.index + start[1].length;
    if (end.index < body || digest(normalize(text.slice(body, end.index))) !== start[2]) return null;
    return scanInstructions(text.slice(0, first)).quoting ? null : { start: first, end: end.index + end[0].length };
  }
  const normalized = normalize(template);
  const ranges = legacyRanges(text, [{ length: normalized.length, sha256: digest(normalized) }, ...(legacyTemplates[name] || [])]);
  return ranges.length === 1 && !LEGACY.test(text.slice(0, ranges[0].start) + text.slice(ranges[0].end)) ? ranges[0] : null;
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

// Removes the devlyn defaults the file holds, keeping everything else. `write` false writes nothing and returns
// whether the file needs the removal. `evaluatorOnly` removes only appended evaluator blocks.
function removeInstructions(name, write = true, directory = process.cwd()) {
  const projectPackage = path.join(directory, 'package.json');
  if (fs.existsSync(path.join(directory, 'bin', 'devlyn.js')) && fs.existsSync(projectPackage)
      && JSON.parse(fs.readFileSync(projectPackage, 'utf8'))?.name === 'devlyn-cli') {
    console.log(`  → Skipping ${name}; shipped instruction template in devlyn-cli source checkout`);
    return false;
  }
  const templatePath = path.join(__dirname, '..', name);
  const template = ['CLAUDE.md', 'AGENTS.md'].includes(name) ? fs.readFileSync(templatePath, 'utf8') : '';
  if (template.includes(BEGIN) || template.includes(END)) {
    throw new Error(`Packaged instruction template contains managed markers: ${templatePath}`);
  }
  const dest = path.join(directory, name);
  const stat = fs.lstatSync(dest, { throwIfNoEntry: false });
  if (!stat) return false;
  const sourceStat = template ? fs.statSync(templatePath) : null;
  if (stat.isFile() && stat.dev === sourceStat?.dev && stat.ino === sourceStat?.ino) {
    console.log(`  → Using source ${name}; packaged template left unchanged`);
    return false;
  }
  // Do not replace a shared instruction symlink or follow it outside the project.
  if (!stat.isFile()) throw new InstructionError(`Instruction file must be a regular file; preserved: ${dest}.`);
  const before = fs.readFileSync(dest);
  let current;
  try {
    current = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(before);
  } catch (cause) {
    throw new InstructionError(`${name} must be UTF-8; original preserved.`, { cause });
  }
  let content = removeEvaluatorBlocks(current);
  const copy = template ? devlynCopy(name, content, template) : null;
  if (copy) content = content.slice(0, copy.start) + content.slice(copy.end);
  const bytes = Buffer.from(content);
  if (bytes.equals(before)) return false;
  if (!write) return true;
  const backup = path.join(directory, '.devlyn', 'instructions', `${encodeURIComponent(name)}.${digest(before)}.backup`);
  retainFile(backup, before);
  console.log(`  → Saved previous ${name}: ${backup}`);
  const empty = content.replace(/^\uFEFF/, '') === '';
  const temp = `${dest}.${crypto.randomUUID()}.tmp`;
  try {
    fs.writeFileSync(temp, bytes, { flag: 'wx', mode: stat.mode & 0o777 });
    fs.chmodSync(temp, stat.mode & 0o777);
    if (!fs.existsSync(dest) || !fs.readFileSync(dest).equals(before)) {
      throw new InstructionError(`${name} changed during removal; preserved it.`);
    }
    if (empty) fs.unlinkSync(dest);
    else fs.renameSync(temp, dest);
  } finally {
    if (fs.existsSync(temp)) fs.unlinkSync(temp);
  }
  console.log(empty ? `  ✕ ${name} (removed)` : `  → Removed Devlyn defaults from ${name}; project-specific instructions preserved`);
  return true;
}

module.exports = { removeInstructions, InstructionError, instructionParagraphs, holdsDevlynDefaults,
  managedBody, managedBlock, sessionDefaults };
