/** Spec 003 — Shared landing page + per-edition indexes (User Story 3).
 *
 *  Covers SC-004 (one-click navigation to either edition) and the
 *  per-edition index contracts from
 *  contracts/html-edition-layout.md §2 + §3.
 */

const fs = require('fs');
const path = require('path');
const cheerio = require('cheerio');

const {
  HTML_ROOT,
  INSTRUCTOR_ROOT,
  STUDENT_ROOT,
  requirePublisherRun,
  readText,
} = require('./helpers');

beforeAll(() => requirePublisherRun());

describe('SC-004 — html/index.html shared landing page', () => {
  test('exists at the html/ root', () => {
    expect(fs.existsSync(path.join(HTML_ROOT, 'index.html'))).toBe(true);
  });

  test('exposes exactly two links, one per edition, in instructor-then-student order', () => {
    const $ = cheerio.load(readText(path.join(HTML_ROOT, 'index.html')));
    const links = $('a').map((_, el) => $(el).attr('href')).get();
    expect(links).toEqual(['instructor/index.html', 'student/index.html']);
  });

  test('each edition link carries an audience description of at least 20 characters', () => {
    const $ = cheerio.load(readText(path.join(HTML_ROOT, 'index.html')));
    // Each <li> hosts the link plus the description text.
    const items = $('li').map((_, el) => $(el).text().trim()).get();
    expect(items).toHaveLength(2);
    for (const item of items) {
      // Strip the link text (e.g. "Instructor edition") and assert the
      // remainder (the audience description) is non-trivial.
      expect(item.length).toBeGreaterThanOrEqual(20 + 'Instructor edition'.length);
    }
  });
});

describe('per-edition index pages', () => {
  test('instructor index exists and contains the word "Instructor" in its heading', () => {
    const indexPath = path.join(INSTRUCTOR_ROOT, 'index.html');
    expect(fs.existsSync(indexPath)).toBe(true);
    const $ = cheerio.load(readText(indexPath));
    expect($('h1').first().text()).toMatch(/Instructor/);
  });

  test('student index exists and does NOT contain "instructor" anywhere', () => {
    const indexPath = path.join(STUDENT_ROOT, 'index.html');
    expect(fs.existsSync(indexPath)).toBe(true);
    const content = readText(indexPath);
    expect(content).not.toMatch(/instructor/i);
  });

  test('both edition indexes list the same publications in the same order', () => {
    const instructorLinks = cheerio
      .load(readText(path.join(INSTRUCTOR_ROOT, 'index.html')))('a')
      .map((_, el) => cheerio.load(`<a href="${el.attribs.href}"/>`)('a').attr('href'))
      .get();
    const studentLinks = cheerio
      .load(readText(path.join(STUDENT_ROOT, 'index.html')))('a')
      .map((_, el) => el.attribs.href)
      .get();
    expect(studentLinks).toEqual(instructorLinks);
    expect(instructorLinks.length).toBeGreaterThan(0);
  });

  test('each per-edition link points at <stem>/index.html', () => {
    const $ = cheerio.load(readText(path.join(INSTRUCTOR_ROOT, 'index.html')));
    const links = $('a').map((_, el) => el.attribs.href).get();
    for (const href of links) {
      expect(href).toMatch(/^[a-z0-9-]+\/index\.html$/);
    }
  });
});
