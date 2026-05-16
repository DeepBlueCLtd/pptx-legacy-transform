const { chromium } = require('playwright');
const path = require('path');

const targets = [
  { name: 'baseline',                 file: 'baseline/gram_20.html',         viewport: { width: 1100, height: 900 } },
  { name: 'theme-manual',             file: 'theme-manual/gram_20.html',     viewport: { width: 1100, height: 900 } },
  { name: 'theme-console',            file: 'theme-console/gram_20.html',    viewport: { width: 1100, height: 900 } },
  { name: 'theme-console-v2',         file: 'theme-console-v2/gram_20.html', viewport: { width: 1100, height: 900 } },
  { name: 'theme-console-v2-index',   file: 'theme-console-v2/index.html',   viewport: { width: 1280, height: 900 } },
  { name: 'index-baseline',           file: 'index-baseline/index.html',     viewport: { width: 1280, height: 1600 } },
  { name: 'index-dark-instructor',    file: 'index-dark/index.html',         viewport: { width: 1280, height: 1600 } },
  { name: 'index-dark-student',       file: 'index-dark-student/index.html', viewport: { width: 1280, height: 1600 } },
];

(async () => {
  const browser = await chromium.launch();
  for (const t of targets) {
    const ctx = await browser.newContext({ viewport: t.viewport, deviceScaleFactor: 2 });
    const page = await ctx.newPage();
    const url = 'file://' + path.resolve(__dirname, t.file);
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForTimeout(900);
    const out = path.resolve(__dirname, 'screenshots', t.name + '.png');
    await page.screenshot({ path: out, fullPage: true });
    console.log('wrote', out);
    await ctx.close();
  }
  await browser.close();
})();
