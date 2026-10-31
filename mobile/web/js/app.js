/* app.js - NutriAgent mobile UI. Plain JS, no framework, no network except the optional user-run Ollama server. */
(function () {
  'use strict';
  const Eng = NutriEngine, Ag = NutriAgents, Md = NutriMd;

  // ------------------------------------------------------------------ constants
  const DIETS = ['Omnivore / Standard', 'Vegetarian', 'Vegan', 'Pescatarian', 'Low-Carb / Mediterranean'];
  const ALLERGENS = ['Gluten / Celiac', 'Lactose / Dairy', 'Tree Nuts & Peanuts', 'Shellfish', 'Soybeans', 'Eggs'];
  const ACTIVITY = ['Sedentary', 'Light', 'Moderate', 'Active', 'Very Active'];
  const SAMPLE_QUERIES = [
    'I have prediabetes and high cholesterol, what should I eat?',
    'I have gout and kidney issues, what foods are safe?',
    'What is a healthy breakfast for someone with high blood pressure?',
    'Calculate my BMI: height 175cm, weight 86.5kg, age 52',
  ];
  const SLOTS = [
    ['breakfast', 'Breakfast', 'sunrise'], ['mid_morning', 'Mid-morning', 'cup'], ['lunch', 'Lunch', 'sun'],
    ['snack', 'Evening snack', 'leaf'], ['dinner', 'Dinner', 'utensils'], ['bedtime', 'Bedtime', 'moon'],
  ];
  const STAGES = [
    ['Profile', 'Reading demographics and biomarkers'], ['Rules engine', 'BMR, TDEE, macros and food constraints'],
    ['Analysis', 'Risk stratification of your results'], ['Nutrition', 'Building the 7-day plan'], ['Audit gate', 'Safety checks and doctor brief'],
  ];
  const RTABS = [['overview', 'Overview'], ['biomarkers', 'Biomarkers'], ['plan', 'Meal plan'], ['brief', 'Doctor brief'], ['ask', 'Ask'], ['export', 'Export']];
  const DISCLAIMER = 'NutriAgent gives general nutrition information computed from the numbers you provide. It is not a medical device and does not diagnose or treat. Always review results and any diet change with your doctor or a registered dietitian.';

  const ICON = {
    home: 'M3 11l9-8 9 8M5 10v10h14V10M10 20v-6h4v6',
    report: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h6',
    chat: 'M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z',
    settings: 'M4 7h9M17 7h3M4 17h3M11 17h9M13 7a2 2 0 1 0 4 0a2 2 0 1 0-4 0M7 17a2 2 0 1 0 4 0a2 2 0 1 0-4 0',
    upload: 'M12 16V4M7 9l5-5 5 5M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3',
    flask: 'M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 15h8',
    shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4',
    send: 'M22 2L11 13M22 2l-7 20-4-9-9-4z', down: 'M6 9l6 6 6-6', check: 'M20 6L9 17l-5-5', x: 'M18 6L6 18M6 6l12 12',
    share: 'M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v13', copy: 'M9 9h10v10H9zM5 15V5h10',
    sunrise: 'M17 18a5 5 0 0 0-10 0M12 2v7M4.2 10.2l1.4 1.4M1 18h2M21 18h2M18.4 11.6l1.4-1.4M23 22H1M8 6l4-4 4 4',
    cup: 'M18 8h1a4 4 0 0 1 0 8h-1M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4zM6 1v3M10 1v3M14 1v3',
    sun: 'M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
    leaf: 'M20 4C10 4 4 10 4 18c8 0 16-5 16-14zM4 20c3-6 7-9 11-11',
    utensils: 'M3 2v7a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V2M7 2v20M21 15V2a5 5 0 0 0-5 5v6a2 2 0 0 0 2 2h3zm0 0v7',
    moon: 'M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z', trash: 'M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14',
    bolt: 'M13 2L4 14h7l-1 8 9-12h-7z', lock: 'M6 11h12v9H6zM9 11V8a3 3 0 0 1 6 0v3',
  };
  const ico = (n, cls) => svg('0 0 24 24', ICON[n], cls);
  function svg(vb, d, cls) {
    const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('viewBox', vb); s.setAttribute('aria-hidden', 'true');
    if (cls) s.setAttribute('class', cls);
    if (d) { const p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.setAttribute('d', d); s.appendChild(p); }
    return s;
  }

  // ------------------------------------------------------------------ tiny DOM helper
  function h(tag, props) {
    const el = document.createElement(tag);
    const kids = Array.prototype.slice.call(arguments, 2);
    if (props) for (const k in props) {
      const v = props[k];
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k === 'html') el.innerHTML = v;
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
      else if (k === 'value') el.value = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    (function add(list) {
      list.forEach(c => {
        if (c == null || c === false) return;
        if (Array.isArray(c)) add(c);
        else el.appendChild(typeof c === 'object' ? c : document.createTextNode(String(c)));
      });
    })(kids);
    return el;
  }
  const $ = s => document.querySelector(s);
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const fmt = n => (n == null || isNaN(n) ? '-' : Number(n).toLocaleString('en-US'));
  const prose = (md, extra) => h('div', { class: 'prose ' + (extra || ''), html: Md.render(md) });
  const esc = Md.esc;

  // ------------------------------------------------------------------ state + storage
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* ignore */ } },
  };
  const DEFAULTS = { aiEnabled: false, url: '', model: 'qwen2.5:7b', timeout: 600, diet: DIETS[0], allergies: [], activity: 'Light', theme: 'system' };
  const S = {
    settings: Object.assign({}, DEFAULTS, store.get('na.settings', {})),
    tab: 'home', rtab: 'overview', day: 0, bmFilter: 'all',
    report: store.get('na.report', null),
    ai: { state: 'off', message: '', models: [] },
    ask: null, askBusy: false, signal: null, scroll: {},
  };
  const V = {};
  const saveSettings = () => store.set('na.settings', S.settings);
  const saveReport = () => { if (S.report && !store.set('na.report', S.report)) toast('Could not save the report on this device'); };
  const llm = () => new Ag.Llm({ url: S.settings.url, model: S.settings.model, timeoutSec: S.settings.timeout, enabled: S.settings.aiEnabled });

  // ------------------------------------------------------------------ toast, theme
  let toastT;
  function toast(msg) {
    const t = $('#toast'); t.textContent = msg; t.classList.add('on');
    clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('on'), 2600);
  }
  function applyTheme() {
    const pref = S.settings.theme;
    const sysDark = () => { try { if (window.Native && Native.isNight) return !!Native.isNight(); } catch (e) { /* fall through */ } return !!(window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches); };
    const dark = pref === 'dark' || (pref === 'system' && sysDark());
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    const bg = dark ? '#0A1120' : '#F4F7FB';
    const m = document.querySelector('meta[name=theme-color]'); if (m) m.content = bg;
    try { if (window.Native && Native.theme) Native.theme(dark, bg); } catch (e) { /* ignore */ }
  }

  // ------------------------------------------------------------------ small visual components
  function pill(text, kind, live) { return h('span', { class: 'pill ' + (kind || '') + (live ? ' live' : '') }, h('i'), text); }
  function statusKind(st) { return /Critical/.test(st) ? 'crit' : /High/.test(st) ? 'warn' : /Low/.test(st) ? 'low' : 'ok'; }
  function sevKind(s) { return s === 'High' ? 'crit' : s === 'Mild' ? 'low' : 'warn'; }
  const STATUS_COLOR = { crit: 'var(--crit)', warn: 'var(--warn)', low: 'var(--low)', ok: 'var(--ok)' };

  function logo(sz) {
    const w = h('span', { html: '<svg viewBox="0 0 108 108" width="' + sz + '" height="' + sz + '" style="border-radius:' + Math.round(sz * .3) + 'px;display:block"><rect width="108" height="108" fill="#0F172A"/><path fill="#34D399" d="M54 30C72 32 80 48 76 66C60 70 40 64 36 46C36 38 44 31 54 30Z"/><path stroke="#0F172A" stroke-width="3" stroke-linecap="round" fill="none" d="M42 64C50 56 58 48 68 40"/><path fill="#38BDF8" d="M50 72h8v6h6v8h-6v6h-8v-6h-6v-8h6z"/></svg>' });
    return w;
  }

  function donut(parts, size, stroke, top, bottom) {
    const r = (size - stroke) / 2, c = 2 * Math.PI * r, tot = parts.reduce((a, p) => a + p.v, 0) || 1;
    let off = 0;
    const ns = 'http://www.w3.org/2000/svg';
    const s = document.createElementNS(ns, 'svg'); s.setAttribute('viewBox', '0 0 ' + size + ' ' + size); s.setAttribute('width', size); s.setAttribute('height', size); s.setAttribute('class', 'donut');
    const bg = document.createElementNS(ns, 'circle');
    ['cx', 'cy'].forEach(a => bg.setAttribute(a, size / 2)); bg.setAttribute('r', r); bg.setAttribute('fill', 'none'); bg.setAttribute('stroke', 'var(--surface-2)'); bg.setAttribute('stroke-width', stroke); s.appendChild(bg);
    parts.forEach(p => {
      const len = (p.v / tot) * c, k = document.createElementNS(ns, 'circle');
      ['cx', 'cy'].forEach(a => k.setAttribute(a, size / 2)); k.setAttribute('r', r); k.setAttribute('fill', 'none'); k.setAttribute('stroke', p.color); k.setAttribute('stroke-width', stroke);
      k.setAttribute('stroke-dasharray', Math.max(0, len - 3) + ' ' + (c - Math.max(0, len - 3))); k.setAttribute('stroke-dashoffset', -off); k.setAttribute('transform', 'rotate(-90 ' + size / 2 + ' ' + size / 2 + ')'); k.setAttribute('stroke-linecap', 'round');
      off += len; s.appendChild(k);
    });
    const t1 = document.createElementNS(ns, 'text'); t1.setAttribute('x', size / 2); t1.setAttribute('y', size / 2 + 2); t1.setAttribute('text-anchor', 'middle'); t1.setAttribute('font-size', size * .2); t1.setAttribute('font-weight', 800); t1.setAttribute('fill', 'var(--text)'); t1.textContent = top; s.appendChild(t1);
    const t2 = document.createElementNS(ns, 'text'); t2.setAttribute('x', size / 2); t2.setAttribute('y', size / 2 + size * .15); t2.setAttribute('text-anchor', 'middle'); t2.setAttribute('font-size', size * .085); t2.setAttribute('font-weight', 700); t2.setAttribute('fill', 'var(--muted)'); t2.textContent = bottom; s.appendChild(t2);
    return s;
  }

  function ring(score, color) {
    const sz = 92, st = 9, r = (sz - st) / 2, c = 2 * Math.PI * r, ns = 'http://www.w3.org/2000/svg';
    const s = document.createElementNS(ns, 'svg'); s.setAttribute('viewBox', '0 0 ' + sz + ' ' + sz); s.setAttribute('width', sz); s.setAttribute('height', sz);
    const a = document.createElementNS(ns, 'circle'); [['cx', sz / 2], ['cy', sz / 2], ['r', r], ['fill', 'none'], ['stroke', 'var(--surface-2)'], ['stroke-width', st]].forEach(x => a.setAttribute(x[0], x[1])); s.appendChild(a);
    const b = document.createElementNS(ns, 'circle'); [['cx', sz / 2], ['cy', sz / 2], ['r', r], ['fill', 'none'], ['stroke', color], ['stroke-width', st], ['stroke-linecap', 'round'], ['stroke-dasharray', (c * score / 100) + ' ' + c]].forEach(x => b.setAttribute(x[0], x[1])); s.appendChild(b);
    return h('div', { class: 'ring' }, s, h('b', { text: String(score) }));
  }

  function accordion(title, body, open) {
    const box = h('div', { class: 'acc' + (open ? ' open' : '') });
    const btn = h('button', { onclick: () => box.classList.toggle('open') }, h('span', { text: title }), ico('down'));
    box.appendChild(btn); box.appendChild(h('div', null, body));
    return box;
  }

  function aiBadge(src, err) {
    return h('span', { class: 'aibadge ' + (src === 'ai' ? 'ai' : '') }, src === 'ai' ? '✦ AI · ' + S.settings.model : 'Built-in engine' + (err ? ' · AI unavailable' : ''));
  }

  // ------------------------------------------------------------------ sheet / overlay plumbing
  const layer = () => $('#layer');
  function openSheet(content) {
    closeSheet(true);
    const scrim = h('div', { class: 'scrim', id: 'scrim', onclick: () => closeSheet() });
    const sh = h('div', { class: 'sheet', id: 'sheet', role: 'dialog', 'aria-modal': 'true' }, h('div', { class: 'grab' }), h('div', { class: 'sheet-body' }, content));
    layer().append(scrim, sh);
    requestAnimationFrame(() => requestAnimationFrame(() => { scrim.classList.add('on'); sh.classList.add('on'); }));
  }
  function closeSheet(now) {
    const sh = $('#sheet'), sc = $('#scrim');
    if (!sh) return false;
    if (now) { sh.remove(); sc && sc.remove(); return true; }
    sh.classList.remove('on'); sc && sc.classList.remove('on');
    setTimeout(() => { sh.remove(); sc && sc.remove(); }, 320);
    return true;
  }

  // ------------------------------------------------------------------ navigation
  function renderNav() {
    const nav = $('#nav'); nav.innerHTML = '';
    [['home', 'Home', 'home'], ['report', 'Report', 'report'], ['ask', 'Ask', 'chat'], ['settings', 'Settings', 'settings']].forEach(t => {
      const b = h('button', { class: S.tab === t[0] ? 'on' : '', onclick: () => go(t[0]), 'aria-label': t[1] },
        h('span', { class: t[0] === 'report' && S.report ? 'dot' : '' }, ico(t[2])), t[1]);
      nav.appendChild(b);
    });
  }
  function go(tab) {
    const v = $('#view'); S.scroll[S.tab] = v.scrollTop;
    S.tab = tab; render();
    v.scrollTop = S.scroll[tab] || 0;
  }
  function render() {
    renderNav();
    const v = $('#view'); v.innerHTML = '';
    const page = ({ home: viewHome, report: () => V.report(), ask: () => V.ask(), settings: () => V.settings() })[S.tab]();
    v.appendChild(page);
  }

  window.__onBack = function () {
    if ($('#pipeline')) { cancelRun(); return 'handled'; }
    if ($('#sheet')) { closeSheet(); return 'handled'; }
    if (S.tab === 'report' && S.rtab !== 'overview') { S.rtab = 'overview'; render(); return 'handled'; }
    if (S.tab !== 'home') { go('home'); return 'handled'; }
    return 'exit';
  };

  // ------------------------------------------------------------------ AI status
  async function refreshAi(silent) {
    if (!S.settings.aiEnabled || !S.settings.url) { S.ai = { state: 'off', message: '', models: [] }; if (S.tab === 'settings' || S.tab === 'home') render(); return S.ai; }
    S.ai = { state: 'checking', message: 'Checking...', models: [] };
    if (!silent) render();
    S.ai = await llm().check();
    if (S.tab === 'settings' || S.tab === 'home') render();
    return S.ai;
  }
  function aiPill() {
    const st = S.ai.state;
    const map = { online: ['AI connected', 'ok'], nomodel: ['Model missing', 'warn'], offline: ['AI unreachable', 'warn'], checking: ['Checking AI', 'low'], off: ['On-device engine', ''] };
    const m = map[st] || map.off;
    return h('button', { onclick: () => go('settings'), 'aria-label': 'AI status' }, pill(m[0], m[1], st === 'checking'));
  }
  const aiLive = () => S.settings.aiEnabled && S.ai.state === 'online';

  // ------------------------------------------------------------------ HOME
  function viewHome() {
    const root = h('div');
    root.appendChild(h('div', { class: 'topbar' }, h('div', { class: 'brand' }, logo(34), 'NutriAgent'), aiPill()));
    const page = h('div', { class: 'page' });
    const hero = h('div', { class: 'hero' },
      h('h1', { text: 'Turn your blood test into a plan you can follow.' }),
      h('p', { text: 'Upload a lab report PDF. Get your risk flags, exact calorie and macro targets, and a 7-day Indian meal plan built from NIN food tables.' }),
      h('div', { class: 'actions' },
        h('button', { class: 'btn white block', onclick: pickPdf }, ico('upload'), 'Upload lab report (PDF)'),
        h('button', { class: 'btn block', style: { background: 'rgba(255,255,255,.14)', color: '#fff' }, onclick: () => startIntake(window.NUTRI_SAMPLE_REPORT, 'Sample report')}, ico('flask'), 'Try the sample report')),
      h('div', { class: 'trust' }, ...['Your report stays on this phone', 'Works offline', 'No account'].map(t => h('span', null, ico('check'), t))));
    page.appendChild(hero);

    if (S.report) {
      const r = S.report, nflags = (r.profile.clinical_flags || []).length;
      page.appendChild(h('div', { class: 'section' }, h('h3', { text: 'Continue' }),
        h('button', { class: 'card resume', onclick: () => { S.rtab = 'overview'; go('report'); } },
          h('div', { class: 'ic' }, ico('report')),
          h('div', { style: { flex: 1, minWidth: 0 } }, h('b', { text: r.sourceName || 'Your report' }), h('div', { class: 'muted', style: { fontSize: '13px' }, text: dateLabel(r.createdAt) + ' · ' + r.protocol.macros.calories + ' kcal · ' + nflags + ' flag' + (nflags === 1 ? '' : 's') })),
          h('span', { class: 'muted', text: '›' }))));
    }

    page.appendChild(h('div', { class: 'section' }, h('h3', { text: 'How it works' }),
      h('div', { class: 'steps' },
        h('div', { class: 'step' }, h('b', { text: '1' }), h('strong', { text: 'Read' }), h('span', { text: '25+ biomarkers read from your PDF' })),
        h('div', { class: 'step' }, h('b', { text: '2' }), h('strong', { text: 'Calculate' }), h('span', { text: 'Mifflin-St Jeor energy and clinical rules' })),
        h('div', { class: 'step' }, h('b', { text: '3' }), h('strong', { text: 'Plan' }), h('span', { text: '7 days of meals with safety checks' })))));

    const input = h('input', { class: 'input', placeholder: 'e.g. I have gout, what can I eat?', enterkeyhint: 'send', 'aria-label': 'Ask a nutrition question' });
    const send = () => { const q = input.value.trim(); if (q) { go('ask'); V.runAsk(q); } };
    input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
    page.appendChild(h('div', { class: 'section' }, h('h3', { text: 'No report? Just ask' }),
      h('div', { class: 'card' },
        h('div', { class: 'note', text: 'Describe your conditions, age, height and weight in a sentence. The same clinical rules run on what you type.' }),
        h('div', { class: 'ask-box' }, input, h('button', { class: 'send', onclick: send, 'aria-label': 'Ask' }, ico('send'))),
        h('div', { class: 'chips', style: { marginTop: '12px' } }, SAMPLE_QUERIES.slice(0, 3).map(q => h('button', { class: 'chip', onclick: () => { go('ask'); V.runAsk(q); } }, q))))));

    page.appendChild(h('p', { class: 'disclaimer', text: DISCLAIMER }));
    root.appendChild(page);
    return root;
  }
  const dateLabel = iso => { try { return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }); } catch (e) { return ''; } };

  // ------------------------------------------------------------------ PDF -> intake
  function pickPdf() { const f = $('#file'); f.value = ''; f.click(); }
  async function onFile(ev) {
    const file = ev.target.files && ev.target.files[0];
    if (!file) return;
    openSheet(h('div', { class: 'empty' }, h('div', { class: 'ic' }, h('span', { class: 'spin' })), h('h3', { text: 'Reading your PDF' }), h('p', { text: file.name })));
    try {
      const buf = await file.arrayBuffer();
      const res = await NutriPdf.extractText(buf, { workerSrc: 'vendor/pdfjs/pdf.worker.min.js' });
      if (res.scanned || !res.text) return intakeError('This PDF has no text layer', 'It looks like a scanned image. Export the report as a text-based PDF from the lab portal, or photograph-to-PDF apps with OCR, then try again.');
      closeSheet(true); startIntake(res.text, file.name);
    } catch (e) {
      if (e && e.code === 'PASSWORD') intakeError('Password-protected PDF', 'Remove the password in your PDF viewer, then upload it again.');
      else intakeError('Could not read this file', 'Make sure it is a valid PDF. (' + ((e && e.message) || e) + ')');
    }
  }
  function intakeError(title, msg) {
    openSheet(h('div', { class: 'empty' }, h('div', { class: 'ic' }, ico('x')), h('h3', { text: title }), h('p', { text: msg }),
      h('div', { class: 'stack', style: { marginTop: '18px' } }, h('button', { class: 'btn primary block', onclick: () => { closeSheet(true); pickPdf(); } }, 'Choose another PDF'),
        h('button', { class: 'btn ghost block', onclick: () => { closeSheet(); go('ask'); } }, 'Describe my health instead'))));
  }

  function startIntake(rawText, name) {
    const probe = Eng.buildHealthProfile(rawText), d = probe.demographics || {}, v = probe.validation || {};
    const nMarkers = Object.keys(probe.biomarkers || {}).length;
    if (!v.valid && nMarkers === 0) return intakeError('This does not look like a lab report', (v.reason || 'No medical markers found') + ' You can describe your health in a sentence instead.');

    const form = {
      name: d.name || 'Patient', age: +d.age || 45, gender: ['Male', 'Female', 'Other'].indexOf(d.gender) >= 0 ? d.gender : 'Male',
      weight: d.weight_kg || null, height: d.height_cm || null,
      diet: S.settings.diet, allergies: S.settings.allergies.slice(), activity: S.settings.activity,
    };
    const bmiOut = h('b', { class: 'num' });
    const upd = () => {
      const wt = +form.weight, ht = +form.height;
      bmiOut.textContent = wt > 0 && ht > 0 ? (Math.round(wt / ((ht / 100) ** 2) * 10) / 10).toFixed(1) + ' kg/m²' : '—';
    };
    const num = (key, label, step, ph) => {
      const i = h('input', { class: 'input num', type: 'number', inputmode: 'decimal', step: step, placeholder: ph, value: form[key] == null ? '' : form[key], 'aria-label': label });
      i.addEventListener('input', () => { form[key] = i.value === '' ? null : +i.value; upd(); });
      return h('label', { class: 'field' }, h('span', { text: label }), i);
    };
    const nameIn = h('input', { class: 'input', value: form.name, 'aria-label': 'Name' }); nameIn.addEventListener('input', () => { form.name = nameIn.value; });
    const sex = h('div', { class: 'seg' }); const drawSex = () => { sex.innerHTML = ''; ['Male', 'Female', 'Other'].forEach(g => sex.appendChild(h('button', { class: form.gender === g ? 'on' : '', onclick: () => { form.gender = g; drawSex(); } }, g))); }; drawSex();
    const dietSel = h('select', { class: 'input', 'aria-label': 'Diet' }, DIETS.map(x => h('option', { value: x, selected: x === form.diet }, x))); dietSel.addEventListener('change', () => { form.diet = dietSel.value; });
    const alg = h('div', { class: 'chips' }); const drawAlg = () => { alg.innerHTML = ''; ALLERGENS.forEach(a => alg.appendChild(h('button', { class: 'chip' + (form.allergies.indexOf(a) >= 0 ? ' on' : ''), onclick: () => { const i = form.allergies.indexOf(a); i >= 0 ? form.allergies.splice(i, 1) : form.allergies.push(a); drawAlg(); } }, a))); }; drawAlg();
    const act = h('div', { class: 'chips' }); const drawAct = () => { act.innerHTML = ''; ACTIVITY.forEach(a => act.appendChild(h('button', { class: 'chip' + (form.activity === a ? ' on' : ''), onclick: () => { form.activity = a; drawAct(); } }, a))); }; drawAct();
    upd();

    const banner = h('div', { class: 'callout', style: { background: 'var(--ok-soft)', borderColor: 'var(--ok-line)', color: 'var(--ok-ink)' } },
      h('b', { text: v.valid ? 'Lab report recognised' : 'Partial match' }),
      h('p', { text: nMarkers + ' biomarkers read' + (d.bp_string ? ' · BP ' + d.bp_string : '') + (v.detected_sections && v.detected_sections.length ? ' · ' + v.detected_sections.slice(0, 3).join(', ') : '') }));
    const go1 = h('button', { class: 'btn primary block', onclick: () => {
      if (!(form.age >= 1 && form.age <= 120)) return toast('Please enter a valid age');
      if (!(form.weight >= 20 && form.weight <= 300)) return toast('Please enter a weight between 20 and 300 kg');
      if (!(form.height >= 80 && form.height <= 250)) return toast('Please enter a height between 80 and 250 cm');
      S.settings.diet = form.diet; S.settings.allergies = form.allergies.slice(); S.settings.activity = form.activity; saveSettings();
      closeSheet(true); runPipeline(rawText, name, form);
    } }, ico('bolt'), 'Analyse my report');

    openSheet(h('div', { class: 'stack' },
      h('div', null, h('h2', { class: 'title-lg', text: 'Check your details' }), h('p', { class: 'muted', style: { marginTop: '4px', fontSize: '13.5px' }, text: 'We pre-filled what we found in the report. Fix anything that looks off.' })),
      banner,
      h('label', { class: 'field' }, h('span', { text: 'Name' }), nameIn),
      h('div', { class: 'field' }, h('span', { text: 'Sex' }), sex),
      h('div', { class: 'grid3' }, num('age', 'Age', '1', 'years'), num('weight', 'Weight kg', '0.5', 'kg'), num('height', 'Height cm', '1', 'cm')),
      h('div', { class: 'row between card', style: { padding: '10px 14px' } }, h('span', { class: 'muted', text: 'Calculated BMI' }), bmiOut),
      h('label', { class: 'field' }, h('span', { text: 'Diet' }), dietSel),
      h('div', { class: 'field' }, h('span', { text: 'Allergens to exclude' }), alg),
      h('div', { class: 'field' }, h('span', { text: 'Activity level' }), act),
      go1));
  }

  // ------------------------------------------------------------------ PIPELINE
  let runCtl = null;
  function cancelRun() { if (runCtl) { runCtl.skipAI = true; runCtl.signal.cancel(); } }

  async function runPipeline(rawText, sourceName, form) {
    const ctl = runCtl = { skipAI: false, signal: Ag.makeSignal(), done: [], dur: {}, active: 0, t0: Date.now(), msg: '' };
    const useAI = aiLive();
    const ov = h('div', { class: 'overlay', id: 'pipeline' });
    layer().appendChild(ov);
    const skipBtn = h('button', { class: 'btn ghost block', onclick: () => { ctl.skipAI = true; ctl.signal.cancel(); toast('Using the built-in engine for the remaining steps'); } }, 'Skip AI, use built-in engine');
    function paint() {
      const flow = h('div', { class: 'flow' });
      STAGES.forEach((s, i) => {
        const cls = ctl.done.indexOf(i) >= 0 ? 'done' : i === ctl.active ? 'active' : '';
        flow.appendChild(h('div', { class: 'fnode ' + cls }, h('div', { class: 'fdot' }, cls === 'done' ? '✓' : String(i + 1)), h('div', { class: 'flabel', text: s[0] })));
        if (i < STAGES.length - 1) flow.appendChild(h('div', { class: 'fedge ' + (ctl.done.indexOf(i) >= 0 && ctl.done.indexOf(i + 1) >= 0 ? 'done' : ctl.done.indexOf(i) >= 0 && ctl.active === i + 1 ? 'active' : '') }));
      });
      const stages = STAGES.map((s, i) => {
        const done = ctl.done.indexOf(i) >= 0, act = i === ctl.active;
        const el = ((i >= 2 && useAI && !ctl.skipAI) ? ' · AI' : '');
        return h('div', { class: 'stage ' + (done ? 'done' : act ? 'active' : '') },
          h('div', { class: 'sn' }, done ? '✓' : String(i + 1)), h('div', { class: 'st' }, h('b', { text: s[0] + (i >= 2 ? el : '') }), h('span', { text: s[1] })),
          h('div', { class: 'tm', text: done ? (ctl.dur[i] / 1000).toFixed(1) + 's' : act ? ((Date.now() - ctl.stageT0) / 1000).toFixed(0) + 's' : '' }));
      });
      ov.innerHTML = '';
      ov.append(h('div', { class: 'pipe' }, h('h2', { text: 'Analysing your report' }),
        h('p', { class: 'sub', text: useAI && !ctl.skipAI ? 'AI model ' + S.settings.model + ' is writing parts of this. Local models can take a minute or two per step.' : 'Running the on-device clinical engine.' }),
        flow, ...stages, ctl.active >= 0 && ctl.active < 5 ? h('div', { class: 'livebar' }) : null,
        h('p', { class: 'note', style: { marginTop: '12px' }, text: ctl.msg })),
        h('div', { class: 'pipe-foot' }, useAI && !ctl.skipAI ? skipBtn : h('button', { class: 'btn ghost block', onclick: cancelPipelineUi }, 'Cancel')));
    }
    function cancelPipelineUi() { ctl.cancelled = true; ctl.signal.cancel(); }
    const tick = setInterval(paint, 500);
    const stage = async (i, msg, fn, min) => {
      ctl.active = i; ctl.msg = msg; ctl.stageT0 = Date.now(); paint();
      const [r] = await Promise.all([fn(), sleep(min || 0)]);
      if (ctl.cancelled) throw new Error('cancelled');
      ctl.dur[i] = Date.now() - ctl.stageT0; ctl.done.push(i); paint(); return r;
    };
    const safe = async (fn, fallback) => { try { return await fn(); } catch (e) { if (ctl.cancelled) throw e; if (ctl.skipAI) return fallback(); throw e; } };

    try {
      const profile = await stage(0, 'Extracting demographics and biomarker values...', async () => {
        const p = Eng.buildHealthProfile(rawText);
        Object.assign(p.demographics, {
          name: form.name, age: form.age, gender: form.gender, weight_kg: form.weight, height_cm: form.height,
          bmi: Math.round(form.weight / ((form.height / 100) ** 2) * 10) / 10,
          dietary_preference: form.diet, allergies: form.allergies, activity_level: form.activity,
        });
        if (!p.demographics.bp_string) p.demographics.bp_string = 'Not found in report';
        return p;
      }, 350);
      const protocol = await stage(1, 'Computing BMR, TDEE and the biomarker-specific macro split...', async () => Eng.computeProtocol(profile), 450);
      const audit = Eng.checkConstraintCompliance(protocol);
      audit.scope = 'Constraint check run on this device: calories, contraindicated foods, protocol coverage, sourced calories';
      const L = () => (ctl.skipAI || !useAI ? null : llm());

      const analysis = await stage(2, useAI ? 'Asking the AI for a risk stratification...' : 'Writing the analysis from your numbers...',
        () => safe(() => Ag.runAnalysis(L(), profile, protocol, ctl.signal), () => ({ text: Ag.builtinAnalysis(profile, protocol), source: 'builtin' })), useAI ? 0 : 400);
      const diet = await stage(3, useAI ? 'Asking the AI for dietitian notes...' : 'Assembling the diet strategy...',
        () => safe(() => Ag.runNutrition(L(), profile, analysis.text, protocol, ctl.signal), () => ({ text: Ag.builtinDietNotes(protocol), source: 'builtin' })), useAI ? 0 : 400);
      const evaluation = await stage(4, useAI ? 'Asking the AI to audit the plan...' : 'Running the safety checks and drafting the doctor brief...',
        () => safe(() => Ag.runEvaluation(L(), profile, analysis.text, diet.text, protocol, audit, ctl.signal), () => ({ text: Ag.builtinEvaluation(profile, protocol, audit), source: 'builtin', aiScore: null })), useAI ? 0 : 400);

      S.report = { sourceName: sourceName, createdAt: new Date().toISOString(), profile, protocol, audit, analysis, diet, evaluation, chat: [], model: S.settings.model };
      saveReport();
      S.rtab = 'overview'; S.day = 0; S.tab = 'report';
      clearInterval(tick); ov.remove(); runCtl = null; render();
      $('#view').scrollTop = 0;
      const dl = ctl.dur[2] + ctl.dur[3] + ctl.dur[4];
      toast('Done' + (analysis.error || diet.error || evaluation.error ? ' - AI was unreachable, used the built-in engine' : ''));
      void dl;
    } catch (e) {
      clearInterval(tick); ov.remove(); runCtl = null;
      if (!(e && e.message === 'cancelled')) { console.error(e); toast('Something went wrong: ' + (e && e.message || e)); }
    }
  }

  window.NutriApp = { V, S, go, render, toast, h, ico, prose, openSheet, closeSheet, pill, donut, ring, accordion, aiBadge, aiLive, llm, refreshAi, saveSettings, saveReport, store, fmt, esc, dateLabel, startIntake, pickPdf, runPipeline, applyTheme, statusKind, sevKind, STATUS_COLOR, SLOTS, RTABS, DIETS, ALLERGENS, ACTIVITY, SAMPLE_QUERIES, DISCLAIMER, aiPill, logo, sleep, onFile, ICON };
})();
