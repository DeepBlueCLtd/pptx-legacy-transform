const { chromium } = require('playwright');
const path = require('path');

const targets = [
  { name: 'baseline',      file: 'baseline/gram_20.html' },
  { name: 'theme-manual',  file: 'theme-manual/gram_20.html' },
  { name: 'theme-console', file: 'theme-console/gram_20.html' },
];

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1100, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  for (const t of targets) {
    const url = 'file://' + path.resolve(__dirname, t.file);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    const out = path.resolve(__dirname, 'screenshots', t.name + '.png');
    await page.screenshot({ path: out, fullPage: true });
    console.log('wrote', out);
  }
  await browser.close();
})();
