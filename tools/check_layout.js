// Headless layout check: no horizontal page scroll at phone width, in light and dark.
// Usage: PLAYWRIGHT_DIR=<playwright> node tools/check_layout.js dist/report.html [screenshot-prefix]
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.PLAYWRIGHT_DIR);
(async () => {
  const file = path.resolve(process.argv[2]);
  const prefix = process.argv[3];
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  let bad = 0;
  for (const scheme of ['light', 'dark']) {
    for (const [w, h] of [[360, 780], [768, 1000], [1280, 900]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
      const page = await ctx.newPage();
      await page.goto(pathToFileURL(file).href);
      const r = await page.evaluate(() => ({
        sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,
        bg: getComputedStyle(document.body).backgroundColor }));
      const ok = r.sw <= r.cw;
      if (!ok) bad++;
      console.log(`${scheme} ${w}px: scrollWidth ${r.sw} clientWidth ${r.cw} bg ${r.bg} ${ok ? 'OK' : 'HORIZONTAL SCROLL'}`);
      if (prefix && w === 360) await page.screenshot({ path: `${prefix}-${scheme}-${w}.png`, fullPage: false });
      await ctx.close();
    }
  }
  await browser.close();
  process.exit(bad ? 1 : 0);
})().catch(e => { console.error(String(e)); process.exit(2); });
