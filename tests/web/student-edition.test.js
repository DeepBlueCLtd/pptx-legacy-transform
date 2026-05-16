/** Spec 003 — Student edition (User Story 1) acceptance tests.
 *
 *  These assertions run against the live html/student/ tree produced
 *  by `python publish_html.py`. They cover SC-001, SC-002, SC-003 and
 *  FR-010 / FR-015.
 */

const path = require('path');
const cheerio = require('cheerio');

const {
  STUDENT_ROOT,
  requirePublisherRun,
  walkFiles,
  walkAllPaths,
  readText,
} = require('./helpers');

beforeAll(() => requirePublisherRun());

describe('SC-002 — no "instructor" substring under html/student/', () => {
  test('no file content under html/student/ contains "instructor"', () => {
    const offenders = [];
    for (const file of walkFiles(STUDENT_ROOT)) {
      const content = readText(file);
      if (/instructor/i.test(content)) {
        const rel = path.relative(STUDENT_ROOT, file);
        offenders.push(rel);
      }
    }
    expect(offenders).toEqual([]);
  });

  test('no path component under html/student/ contains "instructor"', () => {
    const offenders = [];
    for (const p of walkAllPaths(STUDENT_ROOT)) {
      const rel = path.relative(STUDENT_ROOT, p);
      if (/instructor/i.test(rel)) {
        offenders.push(rel);
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe('SC-001 — gram-number-only headings in the student edition', () => {
  test('every gram page heading matches /^Gram \\d+$/ with no separator or vessel name', () => {
    const offenders = [];
    for (const file of walkFiles(STUDENT_ROOT)) {
      if (!/gram_\d+\.html$/.test(file)) continue;
      const $ = cheerio.load(readText(file));
      // DITA-OT renders the topic <title> as the first <h1> on the page.
      const heading = $('h1').first().text().trim();
      if (!/^Gram \d+$/.test(heading)) {
        offenders.push({ file: path.relative(STUDENT_ROOT, file), heading });
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe('SC-003 — no Analysis Sheet sections in the student edition', () => {
  test('no rendered page contains an "Analysis Sheet" heading or string', () => {
    const offenders = [];
    for (const file of walkFiles(STUDENT_ROOT)) {
      if (!file.endsWith('.html')) continue;
      const content = readText(file);
      if (/Analysis Sheet/i.test(content)) {
        offenders.push(path.relative(STUDENT_ROOT, file));
      }
    }
    expect(offenders).toEqual([]);
  });
});
