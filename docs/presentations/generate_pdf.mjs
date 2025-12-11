import puppeteer from 'puppeteer';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { marked } from 'marked';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CSS = `
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #1a1a1a;
    padding: 40px;
    max-width: 100%;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    color: #000;
    border-bottom: 3px solid #0066cc;
    padding-bottom: 12px;
    margin-top: 24px;
  }
  h2 {
    font-size: 20px;
    font-weight: 600;
    color: #333;
    margin-top: 28px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 8px;
  }
  h3 {
    font-size: 16px;
    font-weight: 600;
    color: #444;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 13px;
  }
  th, td {
    border: 1px solid #ccc;
    padding: 10px;
    text-align: left;
  }
  th {
    background-color: #f5f5f5;
    font-weight: 600;
  }
  tr:nth-child(even) {
    background-color: #fafafa;
  }
  pre, code {
    font-family: 'SF Mono', Monaco, 'Courier New', monospace;
    font-size: 11px;
    background-color: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: 8px;
    white-space: pre-wrap;
    word-wrap: break-word;
    overflow-wrap: break-word;
  }
  hr {
    border: none;
    border-top: 2px solid #eee;
    margin: 32px 0;
  }
  ul, ol {
    padding-left: 24px;
  }
  li {
    margin: 6px 0;
  }
  strong {
    color: #000;
  }
`;

async function generatePDF(mdFile, pdfFile) {
  console.log(`Converting ${path.basename(mdFile)} -> ${path.basename(pdfFile)}`);

  const mdContent = fs.readFileSync(mdFile, 'utf-8');
  const htmlContent = marked.parse(mdContent);

  const fullHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>${CSS}</style>
    </head>
    <body>
      ${htmlContent}
    </body>
    </html>
  `;

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage();
  await page.setContent(fullHtml, { waitUntil: 'networkidle0' });

  await page.pdf({
    path: pdfFile,
    format: 'A4',
    printBackground: true,
    margin: { top: '20mm', right: '15mm', bottom: '20mm', left: '15mm' }
  });

  await browser.close();
  console.log(`  Created: ${path.basename(pdfFile)}`);
}

async function main() {
  const files = [
    '01_ARCHITECTURE.md',
    '02_LICENSE.md',
    '03_CLOUD_PRICING.md',
    '04_PROJECT_OVERVIEW_KR.md'
  ];

  for (const mdFile of files) {
    const mdPath = path.join(__dirname, mdFile);
    const pdfPath = path.join(__dirname, mdFile.replace('.md', '.pdf'));
    if (fs.existsSync(mdPath)) {
      await generatePDF(mdPath, pdfPath);
    }
  }

  console.log('\nDone! PDFs in:', __dirname);
}

main().catch(console.error);
