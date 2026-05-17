// Capture real screenshots of the published, GramFrame-enabled HTML output.
// Output goes to presentation/assets/screenshots/.
//
// Run with: NODE_PATH=/opt/node22/lib/node_modules node presentation/scripts/shoot.js

const { chromium } = require('playwright');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const htmlRoot = path.join(repoRoot, 'html');
const outDir = path.join(repoRoot, 'presentation', 'assets', 'screenshots');

const targets = [
  {
    name: 'styled-gram',
    file: 'instructor/main/week-1-grams/gram-09/gram_09.html',
    viewport: { width: 1100, height: 1700 },
    wait: 2500,
  },
  {
    name: 'styled-gram-student',
    file: 'student/main/week-1-grams/gram-09/gram_09.html',
    viewport: { width: 1100, height: 1700 },
    wait: 2500,
  },
  {
    name: 'styled-instructor-index',
    file: 'instructor/main/index.html',
    viewport: { width: 1280, height: 1800 },
    wait: 600,
  },
  {
    name: 'styled-student-index',
    file: 'student/main/index.html',
    viewport: { width: 1280, height: 1800 },
    wait: 600,
  },
  {
    name: 'styled-landing',
    file: 'index.html',
    viewport: { width: 1280, height: 600 },
    wait: 400,
  },
];

(async () => {
  const browser = await chromium.launch();
  for (const t of targets) {
    const ctx = await browser.newContext({ viewport: t.viewport, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    const url = 'file://' + path.join(htmlRoot, t.file);
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForLoadState('networkidle').catch(() => {});
    await page.waitForTimeout(t.wait);
    const out = path.join(outDir, t.name + '.png');
    await page.screenshot({ path: out, fullPage: true });
    console.log('wrote', out);
    await ctx.close();
  }
  await browser.close();
})();
