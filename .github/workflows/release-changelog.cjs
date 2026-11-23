'use strict';

// Installed by the engineering agent loop. Edit it in dlt-hub/engineering-agent-loop, not
// here. Two halves of one release: `--cut` moves what `## [Unreleased]` has collected under a
// version heading, and `--notes` reads that heading's section back out as the body of the
// GitHub release.
//
// `--cut` is the inverse of `insertEntry` in `bump-changelog-entry.cjs`. That one keeps
// `[Unreleased]` holding one bullet per thing a bump changes; this one draws a line under
// everything there and leaves the heading empty for the next bump. Emptying it is also what
// makes the next bump's entry start from this release rather than restate it.

const fs = require('node:fs');

/** `--cut` found `[Unreleased]` empty: an answer rather than a failure. */
const EMPTY = 3;

const UNRELEASED = /^## \[Unreleased\]/;
const HEADING = /^## /;
const SECTION = /^### /;

/** Where a `## ` heading's lines end: the next one, or the end of the file. */
function sectionEnd(lines, at) {
  const next = lines.findIndex((l, i) => i > at && HEADING.test(l));
  return next === -1 ? lines.length : next;
}

/** The lines a `## ` heading owns, with the blank lines around them dropped. */
function sectionBody(lines, at) {
  const body = lines.slice(at + 1, sectionEnd(lines, at));
  while (body.length && !body[0].trim()) body.shift();
  while (body.length && !body[body.length - 1].trim()) body.pop();
  return body;
}

/**
 * Whether a `### ` heading holds at least one line of its own. A block of headings with
 * nothing under them is what a half-finished edit leaves, and it is the one shape a grep for
 * `###` would read as something to release.
 */
function hasEntries(body) {
  let under = false;
  for (const line of body) {
    if (SECTION.test(line)) { under = true; continue; }
    if (under && line.trim()) return true;
  }
  return false;
}

function cut(changelog, version, date) {
  const lines = String(changelog).split('\n');
  const at = lines.findIndex((l) => UNRELEASED.test(l));
  if (at === -1) throw new Error('the changelog has no `## [Unreleased]` heading');
  if (lines.some((l) => l.startsWith(`## [${version}]`))) {
    throw new Error(`the changelog already carries a \`## [${version}]\` heading`);
  }
  if (!hasEntries(sectionBody(lines, at))) {
    // its own exit code, so the workflow can tell "there is nothing to release yet", which is
    // an answer, from a changelog it could not read, which is a defect
    throw Object.assign(
      new Error('`## [Unreleased]` holds no entries, so there is nothing to release'),
      { code: EMPTY },
    );
  }
  // the heading goes *under* `[Unreleased]`, so the sections already written drop beneath it
  // and `[Unreleased]` stays, empty, for the next bump to write into
  lines.splice(at + 1, 0, '', `## [${version}] - ${date}`);
  return lines.join('\n');
}

function notes(changelog, version) {
  const lines = String(changelog).split('\n');
  const at = lines.findIndex((l) => l.startsWith(`## [${version}]`));
  if (at === -1) throw new Error(`the changelog has no \`## [${version}]\` heading`);
  const body = sectionBody(lines, at);
  if (!body.length) throw new Error(`\`## [${version}]\` holds no entries`);
  return `${body.join('\n')}\n`;
}

function main(argv, io = console) {
  const value = (name) => {
    const i = argv.indexOf(name);
    return i === -1 ? null : argv[i + 1];
  };
  const file = value('--changelog');
  const version = value('--version');
  if (!file || !version) {
    io.error('release-changelog: --changelog and --version are both required');
    return 2;
  }
  const text = fs.readFileSync(file, 'utf8');

  try {
    if (argv.includes('--cut')) {
      const date = value('--date');
      if (!date) {
        io.error('release-changelog: --cut needs --date');
        return 2;
      }
      fs.writeFileSync(file, cut(text, version, date));
      io.error(`release-changelog: cut \`## [${version}] - ${date}\` in ${file}`);
      io.log(notes(fs.readFileSync(file, 'utf8'), version));
      return 0;
    }
    io.log(notes(text, version));
    return 0;
  } catch (err) {
    io.error(`release-changelog: ${err.message}`);
    return err.code === EMPTY ? EMPTY : 1;
  }
}

if (require.main === module) process.exit(main(process.argv.slice(2)));

module.exports = {
  EMPTY, sectionEnd, sectionBody, hasEntries, cut, notes, main,
};
