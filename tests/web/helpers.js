/** Shared helpers for the spec-003 Jest test layer.
 *
 *  All tests run against the live html/ tree at the repo root, so the
 *  helpers expose path constants (so individual tests don't reinvent
 *  the same path math), a directory walker, and a small fixture-guard
 *  that fails fast with a clear message if the publisher hasn't been
 *  run.
 */

const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const HTML_ROOT = path.join(REPO_ROOT, 'html');
const INSTRUCTOR_ROOT = path.join(HTML_ROOT, 'instructor');
const STUDENT_ROOT = path.join(HTML_ROOT, 'student');

/** Throw a clear error if the publisher hasn't been run.
 *
 *  Jest's normal "file not found" error message points at our test
 *  code, which is the wrong place to look — the real fix is to run
 *  `python publish_html.py`. We surface that directly.
 */
function requirePublisherRun() {
  if (!fs.existsSync(HTML_ROOT)) {
    throw new Error(
      'html/ does not exist. Run `python publish_html.py --dita dita/ ' +
      '--out html/ --dita-ot <path>` before invoking `npm test`.'
    );
  }
  if (!fs.existsSync(INSTRUCTOR_ROOT) || !fs.existsSync(STUDENT_ROOT)) {
    throw new Error(
      `Both html/instructor/ and html/student/ must exist. Found: ` +
      `instructor=${fs.existsSync(INSTRUCTOR_ROOT)}, ` +
      `student=${fs.existsSync(STUDENT_ROOT)}. ` +
      `Re-run publish_html.py.`
    );
  }
}

/** Recursively walk a directory, yielding every absolute file path. */
function* walkFiles(root) {
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    if (entry.isDirectory()) {
      yield* walkFiles(full);
    } else if (entry.isFile()) {
      yield full;
    }
  }
}

/** Recursively walk a directory, yielding every absolute path (dirs + files). */
function* walkAllPaths(root) {
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    const full = path.join(root, entry.name);
    yield full;
    if (entry.isDirectory()) {
      yield* walkAllPaths(full);
    }
  }
}

/** Read a file as UTF-8 text. */
function readText(filePath) {
  return fs.readFileSync(filePath, 'utf-8');
}

module.exports = {
  REPO_ROOT,
  HTML_ROOT,
  INSTRUCTOR_ROOT,
  STUDENT_ROOT,
  requirePublisherRun,
  walkFiles,
  walkAllPaths,
  readText,
};
