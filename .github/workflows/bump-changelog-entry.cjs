'use strict';

// Installed by the engineering agent loop. Edit it in dlt-hub/engineering-agent-loop, not
// here. Writes a dependency bump's changelog entry from the two `uv.lock` files, as a draft
// the reviewing pass then holds to the diff.
//
// The `--*-before` state the caller passes is the last release, not the tip the recipe just
// overwrote, so the entry is the whole account of what is unreleased. That is what lets a
// second bump before a release replace the bullets the bump before it wrote: both describe
// the same span, one of them a bump out of date. Appending instead grew `[Unreleased]` a
// second `Refreshed ...` line per run.

const fs = require('node:fs');

// not a TOML parser: every package is a `[[package]]` table whose first two keys are `name`
// and `version`, and a parser would be a dependency in a file that must have none
function parseLock(text) {
  const versions = new Map();
  let name = null;
  for (const line of String(text || '').split('\n')) {
    if (line.trim() === '[[package]]') { name = null; continue; }
    // `dependencies` and `wheels` are arrays of tables with `name` keys of their own
    if (/^\[/.test(line)) { name = null; continue; }
    const n = /^name = "([^"]+)"$/.exec(line);
    if (n) { name = normalise(n[1]); continue; }
    const v = /^version = "([^"]+)"$/.exec(line);
    if (v && name) { versions.set(name, v[1]); name = null; }
  }
  return versions;
}

/** PEP 503: lowercase, and every run of `-`, `_` or `.` is one `-`. */
function normalise(name) {
  return String(name).toLowerCase().replace(/[-_.]+/g, '-');
}

function diffLocks(before, after) {
  const moved = [];
  const added = [];
  const removed = [];
  for (const [name, to] of after) {
    const from = before.get(name);
    if (from === undefined) added.push({ name, to });
    else if (from !== to) moved.push({ name, from, to });
  }
  for (const [name, from] of before) {
    if (!after.has(name)) removed.push({ name, from });
  }
  const byName = (a, b) => a.name.localeCompare(b.name);
  return { moved: moved.sort(byName), added: added.sort(byName), removed: removed.sort(byName) };
}

// the optional groups count too: the root project puts `mypy` and `ruff` in `dev`.
// Line by line, because a `[` inside `authors = [` is indistinguishable from a table
// header to anything matching across lines
function directNames(text, into = new Set()) {
  const names = into;
  let table = '';
  let collecting = false;
  for (const line of String(text || '').split('\n')) {
    if (collecting) {
      if (/^\]/.test(line)) { collecting = false; continue; }
      addSpecifiers(names, line);
      continue;
    }
    const header = /^\[\[?([^\]]+)\]\]?\s*$/.exec(line);
    if (header) { table = header[1]; continue; }
    const key = /^([A-Za-z0-9._-]+)\s*=\s*\[(.*)$/.exec(line);
    if (!key) continue;
    const wanted = (table === 'project' && key[1] === 'dependencies')
      || table === 'project.optional-dependencies';
    if (!wanted) continue;
    if (key[2].includes(']')) addSpecifiers(names, key[2]);
    else { addSpecifiers(names, key[2]); collecting = true; }
  }
  return names;
}

function addSpecifiers(into, line) {
  for (const m of line.matchAll(/"([^"]+)"/g)) {
    const name = /^\s*([A-Za-z0-9][A-Za-z0-9._-]*)/.exec(m[1]);
    if (!name) continue;
    const key = normalise(name[1]);
    if (into instanceof Map) into.set(key, m[1].trim());
    else into.add(key);
  }
}

function directSpecs(text) {
  return directNames(text, new Map());
}

/**
 * The packages a bump watches, named in the entry whether or not a pyproject holds them.
 *
 * `lockBullet` names a direct dependency and counts a transitive, which is the shape of every
 * released entry. A package the whole bump exists for can be transitive: one scaffold depends
 * on `dlthub-client` by name and another reaches it through `dlt[hub]`, so without this the
 * one package a reader is looking for is counted among the three hundred nobody reads.
 */
function alsoNamed(value) {
  return new Set(String(value || '').split(',')
    .map((n) => n.trim()).filter(Boolean).map(normalise));
}

/**
 * The skills a `skills/` directory holds, or null where the caller named no such directory.
 *
 * A skill is one directory: `.gitkeep` and anything else loose beside them is not one. Null
 * rather than an empty list, because a baseline that is not there read as "no skills" reports
 * every skill in the repository as one this bump added.
 */
function skillNames(dir) {
  if (!dir || !fs.existsSync(dir)) return null;
  return fs.readdirSync(dir, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name)
    .sort((a, b) => a.localeCompare(b));
}

const versions = (list) => list.map((p) => `\`${p.name}\` ${p.from} → ${p.to}`);

// How each bullet opens. A second bump finds the first one's lines by these, so rewording one
// here is what rewords it everywhere, and a line a person wrote is left alone because it opens
// with something else
const LEADS = {
  scaffold: 'Refreshed the bundled minimal workspace `uv.lock` to the latest'
    + ' within-constraint versions',
  root: 'Refreshed the root `uv.lock` to the latest within-constraint versions',
  deps: "Synced the bundled minimal workspace dependencies with dlt's `workspace_deps()`",
  skills: 'Refreshed the bundled skills to workbench',
  session: 'Re-stamped the bundled notebook session snapshot to marimo',
};

/** Whether a changelog line is a bullet an earlier run of this script wrote. */
const isOwnBullet = (line) => Object.values(LEADS).some((lead) => line.startsWith(`- ${lead}`));

/** The `LEADS` keys a run was given both sides of, which are the bullets it may replace. */
function askedAbout({ scaffold, root, deps, skills, session }) {
  const given = { scaffold, root, deps, skills, session };
  return Object.keys(LEADS).filter((kind) => given[kind]);
}

/** "a", "a and b", "a, b and c" — the last separator is the one a reader expects. */
function sentenceList(parts) {
  if (parts.length < 2) return parts.join('');
  return `${parts.slice(0, -1).join(', ')} and ${parts[parts.length - 1]}`;
}

const plural = (n, noun) => `${n} ${noun}${n === 1 ? '' : 's'}`;

const skillList = (names) => sentenceList(names.map((n) => `\`${n}\``));

// Direct dependencies are named and transitives are counted, which is the shape of every
// released entry. It applies to a package arriving and leaving as much as to one moving
// version: a transitive that left is the resolver's business, and naming thirteen of them
// repeats, in a bullet about a lock, what the person who removed the dependency already
// wrote in `### Removed`.
function lockBullet({ lead, diff, direct }) {
  const split = (list) => {
    const named = list.filter((p) => direct.has(p.name));
    return { named, rest: list.length - named.length };
  };
  const moved = split(diff.moved);
  const added = split(diff.added);
  const removed = split(diff.removed);

  const parts = [lead];
  if (moved.named.length) parts.push(` (${versions(moved.named).join(', ')})`);

  const said = [];
  if (added.named.length) {
    said.push(`added ${added.named.map((p) => `\`${p.name}\` ${p.to}`).join(', ')}`);
  }
  if (removed.named.length) {
    said.push(`dropped ${removed.named.map((p) => `\`${p.name}\``).join(', ')}`);
  }
  const counted = [];
  if (moved.rest) counted.push(plural(moved.rest, 'transitive update'));
  if (added.rest) counted.push(plural(added.rest, 'new transitive'));
  if (removed.rest) counted.push(plural(removed.rest, 'transitive removal'));
  if (counted.length) said.push(`plus ${sentenceList(counted)}`);

  if (said.length) parts.push(`, ${said.join(', ')}`);
  return `- ${parts.join('')}.`;
}

function renderEntry({
  scaffold, root, direct, rootDirect = null, deps = null, skills = null, session = null,
}) {
  const bullets = [];
  if (scaffold && scaffold.moved.length + scaffold.added.length + scaffold.removed.length) {
    bullets.push(lockBullet({ lead: LEADS.scaffold, diff: scaffold, direct }));
  }
  if (deps && deps.added.length + deps.removed.length + deps.raised.length) {
    const said = [];
    if (deps.added.length) said.push(`added ${deps.added.map((n) => `\`${n}\``).join(', ')}`);
    if (deps.raised.length) {
      said.push(`changed ${deps.raised.map((r) => `\`${r.name}\` to \`${r.to}\``).join(', ')}`);
    }
    if (deps.removed.length) said.push(`dropped ${deps.removed.map((n) => `\`${n}\``).join(', ')}`);
    bullets.push(`- ${LEADS.deps}: ${said.join(', ')}.`);
  }
  if (root && root.moved.length + root.added.length + root.removed.length) {
    bullets.push(lockBullet({ lead: LEADS.root, diff: root, direct: rootDirect || direct }));
  }
  // The generator rewrites `skills/` whole at each ref, so a moved ref can add or drop a whole
  // skill that everybody running `uvx dlthub-init` then gets. A seven-character SHA says none
  // of that. What changed inside a skill that was already there is a person's to describe, as
  // it is in the released entries.
  if (skills && skills.from !== skills.to) {
    const said = [];
    if (skills.added && skills.added.length) said.push(`adding ${skillList(skills.added)}`);
    if (skills.removed && skills.removed.length) {
      said.push(`dropping ${skillList(skills.removed)}`);
    }
    const tail = said.length ? `, ${said.join(', ')}` : '';
    bullets.push(`- ${LEADS.skills} \`${skills.to}\`${tail}.`);
  }
  // The snapshot records the marimo version its cell outputs were built with, and a `marimo`
  // pin past it drops those outputs back to a live kernel run on every launch. The version
  // pair is in the lock bullet already where the scaffold names `marimo` directly, so this
  // names what the snapshot was stamped to and not what it came from.
  if (session && session.from !== session.to) {
    bullets.push(`- ${LEADS.session} \`${session.to}\`.`);
  }
  return bullets;
}

// Into the existing `### Changed` block under `[Unreleased]`, so a second bump opens no
// second heading, and in place of the bullets an earlier bump left there: both state what is
// unreleased and only the new ones are current. A line a person wrote stays where it is.
// Every released heading below is what the next release moves, and that is a person's act.
//
// `replaces` is which of the four a run computed, so a bullet that came out empty is dropped
// and one the caller was not asked about is left standing. The two look the same in
// `bullets` and mean opposite things
function insertEntry(changelog, bullets, replaces = Object.keys(LEADS)) {
  if (!bullets.length) return changelog;
  const lines = String(changelog).split('\n');
  const at = lines.findIndex((l) => /^## \[Unreleased\]/.test(l));
  if (at === -1) throw new Error('the changelog has no `## [Unreleased]` heading');
  const nextHeading = lines.findIndex((l, i) => i > at && /^## /.test(l));
  const end = nextHeading === -1 ? lines.length : nextHeading;
  const changed = lines.findIndex((l, i) => i > at && i < end && /^### Changed\s*$/.test(l));
  if (changed === -1) {
    lines.splice(at + 1, 0, '', '### Changed', ...bullets);
    return lines.join('\n');
  }
  // the block ends at the next `###`, not at the next `##`: `[Unreleased]` carries
  // `### Fixed` and `### Removed` beside it and the bullets belong above them
  const after = lines.findIndex((l, i) => i > changed && i < end && /^### /.test(l));
  const blockEnd = after === -1 ? end : after;
  const stale = replaces.map((kind) => `- ${LEADS[kind]}`);
  const kept = lines.slice(changed + 1, blockEnd)
    .filter((l) => !stale.some((lead) => l.startsWith(lead)));
  while (kept.length && !kept[0].trim()) kept.shift();
  while (kept.length && !kept[kept.length - 1].trim()) kept.pop();
  // the trailing blank is the one separating this block from the `###` or `##` after it, and
  // the file's own last newline where `[Unreleased]` is the only section
  lines.splice(changed + 1, blockEnd - changed - 1, ...kept, ...bullets, '');
  return lines.join('\n');
}

const read = (file) => (file && fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '');

function main(argv, io = console) {
  const value = (name) => {
    const i = argv.indexOf(name);
    return i === -1 ? null : argv[i + 1];
  };
  const lockDiff = (before, after) => (before && after
    ? diffLocks(parseLock(read(before)), parseLock(read(after)))
    : null);

  // The watched names go into both sets: which of the two locks a package turns up in does
  // not decide whether a reader wants it named.
  const also = alsoNamed(value('--also-name'));
  const direct = directNames(read(value('--direct')));
  const rootDirect = value('--root-direct') ? directNames(read(value('--root-direct'))) : null;
  for (const name of also) {
    direct.add(name);
    if (rootDirect) rootDirect.add(name);
  }

  const depsBefore = value('--deps-before');
  const depsAfter = value('--deps-after');
  let deps = null;
  if (depsBefore && depsAfter) {
    const was = directSpecs(read(depsBefore));
    const now = directSpecs(read(depsAfter));
    deps = {
      added: [...now.keys()].filter((n) => !was.has(n)).sort(),
      removed: [...was.keys()].filter((n) => !now.has(n)).sort(),
      raised: [...now.keys()].filter((n) => was.has(n) && was.get(n) !== now.get(n))
        .sort().map((name) => ({ name, from: was.get(name), to: now.get(name) })),
    };
  }
  const sessionFrom = value('--session-before');
  const sessionTo = value('--session-after');
  const skillsFrom = value('--skills-before');
  const skillsTo = value('--skills-after');
  const skillDirs = [value('--skills-dir-before'), value('--skills-dir-after')];
  const [wasSkills, nowSkills] = skillDirs.map(skillNames);
  if (skillDirs.some(Boolean) && !(wasSkills && nowSkills)) {
    io.error('bump-changelog-entry: a `skills/` directory the caller named is not there, so the'
      + ' workbench bullet names the ref alone');
  }
  const skillDiff = wasSkills && nowSkills
    ? {
      added: nowSkills.filter((n) => !wasSkills.includes(n)),
      removed: wasSkills.filter((n) => !nowSkills.includes(n)),
    }
    : { added: [], removed: [] };

  const entry = {
    scaffold: lockDiff(value('--scaffold-before'), value('--scaffold-after')),
    root: lockDiff(value('--root-before'), value('--root-after')),
    direct,
    rootDirect,
    deps,
    skills: skillsFrom && skillsTo ? { from: skillsFrom, to: skillsTo, ...skillDiff } : null,
    session: sessionFrom && sessionTo ? { from: sessionFrom, to: sessionTo } : null,
  };
  const bullets = renderEntry(entry);

  if (!bullets.length) {
    io.error('bump-changelog-entry: nothing moved, so there is no entry to write');
    return 1;
  }

  const changelog = value('--changelog');
  if (changelog) {
    const was = fs.readFileSync(changelog, 'utf8');
    const now = insertEntry(was, bullets, askedAbout(entry));
    // the bullets an earlier bump wrote, recomputed against the same release and come out
    // the same: this run rewrote a lock without moving a version anybody reads
    if (now === was) {
      io.error('bump-changelog-entry: the entry is already under `## [Unreleased]`, so this'
        + ' run has nothing new to say');
      return 1;
    }
    fs.writeFileSync(changelog, now);
    io.error(`bump-changelog-entry: wrote ${bullets.length} bullet(s) into ${changelog}`);
  }
  io.log(bullets.join('\n'));
  return 0;
}

if (require.main === module) process.exit(main(process.argv.slice(2)));

module.exports = {
  LEADS, isOwnBullet, askedAbout, parseLock, normalise, diffLocks, directNames, directSpecs,
  alsoNamed, skillNames, lockBullet, renderEntry, insertEntry, main,
};
