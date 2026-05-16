/** Spec 003 — Output idempotency (Polish phase, T032).
 *
 *  Snapshots a sha256 hash of every file under html/ via Jest's
 *  toMatchSnapshot. The first run records the snapshot; subsequent
 *  runs over the same DITA source MUST match it. A non-matching
 *  snapshot is a signal that something non-deterministic has crept
 *  into the publisher output (FR-008 / SC-006).
 *
 *  This is a developer-visible safety net, not a hard gate — the
 *  snapshot is committed to the repo and updated explicitly with
 *  `npm test -- -u` when intentional output changes ship.
 */

const crypto = require('crypto');
const path = require('path');

const {
  HTML_ROOT,
  requirePublisherRun,
  walkFiles,
} = require('./helpers');

beforeAll(() => requirePublisherRun());

describe('FR-008 / SC-006 — publish output is byte-deterministic', () => {
  test('sha256 of every html/ file matches the committed snapshot', () => {
    const fs = require('fs');
    const hashes = {};
    for (const file of walkFiles(HTML_ROOT)) {
      const rel = path.relative(HTML_ROOT, file).split(path.sep).join('/');
      hashes[rel] = crypto
        .createHash('sha256')
        .update(fs.readFileSync(file))
        .digest('hex');
    }
    // Sort keys so the snapshot is order-stable regardless of filesystem
    // traversal order.
    const sorted = Object.fromEntries(
      Object.entries(hashes).sort(([a], [b]) => a.localeCompare(b))
    );
    expect(sorted).toMatchSnapshot();
  });
});
