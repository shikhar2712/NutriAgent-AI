/*
 * pdftext.js - on-device PDF text extraction (pdf.js) shaped like pdfplumber's output.
 *
 *   NutriPdf.extractText(bytes, opts) -> Promise<{ text, pages, tables, scanned }>
 *
 * opts.pdfjsLib  inject a pdf.js instance (node tests); default: global pdfjsLib
 * opts.workerSrc worker URL (default 'vendor/pdfjs/pdf.worker.min.js')
 * opts.maxPages  default 40
 * opts.password  for encrypted PDFs
 *
 * Errors: rejects with Error whose .code is 'PASSWORD' (needs/incorrect password),
 * 'INVALID' (not a readable PDF) or 'NO_PDFJS'. A PDF without a text layer resolves
 * with text '' and scanned:true.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.NutriPdf = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var LINE_TOL = 2.5;      // baseline tolerance, PDF units

  function fail(code, msg) { var e = new Error(msg); e.code = code; return e; }

  // Items of one page -> text lines, top to bottom, left to right.
  function pageToLines(items) {
    var toks = [];
    items.forEach(function (it) {
      if (typeof it.str !== 'string' || !it.transform) return;
      var h = Math.abs(it.transform[3]) || Math.abs(it.height) || 10;
      toks.push({ s: it.str, x: it.transform[4], y: it.transform[5], w: it.width || 0, h: h });
    });
    toks.sort(function (a, b) { return b.y - a.y || a.x - b.x; });

    var lines = [];
    toks.forEach(function (t) {
      var ln = lines[lines.length - 1];
      if (ln && Math.abs(ln.y - t.y) <= LINE_TOL) ln.items.push(t);
      else lines.push({ y: t.y, items: [t] });
    });

    return lines.map(function (ln) {
      ln.items.sort(function (a, b) { return a.x - b.x; });
      var out = '', prevEnd = null, prevH = 10;
      ln.items.forEach(function (t) {
        if (t.s === '' ) return;
        if (out !== '' && prevEnd !== null) {
          var gap = t.x - prevEnd, em = Math.max(prevH, t.h);
          var endsSp = /\s$/.test(out), startsSp = /^\s/.test(t.s);
          if (!endsSp && !startsSp) {
            if (gap > em * 0.9) out += '   ';        // column gap in a table row
            else if (gap > em * 0.12) out += ' ';    // word gap
          }
        }
        out += t.s;
        prevEnd = t.x + t.w; prevH = t.h;
      });
      return out.replace(/[ \t]+$/, '').replace(/^[ \t]+/, '');
    }).filter(function (l) { return l.trim() !== ''; });
  }

  function extractText(bytes, opts) {
    opts = opts || {};
    var lib = opts.pdfjsLib || (typeof pdfjsLib !== 'undefined' ? pdfjsLib : null);
    if (!lib) return Promise.reject(fail('NO_PDFJS', 'pdf.js is not loaded'));
    if (lib.GlobalWorkerOptions && !opts.pdfjsLib) {
      lib.GlobalWorkerOptions.workerSrc = opts.workerSrc || 'vendor/pdfjs/pdf.worker.min.js';
    }
    var data = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    var maxPages = opts.maxPages || 40;
    var params = { data: data };
    if (opts.password) params.password = opts.password;
    if (opts.pdfjsLib) params.disableWorker = true;   // node: no worker file needed

    return lib.getDocument(params).promise.then(function (doc) {
      var n = Math.min(doc.numPages, maxPages), text = '', chain = Promise.resolve();
      for (var i = 1; i <= n; i++) (function (pn) {
        chain = chain.then(function () { return doc.getPage(pn); })
          .then(function (page) { return page.getTextContent(); })
          .then(function (tc) {
            var lines = pageToLines(tc.items);
            if (lines.length) text += '\n--- Page ' + pn + ' ---\n' + lines.join('\n');
          });
      })(i);
      return chain.then(function () {
        text = text.trim();
        if (doc.destroy) doc.destroy();
        return { text: text, pages: doc.numPages, tables: [], scanned: text === '' };
      });
    }, function (err) {
      var name = err && err.name;
      if (name === 'PasswordException') throw fail('PASSWORD', 'This PDF is password protected.');
      throw fail('INVALID', 'Could not read this PDF' + (err && err.message ? ': ' + err.message : ''));
    });
  }

  return { extractText: extractText, _pageToLines: pageToLines };
});
