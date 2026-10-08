// Print dist/report.html to PDF with the Edge that is already installed.
// Headless: it opens no window. Usage: PLAYWRIGHT_DIR=<path to playwright> node make_pdf.js in.html out.pdf
const path = require('path');
const { pathToFileURL } = require('url');
const { chromium } = require(process.env.PLAYWRIGHT_DIR);
(async () => {
  const [, , inp, out] = process.argv;
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage();
  await page.emulateMedia({ media: 'print' });
  await page.goto(pathToFileURL(path.resolve(inp)).href);
  await page.pdf({ path: path.resolve(out), format: 'A4', printBackground: true,
                   margin: { top: '16mm', bottom: '16mm', left: '14mm', right: '14mm' } });
  await browser.close();
})().catch(e => { console.error(String(e)); process.exit(1); });
