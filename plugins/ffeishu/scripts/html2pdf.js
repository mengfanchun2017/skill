// book.html -> PDF via Playwright chromium（含页码页眉）
const { chromium } = require('playwright-core');
const path = require('path');

(async () => {
  const T = process.env.BUILD_DIR || './pdfbuild';
  const BOOK = process.env.BOOK_TITLE || '文档合订本';
  const browser = await chromium.launch({
    executablePath: process.env.CHROME || (process.env.HOME + '/.local/state/pw-chromium/chrome'),
    args: ['--no-sandbox', '--font-render-hinting=none'],
  });
  const page = await browser.newPage();
  await page.goto('file://' + path.join(T, 'book.html'), { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  await page.pdf({
    path: path.join(T, BOOK + '.pdf'),
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div style="font-size:8px;color:#9aa3af;width:100%;padding:0 16mm;font-family:sans-serif;">' + BOOK + '</div>',
    footerTemplate: '<div style="font-size:8px;color:#9aa3af;width:100%;text-align:center;font-family:sans-serif;"><span class="pageNumber"></span> / <span class="totalPages"></span></div>',
    margin: { top: '16mm', bottom: '16mm', left: '16mm', right: '16mm' },
  });
  await browser.close();
  console.log('PDF done');
})();