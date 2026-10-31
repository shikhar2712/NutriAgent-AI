/* views.js - results, Ask and Settings screens + bootstrap. Depends on app.js (window.NutriApp). */
(function () {
  'use strict';
  const A = NutriApp, V = A.V, S = A.S, h = A.h, ico = A.ico, prose = A.prose, fmt = A.fmt, toast = A.toast;
  const Eng = NutriEngine, Ag = NutriAgents;

  const sectionTitle = (t, right) => h('h3', null, h('span', { text: t }), right || null);

  // =================================================================== REPORT
  V.report = function () {
    const r = S.report;
    if (!r) {
      return h('div', { class: 'page', style: { paddingTop: 'calc(var(--sat) + 60px)' } }, h('div', { class: 'empty' },
        h('div', { class: 'ic' }, ico('report')), h('h3', { text: 'No report yet' }), h('p', { text: 'Upload a lab report PDF, or try the sample, to see your flags, targets and 7-day plan here.' }),
        h('div', { class: 'stack', style: { marginTop: '18px' } },
          h('button', { class: 'btn primary block', onclick: A.pickPdf }, ico('upload'), 'Upload lab report'),
          h('button', { class: 'btn ghost block', onclick: () => A.startIntake(window.NUTRI_SAMPLE_REPORT, 'Sample report') }, ico('flask'), 'Try the sample report'))));
    }
    const d = r.profile.demographics, m = r.protocol.macros, flags = r.profile.clinical_flags || [];
    const root = h('div', { class: 'page' });
    root.appendChild(h('div', { class: 'rhead', style: { padding: 'calc(var(--sat) + 14px) 0 4px' } },
      h('div', { class: 'row between' }, h('div', { style: { minWidth: 0 } },
        h('h1', { class: 'title-lg', text: d.name || 'Patient' }),
        h('div', { class: 'muted', style: { fontSize: '13px', marginTop: '2px' }, text: [d.age + ' y', d.gender, 'BMI ' + d.bmi, A.dateLabel(r.createdAt)].join(' · ') })),
        h('button', { class: 'btn ghost sm', onclick: () => A.go('home') }, 'New'))));
    const sc = r.audit.score;
    root.appendChild(h('div', { class: 'kpis', style: { marginTop: '8px' } },
      kpi('Daily energy', fmt(m.calories), 'kcal', 'BMR ' + r.protocol.energy.bmr + ' · TDEE ' + r.protocol.energy.tdee),
      kpi('Carb / Prot / Fat', m.carbs.percentage + '/' + m.protein.percentage + '/' + m.fat.percentage, '%', m.protein.grams + ' g protein daily'),
      kpi('Flags', String(flags.length), flags.length === 1 ? 'flag' : 'flags', flags.length ? flags[0].condition.slice(0, 26) : 'All clear', flags.length ? 'var(--crit)' : 'var(--ok)'),
      kpi('Plan self-check', String(sc), '/100', sc === 100 ? 'All checks passed' : 'Review flagged rows', sc >= 80 ? 'var(--ok)' : 'var(--warn)')));
    const tabs = h('div', { class: 'rtabs' }, A.RTABS.map(t => h('button', { class: 'rtab' + (S.rtab === t[0] ? ' on' : ''), onclick: () => { S.rtab = t[0]; A.render(); const v = document.querySelector('#view'), bar = v.querySelector('.rtabs'); if (bar && v.scrollTop > bar.offsetTop) v.scrollTop = bar.offsetTop; } }, t[1])));
    root.appendChild(tabs);
    const body = h('div', { style: { paddingTop: '14px' } }, { overview: tabOverview, biomarkers: tabBiomarkers, plan: tabPlan, brief: tabBrief, ask: tabAsk, export: tabExport }[S.rtab](r));
    root.appendChild(body);
    root.appendChild(h('p', { class: 'disclaimer', text: A.DISCLAIMER }));
    requestAnimationFrame(() => { const on = tabs.querySelector('.on'); if (on) on.scrollIntoView({ inline: 'center', block: 'nearest' }); });
    return root;
  };
  function kpi(l, v, unit, s, color) {
    return h('div', { class: 'kpi' }, h('div', { class: 'l', text: l }), h('div', { class: 'v', style: color ? { color } : null }, v, unit ? h('small', { text: unit }) : null), h('div', { class: 's', text: s }));
  }

  // ------------------------------------------------------------------- overview
  function tabOverview(r) {
    const p = r.protocol, m = p.macros, mi = p.micronutrient_targets, flags = r.profile.clinical_flags || [];
    const out = h('div');
    out.appendChild(h('div', { class: 'callout' }, h('b', { text: 'What your results mean' }), ...(p.plain_summary || []).map(t => h('p', { text: t }))));

    out.appendChild(h('div', { class: 'section' }, sectionTitle('Health indicators'),
      flags.length ? flags.map(f => h('div', { class: 'organ' },
        h('div', { class: 'oh' }, h('span', { class: 'ot', text: f.organ || 'General metabolism' }), A.pill(String(f.severity).toUpperCase(), A.sevKind(f.severity))),
        h('h4', { text: f.condition }), h('p', { text: f.plain_meaning || '' }),
        f.marker ? h('p', { class: 'mono', style: { fontSize: '12px', color: 'var(--faint)' }, text: f.marker }) : null,
        f.action_tip ? h('div', { class: 'act' }, h('b', { text: 'Action: ' }), f.action_tip) : null))
        : h('div', { class: 'good' }, ico('check'), 'No clinical flags were raised from this report.')));

    const legend = h('div', { class: 'legend' }, [['Carbohydrate', m.carbs, 'var(--c-carb)'], ['Protein', m.protein, 'var(--c-protein)'], ['Fat', m.fat, 'var(--c-fat)']].map(x =>
      h('div', { class: 'lg' }, h('i', { style: { background: x[2] } }), x[0], h('b', { text: x[1].grams + ' g · ' + x[1].percentage + '%' }))));
    out.appendChild(h('div', { class: 'section' }, sectionTitle('Daily targets'), h('div', { class: 'card' },
      h('div', { class: 'row', style: { gap: '18px' } },
        A.donut([{ v: m.carbs.calories, color: 'var(--c-carb)' }, { v: m.protein.calories, color: 'var(--c-protein)' }, { v: m.fat.calories, color: 'var(--c-fat)' }], 132, 16, fmt(m.calories), 'kcal / day'), legend),
      h('div', { class: 'statrow' },
        h('div', { class: 'stat' }, h('b', { text: '≥ ' + mi.fiber_min_g + ' g' }), h('span', { text: 'Fibre' })),
        h('div', { class: 'stat' }, h('b', { text: '< ' + fmt(mi.sodium_max_mg) + ' mg' }), h('span', { text: 'Sodium' })),
        h('div', { class: 'stat' }, h('b', { text: mi.water_intake_liters + ' L' }), h('span', { text: 'Water' }))),
      h('p', { class: 'note', style: { marginTop: '12px' }, text: r.protocol.energy.goal + ' · Mifflin-St Jeor, ' + (r.protocol.energy.activity_level || 'light').toString().toLowerCase() + ' activity.' }))));

    out.appendChild(h('div', { class: 'section' }, sectionTitle('Protocols applied'),
      h('div', { class: 'chips' }, (p.protocols || []).map(x => h('span', { class: 'chip tag on', text: x })))));
    if ((p.clinical_constraints || []).length) out.appendChild(h('div', { class: 'section' }, A.accordion('Clinical constraints (' + p.clinical_constraints.length + ')', h('ul', { class: 'prose', style: { paddingLeft: '20px', margin: 0 } }, p.clinical_constraints.map(c => h('li', { text: c }))))));
    out.appendChild(h('div', { class: 'section' }, h('div', { class: 'row between', style: { margin: '0 2px 10px' } }, h('span', { class: 'h-sec', style: { margin: 0 }, text: 'Clinical analysis' }), A.aiBadge(r.analysis.source, r.analysis.error)), h('div', { class: 'card' }, prose(r.analysis.text))));
    return out;
  }

  // ------------------------------------------------------------------- biomarkers
  function rangeBar(b) {
    const lo = Math.min(b.min, b.value), hi = Math.max(b.max, b.value), pad = (hi - lo) * 0.22 || 1;
    const d0 = lo - pad, d1 = hi + pad, pos = x => Math.max(1, Math.min(99, ((x - d0) / (d1 - d0)) * 100));
    const kind = A.statusKind(b.status);
    return h('div', { class: 'rbar', role: 'img', 'aria-label': b.name + ' ' + b.value + ' ' + b.unit + ', ' + b.status },
      h('div', { class: 'band', style: { left: pos(b.min) + '%', width: (pos(b.max) - pos(b.min)) + '%' } }),
      h('div', { class: 'mk', style: { left: pos(b.value) + '%', background: A.STATUS_COLOR[kind] } }));
  }
  function tabBiomarkers(r) {
    const bms = Object.values(r.profile.biomarkers || {});
    const out = h('div');
    if (!bms.length) return h('div', { class: 'empty' }, h('div', { class: 'ic' }, ico('report')), h('h3', { text: 'No biomarkers found' }), h('p', { text: 'We could not match standard lab values in this document. The plan uses your details only.' }));
    const abn = bms.filter(b => b.status !== 'Normal').length;
    out.appendChild(h('div', { class: 'seg' },
      h('button', { class: S.bmFilter === 'all' ? 'on' : '', onclick: () => { S.bmFilter = 'all'; A.render(); } }, 'All (' + bms.length + ')'),
      h('button', { class: S.bmFilter === 'abn' ? 'on' : '', onclick: () => { S.bmFilter = 'abn'; A.render(); } }, 'Out of range (' + abn + ')')));
    const cats = {};
    bms.forEach(b => { if (S.bmFilter === 'abn' && b.status === 'Normal') return; (cats[b.category || 'General'] = cats[b.category || 'General'] || []).push(b); });
    if (!Object.keys(cats).length) out.appendChild(h('div', { class: 'good', style: { marginTop: '14px' } }, ico('check'), 'Every extracted biomarker is inside its reference range.'));
    Object.keys(cats).forEach(c => {
      out.appendChild(h('div', { class: 'bcat', text: c }));
      cats[c].forEach(b => out.appendChild(h('div', { class: 'bm' },
        h('div', { class: 't' }, h('div', null, h('div', { class: 'n', text: b.name }), h('div', { class: 'r', text: 'Reference ' + b.range })),
          h('div', { class: 'val' }, h('b', { class: 'num', text: String(b.value) }), h('small', { text: b.unit }), h('div', { style: { marginTop: '4px' } }, A.pill(b.status.toUpperCase(), A.statusKind(b.status))))),
        rangeBar(b), h('div', { class: 'd', text: b.plain_desc || '' }))));
    });
    out.appendChild(h('div', { class: 'section' }, A.accordion('Text read from the document', h('pre', { class: 'mono', style: { whiteSpace: 'pre-wrap', fontSize: '11.5px', margin: 0, color: 'var(--muted)' }, text: r.profile.raw_text_preview || '' }))));
    return out;
  }

  // ------------------------------------------------------------------- meal plan
  const groceryKey = (c, i) => c + '|' + i;
  function mealCard(meal, slot) {
    return h('div', { class: 'meal' },
      h('div', { class: 'mh' }, h('span', { class: 'slot' }, h('span', { class: 'ic' }, ico(slot[2])), slot[1]), h('span', { class: 'kc', text: fmt(meal.kcal) + ' kcal' })),
      h('h4', { text: meal.name }), h('p', { class: 'pt', text: meal.portion }),
      meal.why ? h('div', { class: 'why' }, h('b', { text: 'Why: ' }), meal.why) : null,
      meal.source ? h('div', { class: 'src', text: 'Calories: ' + meal.source }) : null);
  }
  function tabPlan(r) {
    const p = r.protocol, m = p.macros, days = p.structured_7day_meals || [];
    const out = h('div');
    if (!days.length) { out.appendChild(h('div', { class: 'card' }, prose(r.diet.text))); return out; }
    if (S.day >= days.length) S.day = 0;
    const strip = h('div', { class: 'days', role: 'tablist' });
    const dayBox = h('div', { class: 'daycard' });
    const draw = () => {
      strip.querySelectorAll('.day').forEach((el, i) => el.classList.toggle('on', i === S.day));
      const d = days[S.day], tot = d.day_total_kcal != null ? d.day_total_kcal : A.SLOTS.reduce((a, s) => a + ((d[s[0]] || {}).kcal || 0), 0);
      dayBox.innerHTML = '';
      dayBox.append(h('div', { class: 'card' }, h('div', { class: 'dt', text: 'Day ' + d.day + ': ' + d.title }), h('div', { class: 'df', text: d.focus }),
        h('div', { class: 'kbar' }, h('i', { style: { width: Math.min(100, tot / m.calories * 100) + '%' } })),
        h('div', { class: 'kbar-l' }, h('span', { text: fmt(tot) + ' kcal planned' }), h('span', { text: 'target ' + fmt(m.calories) }))));
      A.SLOTS.forEach(s => { const meal = d[s[0]]; if (meal && meal.name) dayBox.appendChild(mealCard(meal, s)); });
    };
    days.forEach((d, i) => strip.appendChild(h('button', { class: 'day', role: 'tab', onclick: () => { S.day = i; draw(); } }, h('small', { text: 'Day' }), h('b', { text: String(d.day) }))));
    let x0 = null;
    dayBox.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
    dayBox.addEventListener('touchend', e => { if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 70) { S.day = Math.max(0, Math.min(days.length - 1, S.day + (dx < 0 ? 1 : -1))); draw(); const on = strip.querySelector('.on'); on && on.scrollIntoView({ inline: 'center', block: 'nearest', behavior: 'smooth' }); } }, { passive: true });

    out.appendChild(h('div', { class: 'grid2' }, ...[['Carbs', m.carbs], ['Protein', m.protein]].map(x => h('div', { class: 'stat' }, h('b', { text: x[1].grams + ' g' }), h('span', { text: x[0] + ' · ' + x[1].percentage + '%' })))));
    out.appendChild(h('p', { class: 'note', style: { margin: '10px 2px 12px' }, text: (p.cuisine || '') + '. Swipe the day card or tap a day.' }));
    const algs = (r.profile.demographics.allergies || []);
    if (algs.length) out.appendChild(h('div', { class: 'callout warn', style: { marginBottom: '12px' } }, h('b', { text: 'Allergens: ' + algs.join(', ') }),
      h('p', { text: 'Foods are filtered by name. Ingredients hidden inside a dish (ghee in kichdi, groundnuts in chutney, wheat in hing) cannot be seen, so check every recipe yourself.' })));
    out.appendChild(strip); out.appendChild(dayBox); draw();

    const chipsOf = (list, cls) => h('div', { class: 'chips' }, list.map(x => h('span', { class: 'chip tag ' + cls, text: x })));
    out.appendChild(h('div', { class: 'section' },
      A.accordion('Foods to emphasise (' + p.strongly_recommend.length + ')', chipsOf(p.strongly_recommend, 'ok')),
      A.accordion('Foods to avoid (' + p.strictly_avoid.length + ')', chipsOf(p.strictly_avoid, 'bad'))));

    const checked = A.store.get('na.groc', {});
    const gl = h('div', { class: 'glist' });
    Object.keys(p.grocery_categories || {}).forEach(c => {
      gl.appendChild(h('h5', { text: c }));
      p.grocery_categories[c].forEach((item, i) => {
        const cb = h('input', { type: 'checkbox' }); cb.checked = !!checked[groceryKey(c, i)];
        cb.addEventListener('change', () => { checked[groceryKey(c, i)] = cb.checked; A.store.set('na.groc', checked); });
        gl.appendChild(h('label', null, cb, h('span', { text: item })));
      });
    });
    out.appendChild(h('div', { class: 'section' }, A.accordion('Grocery list', gl),
      A.accordion('4 daily habits', h('div', { class: 'stack' }, (p.lifestyle_habits || []).map(x => h('div', null, h('b', { text: x.title }), h('div', { class: 'muted', style: { fontSize: '13.5px' }, text: x.desc }))))),
      A.accordion('Dietitian notes', h('div', null, h('div', { style: { marginBottom: '8px' } }, A.aiBadge(r.diet.source, r.diet.error)), prose(r.diet.text)))));
    return out;
  }

  // ------------------------------------------------------------------- doctor brief
  function tabBrief(r) {
    const a = r.audit, sc = a.score, col = sc >= 80 ? 'var(--ok)' : sc >= 50 ? 'var(--warn)' : 'var(--crit)';
    const out = h('div');
    out.appendChild(h('div', { class: 'card' }, h('div', { class: 'score' }, A.ring(sc, col),
      h('div', null, h('div', { class: 'muted', style: { fontSize: '12px', fontWeight: 800, letterSpacing: '.07em', textTransform: 'uppercase' }, text: 'Plan self-check' }),
        h('div', { style: { fontSize: '17px', fontWeight: 800, marginTop: '2px' }, text: a.verdict.replace(/^PASSED - /, 'Passed: ').replace(/^PARTIAL - /, 'Partial: ').replace(/^FAILED$/, 'Failed') }),
        h('div', { class: 'note', style: { marginTop: '4px' }, text: 'Checks the plan against its own rules. This is not a medical clearance.' }),
        r.evaluation.aiScore != null ? h('div', { class: 'note', style: { marginTop: '4px' }, text: 'AI self-assessed: ' + r.evaluation.aiScore + '/100' }) : null)),
      h('div', { style: { marginTop: '8px' } }, (a.checks || []).map(c => h('div', { class: 'check' }, h('span', { class: 'ck' + (c[1] ? '' : ' no') }, ico(c[1] ? 'check' : 'x')), h('div', null, c[0], h('small', { text: c[2] }))))),
      h('p', { class: 'note', style: { marginTop: '8px' }, text: a.scope })));
    out.appendChild(h('div', { class: 'section' }, h('div', { class: 'row between', style: { margin: '0 2px 10px' } }, h('span', { class: 'h-sec', style: { margin: 0 }, text: 'Doctor brief' }), A.aiBadge(r.evaluation.source, r.evaluation.error)),
      h('div', { class: 'card' }, prose(r.evaluation.text)),
      h('button', { class: 'btn dark block', style: { marginTop: '12px' }, onclick: () => shareText('Doctor brief - ' + (r.profile.demographics.name || 'Patient'), r.evaluation.text) }, ico('share'), 'Share doctor brief')));
    return out;
  }

  // ------------------------------------------------------------------- chat inside report
  let chatBusy = false;
  function tabAsk(r) {
    const out = h('div'), list = h('div', { class: 'chat' });
    const sug = ['Can I eat rice?', 'What does my HbA1c mean?', 'Swap my breakfast', 'How much water should I drink?'];
    const draw = () => {
      list.innerHTML = '';
      if (!r.chat.length) list.appendChild(h('div', { class: 'bubble a' }, 'Hi! Ask about a food, a lab value, or a swap in your plan. I check every answer against your own flags and allergens.'));
      r.chat.forEach(msg => list.appendChild(msg.role === 'user' ? h('div', { class: 'bubble u', text: msg.content }) : h('div', { class: 'bubble a' }, prose(msg.content), msg.src ? h('div', { style: { marginTop: '8px' } }, A.aiBadge(msg.src)) : null)));
      if (chatBusy) list.appendChild(h('div', { class: 'bubble a' }, h('span', { class: 'typing' }, h('i'), h('i'), h('i'))));
    };
    const input = h('input', { class: 'input', placeholder: 'Ask about your report or plan...', enterkeyhint: 'send', 'aria-label': 'Question' });
    const send = async (q) => {
      q = (q || input.value).trim(); if (!q || chatBusy) return; input.value = '';
      r.chat.push({ role: 'user', content: q }); chatBusy = true; draw(); scrollEnd();
      const ctx = { profile: r.profile, protocol: r.protocol, analysis: r.analysis.text, diet: r.diet.text };
      let res;
      try { res = await Ag.runConsultant(A.aiLive() ? A.llm() : null, q, r.chat.slice(0, -1), ctx, null); }
      catch (e) { res = { text: Ag.answerOffline(q, ctx), source: 'builtin' }; }
      r.chat.push({ role: 'assistant', content: res.text, src: res.source }); chatBusy = false; A.saveReport();
      if (S.tab === 'report' && S.rtab === 'ask') { draw(); scrollEnd(); }
      if (res.error) toast('AI unreachable - answered on-device');
    };
    const scrollEnd = () => requestAnimationFrame(() => { const v = document.querySelector('#view'); v.scrollTop = v.scrollHeight; });
    input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
    out.append(list);
    if (r.chat.length < 2) out.appendChild(h('div', { class: 'chips', style: { marginTop: '12px' } }, sug.map(s => h('button', { class: 'chip', onclick: () => send(s) }, s))));
    out.appendChild(h('div', { class: 'composer' }, input, h('button', { class: 'send', onclick: () => send(), 'aria-label': 'Send' }, ico('send'))));
    if (r.chat.length) out.appendChild(h('button', { class: 'btn ghost sm', style: { marginTop: '8px' }, onclick: () => { r.chat = []; A.saveReport(); A.render(); } }, 'Clear conversation'));
    draw();
    return out;
  }

  // ------------------------------------------------------------------- export
  function shareText(title, text) {
    try { if (window.Native && Native.share) return Native.share(title, text); } catch (e) { /* fall through */ }
    if (navigator.share) return navigator.share({ title, text }).catch(() => {});
    copyText(text);
  }
  function copyText(text) {
    const done = () => toast('Copied to clipboard');
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text).then(done, () => legacyCopy(text, done));
    legacyCopy(text, done);
  }
  function legacyCopy(text, done) { const t = h('textarea', { style: { position: 'fixed', opacity: 0 } }); t.value = text; document.body.appendChild(t); t.select(); try { document.execCommand('copy'); done(); } catch (e) { toast('Copy is not available here'); } t.remove(); }

  function reportMarkdown(r) {
    const d = r.profile.demographics, p = r.protocol, m = p.macros, L = [];
    L.push('# Clinical nutrition report', '', '**Patient**: ' + d.name + ' | **Age**: ' + d.age + ' | **Sex**: ' + d.gender + ' | **BMI**: ' + d.bmi + ' kg/m2 | **BP**: ' + (d.bp_string || 'n/a'),
      '**Date**: ' + new Date(r.createdAt).toISOString().slice(0, 10), '**Flags**: ' + ((r.profile.clinical_flags || []).map(f => f.condition).join('; ') || 'none'),
      '**Prescribed energy**: ' + m.calories + ' kcal/day (carbs ' + m.carbs.percentage + '%, protein ' + m.protein.percentage + '%, fat ' + m.fat.percentage + '%)', '');
    L.push('## Biomarkers');
    Object.values(r.profile.biomarkers || {}).forEach(b => L.push('- ' + b.name + ': ' + b.value + ' ' + b.unit + ' (ref ' + b.range + ') - ' + b.status));
    L.push('', '## Clinical analysis', r.analysis.text, '', '## Audit and doctor brief', r.evaluation.text, '', '## Diet strategy', r.diet.text, '', '## 7-day plan');
    (p.structured_7day_meals || []).forEach(day => {
      L.push('', '### Day ' + day.day + ' - ' + day.title + ' (' + (day.day_total_kcal || '') + ' kcal)');
      A.SLOTS.forEach(s => { const x = day[s[0]]; if (x && x.name) L.push('- **' + s[1] + '**: ' + x.name + ' (' + x.kcal + ' kcal) - ' + x.portion); });
    });
    L.push('', '## Avoid', ...p.strictly_avoid.map(x => '- ' + x), '', '---', A.DISCLAIMER);
    return L.join('\n');
  }
  function tabExport(r) {
    const md = reportMarkdown(r), name = (r.profile.demographics.name || 'Patient');
    return h('div', { class: 'stack' },
      h('div', { class: 'card' }, h('h4', { text: 'Share your report' }), h('p', { class: 'muted', style: { fontSize: '13.5px', margin: '4px 0 12px' }, text: 'Opens the Android share sheet so you can send it to your doctor, save it to Drive or email it. Nothing is uploaded by this app.' }),
        h('div', { class: 'stack' },
          h('button', { class: 'btn primary block', onclick: () => shareText('Clinical nutrition report - ' + name, md) }, ico('share'), 'Share full report (text)'),
          h('button', { class: 'btn line block', onclick: () => copyText(md) }, ico('copy'), 'Copy as Markdown'),
          h('button', { class: 'btn line block', onclick: () => shareText('NutriAgent data - ' + name, JSON.stringify({ profile: r.profile, protocol: r.protocol, audit: r.audit, analysis: r.analysis.text, evaluation: r.evaluation.text }, null, 2)) }, ico('share'), 'Share structured data (JSON)'))),
      A.accordion('Preview', prose(md)),
      h('div', { class: 'card' }, h('h4', { text: 'Remove this report' }), h('p', { class: 'muted', style: { fontSize: '13.5px', margin: '4px 0 12px' }, text: 'Deletes the saved report and conversation from this phone.' }),
        h('button', { class: 'btn ghost block', onclick: () => { S.report = null; A.store.del('na.report'); A.store.del('na.groc'); S.rtab = 'overview'; toast('Report deleted'); A.go('home'); } }, ico('trash'), 'Delete report')));
  }

  // =================================================================== ASK (no report)
  function bmiCat(b) { return b >= 30 ? 'Obese' : b >= 25 ? 'Overweight' : b >= 18.5 ? 'Normal weight' : 'Underweight'; }
  function builtinGeneralMd(prep) {
    const m = prep.protocol.macros, en = prep.protocol.energy, L = [];
    L.push('Your targets from the details you gave: **' + m.calories + ' kcal/day** (BMR ' + en.bmr + ', TDEE ' + en.tdee + '), carbohydrate ' + m.carbs.grams + ' g, protein ' + m.protein.grams + ' g, fat ' + m.fat.grams + ' g.');
    const flags = prep.profile.clinical_flags || [];
    L.push(flags.length ? 'Conditions detected: **' + flags.map(f => f.condition).join('**, **') + '**.' : 'No specific condition was detected, so the balanced whole-foods baseline applies.');
    if ((prep.protocol.plain_summary || []).length) L.push('', ...prep.protocol.plain_summary.map(x => '- ' + x));
    L.push('', '*These targets come from what you typed, not from blood tests. Upload a lab report for biomarker-based results.*');
    return L.join('\n');
  }

  let askBox = null;
  V.ask = function () {
    const page = h('div', { class: 'page' });
    page.appendChild(h('div', { class: 'topbar', style: { padding: 'calc(var(--sat) + 14px) 0 10px' } }, h('div', null, h('h1', { class: 'title-lg', text: 'Ask NutriAgent' }), h('div', { class: 'muted', style: { fontSize: '13.5px', marginTop: '2px' }, text: 'No report needed. Describe your health in a sentence.' })), A.aiPill()));
    const ta = h('textarea', { class: 'input', placeholder: 'e.g. I am a 45 year old vegetarian with diabetes and high BP. Height 168cm, weight 78kg. What should I eat?', 'aria-label': 'Your question', value: S.askDraft || '' });
    ta.addEventListener('input', () => { S.askDraft = ta.value; });
    const go1 = () => { const q = ta.value.trim(); if (q) V.runAsk(q); };
    page.appendChild(h('div', { class: 'card' }, ta, h('div', { class: 'row between', style: { marginTop: '10px' } }, h('span', { class: 'note', text: 'Your saved diet and allergens are applied.' }), h('button', { class: 'btn primary', onclick: go1 }, ico('send'), 'Ask'))));
    page.appendChild(h('div', { class: 'chips', style: { marginTop: '12px' } }, A.SAMPLE_QUERIES.map(q => h('button', { class: 'chip', onclick: () => V.runAsk(q) }, q))));
    askBox = h('div', { style: { marginTop: '18px' } });
    page.appendChild(askBox);
    drawAsk();
    return page;
  };

  function drawAsk() {
    if (!askBox || !S.ask) return;
    const a = S.ask, prep = a.prep, p = prep.protocol, m = p.macros, flags = prep.profile.clinical_flags || [];
    askBox.innerHTML = '';
    askBox.appendChild(h('div', { class: 'bubble u', style: { marginLeft: 'auto', display: 'block', width: 'fit-content' }, text: a.query }));
    const stated = !(prep.assumptions || []).some(x => /Height\/weight not stated/.test(x));
    const demo = prep.profile.demographics;
    if (stated && demo.bmi) askBox.appendChild(h('div', { class: 'card', style: { marginTop: '12px' } }, h('div', { class: 'row between' }, h('div', null, h('div', { class: 'muted', style: { fontSize: '12px', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.07em' }, text: 'Your BMI' }), h('div', { class: 'title-lg num', text: String(demo.bmi) })), A.pill(bmiCat(demo.bmi), demo.bmi >= 30 ? 'crit' : demo.bmi >= 25 ? 'warn' : demo.bmi < 18.5 ? 'low' : 'ok'))));
    askBox.appendChild(h('div', { class: 'card', style: { marginTop: '12px' } },
      h('div', { class: 'row', style: { gap: '16px' } },
        A.donut([{ v: m.carbs.calories, color: 'var(--c-carb)' }, { v: m.protein.calories, color: 'var(--c-protein)' }, { v: m.fat.calories, color: 'var(--c-fat)' }], 112, 14, fmt(m.calories), 'kcal / day'),
        h('div', { class: 'legend', style: { flex: 1 } }, [['Carbs', m.carbs, 'var(--c-carb)'], ['Protein', m.protein, 'var(--c-protein)'], ['Fat', m.fat, 'var(--c-fat)']].map(x => h('div', { class: 'lg' }, h('i', { style: { background: x[2] } }), x[0], h('b', { text: x[1].grams + ' g' }))))),
      flags.length ? h('div', { class: 'chips', style: { marginTop: '12px' } }, flags.map(f => h('span', { class: 'chip tag on', text: f.condition }))) : h('p', { class: 'note', style: { marginTop: '10px' }, text: 'No specific condition detected in your sentence.' }),
      (prep.assumptions || []).length ? h('p', { class: 'note', style: { marginTop: '10px' }, text: 'Assumptions: ' + prep.assumptions.join('; ') + '.' }) : null));

    const answerCard = h('div', { class: 'card', style: { marginTop: '12px' } });
    answerCard.appendChild(h('div', { class: 'row between', style: { marginBottom: '8px' } }, h('b', { text: 'NutriAgent says' }), a.busy ? h('span', { class: 'aibadge' }, h('span', { class: 'spin' }), 'AI writing...') : A.aiBadge(a.ai && a.ai.source, a.ai && a.ai.error)));
    answerCard.appendChild(a.busy ? h('div', null, h('div', { class: 'skeleton', style: { height: '14px', margin: '8px 0', width: '92%' } }), h('div', { class: 'skeleton', style: { height: '14px', margin: '8px 0', width: '78%' } }), h('div', { class: 'skeleton', style: { height: '14px', margin: '8px 0', width: '64%' } })) : prose((a.ai && a.ai.text) || builtinGeneralMd(prep)));
    askBox.appendChild(answerCard);

    const chipsOf = (list, cls) => h('div', { class: 'chips' }, list.map(x => h('span', { class: 'chip tag ' + cls, text: x })));
    askBox.appendChild(h('div', { style: { marginTop: '12px' } },
      A.accordion('Protocols and constraints', h('div', null, h('div', { class: 'chips', style: { marginBottom: '10px' } }, p.protocols.map(x => h('span', { class: 'chip tag on', text: x }))), h('ul', { class: 'prose', style: { paddingLeft: '20px', margin: 0 } }, (p.clinical_constraints || []).map(c => h('li', { text: c }))))),
      A.accordion('Foods to emphasise', chipsOf(p.strongly_recommend, 'ok')), A.accordion('Foods to avoid', chipsOf(p.strictly_avoid, 'bad'))));

    const d1 = (p.structured_7day_meals || [])[0];
    if (d1) askBox.appendChild(h('div', { style: { marginTop: '8px' } }, A.accordion('Sample day: ' + d1.title + ' (' + fmt(d1.day_total_kcal) + ' kcal)', h('div', null, A.SLOTS.map(s => d1[s[0]] && d1[s[0]].name ? mealCard(d1[s[0]], s) : null)))));

    if (prep.comparison_rows && prep.comparison_rows.length) {
      const cmp = h('div', { class: 'rows' }, prep.comparison_rows.map(r => h('div', null, h('b', { text: r.dimension }), h('div', { class: 'l', text: 'Single AI: ' + r.llm }), h('div', { class: 'a', text: 'NutriAgent: ' + r.agent }))));
      const plain = a.plain ? h('div', { class: 'cmp', style: { marginBottom: '12px' } }, h('div', { class: 'col l' }, h('h4', null, 'Plain AI, no engine', A.pill('UNVERIFIED', 'crit')), a.plain.text ? prose(a.plain.text) : h('p', { class: 'note', text: a.plain.error || 'No answer.' }))) : null;
      askBox.appendChild(h('div', { style: { marginTop: '8px' } }, A.accordion('Compare: plain AI vs NutriAgent', h('div', null,
        A.aiLive() && !a.plain ? h('button', { class: 'btn line block sm', style: { marginBottom: '12px' }, onclick: runPlainCompare }, a.plainBusy ? 'Asking...' : 'Ask the plain AI the same question') : null,
        plain, h('p', { class: 'note', style: { marginBottom: '10px' }, text: 'The difference is the rules engine, NIN tables and safety checks around the model, not the model itself.' }), cmp), !!(a.plain || a.plainBusy))));
    }
    askBox.appendChild(h('div', { class: 'good', style: { marginTop: '14px', background: 'var(--accent-soft)', borderColor: 'transparent', color: 'var(--accent-ink)' } }, ico('upload'), h('div', null, h('b', { text: 'Want results from real numbers?' }), h('div', { style: { fontWeight: 500, fontSize: '13px' }, text: 'Upload a lab report to get biomarker-based flags and a full audit.' })),
      h('button', { class: 'btn primary sm', style: { marginLeft: 'auto', flex: 'none' }, onclick: A.pickPdf }, 'Upload')));
  }

  async function runPlainCompare() {
    const a = S.ask; if (!a || a.plainBusy) return;
    a.plainBusy = true; drawAsk();
    try { a.plain = await Ag.runPlain(A.llm(), a.query, null); } catch (e) { a.plain = { text: '', error: String(e.message || e) }; }
    a.plainBusy = false; drawAsk();
  }

  V.runAsk = async function (q) {
    if (S.tab !== 'ask') A.go('ask');
    S.askDraft = q;
    let prep;
    try { prep = Eng.prepareGeneral(q, { allergies: S.settings.allergies, dietary_preference: S.settings.diet, activity_level: S.settings.activity }); }
    catch (e) { console.error(e); return toast('Could not process that question'); }
    const a = S.ask = { query: q, prep, ai: null, plain: null, busy: A.aiLive() };
    A.render();
    const ta = document.querySelector('#view textarea'); if (ta) ta.value = q;
    requestAnimationFrame(() => { if (askBox) askBox.scrollIntoView({ block: 'start', behavior: 'smooth' }); });
    if (a.busy) {
      try { a.ai = await Ag.runGeneral(A.llm(), prep, null); } catch (e) { a.ai = { text: '', source: 'builtin' }; }
      a.busy = false; if (S.ask === a && S.tab === 'ask') drawAsk();
      if (a.ai && a.ai.error) toast('AI unreachable - showing the on-device answer');
    }
  };

  // =================================================================== SETTINGS
  V.settings = function () {
    const st = S.settings, page = h('div', { class: 'page' });
    page.appendChild(h('div', { class: 'topbar', style: { padding: 'calc(var(--sat) + 14px) 0 10px' } }, h('h1', { class: 'title-lg', text: 'Settings' })));

    // --- AI
    const sw = h('button', { class: 'switch' + (st.aiEnabled ? ' on' : ''), role: 'switch', 'aria-checked': String(!!st.aiEnabled), 'aria-label': 'Use AI server', onclick: () => { st.aiEnabled = !st.aiEnabled; A.saveSettings(); A.refreshAi().then(() => {}); A.render(); } });
    const aiList = h('div', { class: 'list' }, h('div', { class: 'item' }, h('div', { class: 'row between' }, h('div', { style: { minWidth: 0 } }, h('div', { class: 'it', text: 'Use an AI model' }), h('div', { class: 'id', text: 'Optional. Adds written analysis, dietitian notes and open-ended chat. Without it everything still runs on your phone.' })), sw)));
    if (st.aiEnabled) {
      const url = h('input', { class: 'input', placeholder: 'http://192.168.1.20:11434', inputmode: 'url', autocapitalize: 'off', autocomplete: 'off', value: st.url, 'aria-label': 'Server address' });
      url.addEventListener('change', () => { st.url = url.value.trim(); A.saveSettings(); });
      const model = h('input', { class: 'input', list: 'models', value: st.model, autocapitalize: 'off', 'aria-label': 'Model' });
      model.addEventListener('change', () => { st.model = model.value.trim() || 'qwen2.5:7b'; A.saveSettings(); });
      const dl = h('datalist', { id: 'models' }, ['qwen2.5:7b', 'qwen2.5:14b', 'qwen2.5:32b', 'qwen2.5:latest'].concat(S.ai.models || []).map(x => h('option', { value: x })));
      const res = h('div', { class: 'hidden' });
      const test = h('button', { class: 'btn line block', onclick: async () => {
        st.url = url.value.trim(); st.model = model.value.trim() || 'qwen2.5:7b'; A.saveSettings();
        test.disabled = true; test.replaceChildren(h('span', { class: 'spin' }), ' Testing...');
        const r = await A.refreshAi(true); S.ai = r;
        A.render();
      } }, 'Test connection');
      const to = h('div', { class: 'seg' }, [[120, '2 min'], [300, '5 min'], [600, '10 min'], [1200, '20 min']].map(x => h('button', { class: st.timeout === x[0] ? 'on' : '', onclick: () => { st.timeout = x[0]; A.saveSettings(); A.render(); } }, x[1])));
      const tr = S.ai.message ? h('div', { class: 'testres ' + ({ online: 'ok', nomodel: 'warn', offline: 'crit', checking: 'warn' }[S.ai.state] || 'warn'), text: S.ai.message }) : null;
      aiList.appendChild(h('div', { class: 'item stack' }, h('label', { class: 'field' }, h('span', { text: 'Server address' }), url), h('label', { class: 'field' }, h('span', { text: 'Model' }), model, dl),
        h('div', { class: 'field' }, h('span', { text: 'Wait up to' }), to), test, tr, res,
        (S.ai.models || []).length ? h('div', { class: 'chips' }, S.ai.models.slice(0, 8).map(x => h('button', { class: 'chip' + (x === st.model ? ' on' : ''), onclick: () => { st.model = x; A.saveSettings(); A.render(); } }, x))) : null));
      aiList.appendChild(h('div', { class: 'item' }, A.accordion('How to set this up', prose('1. On your computer install Ollama (ollama.com) and run `ollama pull qwen2.5:7b`.\n2. Let other devices reach it: start it with `OLLAMA_HOST=0.0.0.0 ollama serve` (on Linux with systemd set `Environment="OLLAMA_HOST=0.0.0.0"` in the service).\n3. Put your phone on the same Wi-Fi and enter `http://<computer-ip>:11434` above.\n4. Allow port **11434** through the computer firewall.\n\nOnly the question text and numbers from your report are sent, and only to the address you enter.'))));
    }
    page.appendChild(h('div', { class: 'section' }, sectionTitle('AI server', A.aiPill()), aiList));

    // --- preferences
    const diet = h('select', { class: 'input', 'aria-label': 'Diet' }, A.DIETS.map(x => h('option', { value: x, selected: x === st.diet }, x))); diet.addEventListener('change', () => { st.diet = diet.value; A.saveSettings(); });
    const alg = h('div', { class: 'chips' }), drawAlg = () => { alg.innerHTML = ''; A.ALLERGENS.forEach(x => alg.appendChild(h('button', { class: 'chip' + (st.allergies.indexOf(x) >= 0 ? ' on' : ''), onclick: () => { const i = st.allergies.indexOf(x); i >= 0 ? st.allergies.splice(i, 1) : st.allergies.push(x); A.saveSettings(); drawAlg(); } }, x))); }; drawAlg();
    const act = h('div', { class: 'chips' }), drawAct = () => { act.innerHTML = ''; A.ACTIVITY.forEach(x => act.appendChild(h('button', { class: 'chip' + (st.activity === x ? ' on' : ''), onclick: () => { st.activity = x; A.saveSettings(); drawAct(); } }, x))); }; drawAct();
    page.appendChild(h('div', { class: 'section' }, sectionTitle('My preferences'), h('div', { class: 'list' },
      h('div', { class: 'item stack' }, h('label', { class: 'field' }, h('span', { text: 'Diet' }), diet), h('div', { class: 'field' }, h('span', { text: 'Allergens to exclude' }), alg), h('div', { class: 'field' }, h('span', { text: 'Activity level' }), act),
        h('p', { class: 'note', text: 'Used for every new report and every question. Allergens always remove matching foods from plans.' })))));

    // --- appearance
    const th = h('div', { class: 'seg' }, [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']].map(x => h('button', { class: st.theme === x[0] ? 'on' : '', onclick: () => { st.theme = x[0]; A.saveSettings(); A.applyTheme(); A.render(); } }, x[1])));
    page.appendChild(h('div', { class: 'section' }, sectionTitle('Appearance'), h('div', { class: 'list' }, h('div', { class: 'item' }, th))));

    // --- data + about
    page.appendChild(h('div', { class: 'section' }, sectionTitle('Privacy and data'), h('div', { class: 'list' },
      h('div', { class: 'item' }, h('div', { class: 'row', style: { gap: '12px', alignItems: 'flex-start' } }, h('span', { class: 'ic', style: { color: 'var(--ok)', flex: 'none' } }, ico('lock')), h('div', null, h('div', { class: 'it', text: 'Stays on your phone' }), h('div', { class: 'id', text: 'PDFs are read on the device. Reports are saved only in this app. The only network traffic is to the AI address you choose, if any.' })))),
      h('div', { class: 'item' }, h('button', { class: 'btn ghost block', onclick: () => { if (!confirm('Delete the saved report, chat, grocery ticks and all settings?')) return; ['na.report', 'na.groc', 'na.settings'].forEach(A.store.del); S.report = null; Object.assign(S.settings, { aiEnabled: false, url: '', model: 'qwen2.5:7b', timeout: 600, diet: A.DIETS[0], allergies: [], activity: 'Light', theme: 'system' }); S.ai = { state: 'off', message: '', models: [] }; A.applyTheme(); toast('All data deleted'); A.render(); } }, ico('trash'), 'Delete all app data')))));
    const nin = (Eng.getNinSource && Eng.getNinSource()) || 'ICMR-NIN Dietary Guidelines for Indians';
    page.appendChild(h('div', { class: 'section' }, sectionTitle('About'), h('div', { class: 'list' },
      h('div', { class: 'item' }, h('div', { class: 'row', style: { gap: '12px' } }, A.logo(40), h('div', null, h('div', { class: 'it', text: 'NutriAgent 1.0' }), h('div', { class: 'id', text: 'On-device port of the NutriAgent clinical nutrition engine.' })))),
      h('div', { class: 'item' }, h('div', { class: 'id', text: 'Food energy values: ' + nin + '. Energy targets use the Mifflin-St Jeor equation. Condition protocols: low-GI, DASH, Mediterranean, renal and low-purine.' })),
      h('div', { class: 'item' }, h('div', { class: 'id', text: A.DISCLAIMER })))));
    return page;
  };

  // =================================================================== BOOT
  async function boot() {
    try {
      const res = await fetch('data/nin_food_data.json'); Eng.setNinData(await res.json());
    } catch (e) { console.error(e); toast('Food tables could not be loaded; meal plans will be limited'); }
    document.querySelector('#file').addEventListener('change', A.onFile);
    A.applyTheme();
    if (window.matchMedia) { try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', A.applyTheme); } catch (e) { /* old webview */ } }
    A.render();
    if (S.settings.aiEnabled && S.settings.url) A.refreshAi(true);
  }
  boot();
})();
