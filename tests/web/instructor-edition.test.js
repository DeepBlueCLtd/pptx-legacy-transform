/** Spec 003 — Instructor edition (User Story 2) acceptance tests.
 *
 *  These assertions run against the live html/instructor/ tree
 *  alongside the html/student/ tree. They cover SC-007 (instructor
 *  edition unmistakably marked) and FR-016 (URL parity across
 *  editions).
 */

const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

const {
  INSTRUCTOR_ROOT,
  STUDENT_ROOT,
  requirePublisherRun,
  walkFiles,
  readText,
} = require('./helpers');

beforeAll(() => requirePublisherRun());

describe('SC-007 — instructor pages clearly marked as the instructor edition', () => {
  test('every publication-level page exposes "Instructor Version" in its title or first heading', () => {
    // FR-002c locates the "Instructor Version" decoration on the
    // publication-level title or page header. DITA-OT renders that
    // suffix on the per-publication index.html files (the map title
    // emitted as a <title> child element of <map>). Individual gram
    // pages carry their own gram title — they reach this edition
    // through a marked publication index, not through their own page
    // title.
    const offenders = [];
    for (const file of walkFiles(INSTRUCTOR_ROOT)) {
      const rel = path.relative(INSTRUCTOR_ROOT, file);
      // Publication-level pages: <stem>/index.html (e.g. main/index.html,
      // progress-test-1/index.html) plus the per-edition index.html.
      const isPublicationLevel =
        /^[a-z0-9-]+\/index\.html$/.test(rel) || rel === 'index.html';
      if (!isPublicationLevel) continue;
      const $ = cheerio.load(readText(file));
      const title = $('title').text();
      const h1 = $('h1').first().text();
      if (!/Instructor Version|Instructor edition/i.test(title) &&
          !/Instructor Version|Instructor edition/i.test(h1)) {
        offenders.push({
          file: rel,
          title: title.trim(),
          h1: h1.trim(),
        });
      }
    }
    expect(offenders).toEqual([]);
  });
});

describe('FR-016 — URL parity between editions (HTML pages)', () => {
  // URL parity applies to *pages*. Assets referenced only by audience-
  // filtered sections (e.g. analysis-sheet.docx, analysis.png — linked
  // from the trainee-only <section audience="-trainee">) legitimately
  // exist only in the instructor edition; the student edition's filter
  // strips the referencing section and DITA-OT therefore does not copy
  // the asset.

  test('every .html page under html/instructor/ has a sibling at the same path under html/student/', () => {
    const missing = [];
    for (const file of walkFiles(INSTRUCTOR_ROOT)) {
      if (!file.endsWith('.html')) continue;
      const rel = path.relative(INSTRUCTOR_ROOT, file);
      const sibling = path.join(STUDENT_ROOT, rel);
      if (!fs.existsSync(sibling)) {
        missing.push(rel);
      }
    }
    expect(missing).toEqual([]);
  });

  test('every .html page under html/student/ has a sibling at the same path under html/instructor/', () => {
    const missing = [];
    for (const file of walkFiles(STUDENT_ROOT)) {
      if (!file.endsWith('.html')) continue;
      const rel = path.relative(STUDENT_ROOT, file);
      const sibling = path.join(INSTRUCTOR_ROOT, rel);
      if (!fs.existsSync(sibling)) {
        missing.push(rel);
      }
    }
    expect(missing).toEqual([]);
  });
});

describe('SC-003 — Analysis Sheets retained in the instructor edition', () => {
  test('at least three gram pages under html/instructor/ contain an "Analysis Sheet" heading', () => {
    let count = 0;
    for (const file of walkFiles(INSTRUCTOR_ROOT)) {
      if (!/gram_\d+\.html$/.test(file)) continue;
      const $ = cheerio.load(readText(file));
      const headings = $('h1, h2, h3, h4').map((_, el) => $(el).text().trim()).get();
      if (headings.some((h) => /Analysis Sheet/i.test(h))) {
        count += 1;
      }
      if (count >= 3) break;
    }
    expect(count).toBeGreaterThanOrEqual(3);
  });
});
