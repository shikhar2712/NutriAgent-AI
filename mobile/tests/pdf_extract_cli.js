// node pdf_extract_cli.js out.json a.pdf b.pdf ... -> writes JSON {path: result} to out.json (pdf.js via pdftext.js)
const fs = require('fs'), path = require('path');
const lib = require('pdfjs-dist/legacy/build/pdf.js');
const { extractText } = require('../web/js/pdftext.js');
(async () => {
  const out = {};
  for (const p of process.argv.slice(3)) {
    const r = await extractText(new Uint8Array(fs.readFileSync(p)), { pdfjsLib: lib });
    out[p] = r;
  }
  fs.writeFileSync(process.argv[2], JSON.stringify(out));
})().catch(e => { console.error(e.code, e.message); process.exit(1); });
