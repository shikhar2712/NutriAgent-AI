/* md.js - tiny, safe markdown -> HTML. Everything is HTML-escaped first, so model output cannot inject markup. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(); else root.NutriMd = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function inline(s) {
    s = esc(s);
    const codes = [];
    s = s.replace(/`([^`]+)`/g, (_, c) => { codes.push(c); return '\u0000' + (codes.length - 1) + '\u0000'; });
    s = s.replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
         .replace(/__([^_]+?)__/g, '<strong>$1</strong>')
         .replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\w)/g, '$1<em>$2</em>')
         .replace(/(^|[^_\w])_([^_\s][^_]*?)_(?!\w)/g, '$1<em>$2</em>');
    return s.replace(/\u0000(\d+)\u0000/g, (_, i) => '<code>' + codes[+i] + '</code>');
  }

  function splitRow(line) {
    let t = line.trim();
    if (t[0] === '|') t = t.slice(1);
    if (t[t.length - 1] === '|') t = t.slice(0, -1);
    return t.split('|').map(c => c.trim());
  }

  function render(src) {
    const lines = String(src == null ? '' : src).replace(/\r\n?/g, '\n').split('\n');
    const out = [];
    let i = 0, para = [], list = null;

    const flushPara = () => { if (para.length) { out.push('<p>' + inline(para.join(' ')) + '</p>'); para = []; } };
    const closeList = () => { if (list) { out.push('</' + list + '>'); list = null; } };

    while (i < lines.length) {
      const line = lines[i];
      const t = line.trim();

      if (!t) { flushPara(); closeList(); i++; continue; }

      let m;
      if ((m = /^(#{1,4})\s+(.*)$/.exec(t))) {
        flushPara(); closeList();
        const lvl = Math.min(4, m[1].length);
        out.push('<h' + lvl + '>' + inline(m[2].replace(/\s*#+\s*$/, '')) + '</h' + lvl + '>');
        i++; continue;
      }
      if (/^(-{3,}|\*{3,}|={3,})$/.test(t)) { flushPara(); closeList(); out.push('<hr>'); i++; continue; }

      if (t[0] === '|' && i + 1 < lines.length && /^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(lines[i + 1].trim())) {
        flushPara(); closeList();
        const head = splitRow(t); i += 2;
        let rows = '';
        while (i < lines.length && lines[i].trim()[0] === '|') {
          rows += '<tr>' + splitRow(lines[i]).map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>'; i++;
        }
        out.push('<div class="tw"><table><thead><tr>' + head.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr></thead><tbody>' + rows + '</tbody></table></div>');
        continue;
      }
      if ((m = /^>\s?(.*)$/.exec(t))) { flushPara(); closeList(); out.push('<blockquote>' + inline(m[1]) + '</blockquote>'); i++; continue; }

      if ((m = /^[-*+]\s+(.*)$/.exec(t))) {
        flushPara(); if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul'; }
        out.push('<li>' + inline(m[1]) + '</li>'); i++; continue;
      }
      if ((m = /^\d+[.)]\s+(.*)$/.exec(t))) {
        flushPara(); if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol'; }
        out.push('<li>' + inline(m[1]) + '</li>'); i++; continue;
      }
      // wrapped continuation of a list item
      if (list && /^\s+/.test(line) && out.length && out[out.length - 1].startsWith('<li>')) {
        out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, ' ' + inline(t) + '</li>'); i++; continue;
      }
      closeList(); para.push(t); i++;
    }
    flushPara(); closeList();
    return out.join('\n');
  }

  return { render: render, esc: esc, inline: inline };
});
