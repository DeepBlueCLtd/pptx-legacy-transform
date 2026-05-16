/** Jest configuration for the HTML-output verification layer.
 *
 *  Python `unittest` (under tests/) covers:
 *    - generate_dita.py — DITA XML shape, chapter slug normalisation,
 *      ditamap element forms.
 *    - publish_html.py  — DITA-OT invocation, output paths, logging,
 *      idempotency of the publisher's own behaviour.
 *
 *  Jest (under tests/web/) covers:
 *    - rendered HTML content checks (no-`instructor` leakage,
 *      URL parity, gram heading shape, shared landing page).
 *
 *  Both layers are run independently. The Jest layer requires a real
 *  publisher run (i.e. a populated html/ tree) before `npm test` is
 *  invoked; see README and quickstart for the order.
 */
module.exports = {
  rootDir: './tests/web',
  testEnvironment: 'node',
  testMatch: ['**/*.test.js'],
};
