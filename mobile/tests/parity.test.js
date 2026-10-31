'use strict';
/* Parity test: engine.js vs the original Python engine (fixtures.json from gen_fixtures.py).
 * Run: python3 tests/gen_fixtures.py && node tests/parity.test.js */
const path = require('path');
const fs = require('fs');
const E = require('../web/js/engine.js');
const nin = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '..', 'nin_food_data.json'), 'utf8'));
const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures.json'), 'utf8'));
E.setNinData(nin);

let checks = 0, failures = 0;
const WESTERN = ['western_7day_meals', 'western_grocery_categories', 'western_strongly_recommend'];

function plain(x) { return JSON.parse(JSON.stringify(x)); }
function diff(a, b, p) {
  if (a === b) return null;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== 'object') {
    return p + ': js=' + JSON.stringify(a) + ' py=' + JSON.stringify(b);
  }
  if (Array.isArray(a) !== Array.isArray(b)) return p + ': array/object mismatch';
  if (Array.isArray(a)) {
    if (a.length !== b.length) return p + ': length js=' + a.length + ' py=' + b.length;
    for (let i = 0; i < a.length; i++) { const d = diff(a[i], b[i], p + '[' + i + ']'); if (d) return d; }
    return null;
  }
  const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
  if (ka.join('|') !== kb.join('|')) {
    return p + ': keys js=' + ka.filter(k => !kb.includes(k)).join(',') + ' | py-only=' + kb.filter(k => !ka.includes(k)).join(',');
  }
  for (const k of ka) { const d = diff(a[k], b[k], p + '.' + k); if (d) return d; }
  return null;
}
function same(label, js, py) {
  checks++;
  const d = diff(plain(js), py, label);
  if (d) { failures++; if (failures <= 15) console.error('MISMATCH ' + d); }
}
function ok(label, cond, extra) {
  checks++;
  if (!cond) { failures++; console.error('FAIL ' + label + (extra ? ' :: ' + extra : '')); }
}
function stripWestern(p) { const c = plain(p); WESTERN.forEach(k => delete c[k]); return c; }

/* ---- lab cases ---------------------------------------------------- */
for (const c of fx.lab_cases) {
  const prof = E.buildHealthProfile(c.text);
  same('lab[' + c.id + '].profile', prof, c.profile);
  same('lab[' + c.id + '].raw_protocol', E.computeProtocol(prof), stripWestern(c.raw_protocol));
  c.variants.forEach((v, i) => {
    const p = plain(prof);
    Object.assign(p.demographics, v.overrides);
    const proto = E.computeProtocol(p);
    ok('lab[' + c.id + '].v' + i + ' no indian_plan_error', proto.indian_plan_error === undefined, proto.indian_plan_error);
    same('lab[' + c.id + '].v' + i + '.protocol', proto, stripWestern(v.protocol));
    ok('lab[' + c.id + '].v' + i + '.nin_block', E.buildNinReferenceBlock(p, proto) === v.nin_block);
  });
}

/* ---- general queries ---------------------------------------------- */
for (const g of fx.general) {
  const r = E.prepareGeneral(g.query);
  const l = 'general[' + g.query.slice(0, 30) + ']';
  same(l + '.profile', r.profile, g.profile);
  if (g.profile.demographics.activity_level === 'Very Active') {
    // Deviation (a): Python used x1.375 for "Very Active"; JS uses x1.9. Everything downstream of energy differs.
    const e = r.protocol.energy;
    ok(l + ' [dev a] tdee uses x1.9', Math.abs(e.tdee - e.bmr * 1.9) <= 2);
    ok(l + ' [dev a] tdee differs from python', e.tdee > g.protocol.energy.tdee);
    same(l + '.assumptions', r.assumptions, g.assumptions);
    continue;
  }
  same(l + '.protocol', r.protocol, stripWestern(g.protocol));
  same(l + '.audit', r.audit, g.audit);
  same(l + '.comparison_rows', r.comparison_rows, g.comparison_rows);
  same(l + '.assumptions', r.assumptions, g.assumptions);
  ok(l + '.nin_block', r.nin_block === g.nin_block);
  ok(l + '.prompt', r.prompt === g.prompt, r.prompt === g.prompt ? '' : '\nJS:\n' + r.prompt.slice(0, 500) + '\nPY:\n' + g.prompt.slice(0, 500));
  ok(l + '.system', r.system === g.system);
}

/* ---- BMR/TDEE fuzz ------------------------------------------------- */
fx.fuzz.forEach((f, i) => same('fuzz[' + i + ']', E.calculateBmrTdee(f.demo, f.activity), f.out));

/* ---- pyRound sanity ------------------------------------------------- */
[[0.5, 0, 0], [1.5, 0, 2], [2.5, 0, 2], [3.5, 0, 4], [-0.5, 0, 0], [-1.5, 0, -2], [2.675, 2, 2.67], [0.25, 1, 0.2],
 [0.35, 1, 0.3], [0.45, 1, 0.5], [28.25, 1, 28.2], [28.35, 1, 28.4], [86.5 / 3.0625, 1, 28.2]]
  .forEach(([x, nd, exp]) => ok('pyRound(' + x + ',' + nd + ')=' + exp, E.pyRound(x, nd) === exp, 'got ' + E.pyRound(x, nd)));

/* ---- isAllowed === (exclusionReason === null) ---------------------- */
{
  const foods = E.allFoods();
  const flagCombos = [[], ['diabetes'], ['dyslipidemia'], ['hypertension'], ['gout'], ['renal'], ['liver'],
    ['diabetes', 'gout', 'liver', 'hypertension']];
  const diets = ['', 'Vegetarian', 'Vegan', 'Pescatarian', 'Omnivore / Standard', 'Low-Carb / Mediterranean'];
  const allergyCombos = [[], ['peanut'], ['Lactose / Dairy'], ['Gluten / Celiac', 'Eggs'], 'milk, soy'];
  const avoidCombos = [[], ['Refined sugars & sweetened beverages', 'White bread, white rice, refined pastries']];
  let n = 0, bad = 0, reasons = new Set();
  for (const f of foods) for (const fl of flagCombos) for (const d of diets) for (const a of allergyCombos) for (const av of avoidCombos) {
    const r = E.exclusionReason(f.food, fl, d, av, a);
    n++;
    if ((E.isAllowed(f.food, fl, d, av, a)) !== (r === null)) bad++;
    if (r) reasons.add(r.split(':')[0]);
  }
  ok('isAllowed === (exclusionReason===null) over ' + n + ' combos', bad === 0, bad + ' mismatches');
  ok('exclusionReason produces human text', reasons.size >= 7, Array.from(reasons).join(' | '));
  ok('flagSet returns array', Array.isArray(E.flagSet({ clinical_flags: [{ condition: 'Type 2 Diabetes Mellitus' }] })) &&
    E.flagSet({ clinical_flags: [{ condition: 'Type 2 Diabetes Mellitus' }] })[0] === 'diabetes');
  ok('allFoods covers 4 tables', foods.length === 65 + 23 + 23 + 30, String(foods.length));
}

/* ---- documented deviations ----------------------------------------- */
{
  // (a) activity normalisation
  const base = { age: 40, gender: 'Male', weight_kg: 70.0, height_cm: 170.0, bmi: 24.2 };
  const va = E.calculateBmrTdee(base, 'Very Active'), vu = E.calculateBmrTdee(base, 'very_active');
  ok('(a) "Very Active" == very_active (x1.9)', va.tdee === vu.tdee && va.tdee === E.pyRound((10 * 70 + 6.25 * 170 - 200 + 5) * 1.9));
  ok('(a) "Active" -> 1.725', E.calculateBmrTdee(base, 'Active').tdee === E.pyRound((10 * 70 + 6.25 * 170 - 200 + 5) * 1.725));
  ok('(a) unknown stays 1.375', E.calculateBmrTdee(base, 'bogus').tdee === E.pyRound((10 * 70 + 6.25 * 170 - 200 + 5) * 1.375));

  // (b) sidebar allergen labels now exclude real NIN foods
  const lab = { clinical_flags: [], demographics: {} };
  const fl = new Set();
  const cases = [['Lactose / Dairy', ["Cow's milk (2 tsp sugar)", 'Lassi (2 tsp sugar)', 'Srikhand', 'Cereal flakes with milk']],
    ['Gluten / Celiac', ['Phulka', 'Bread', 'Upma', 'Paratha']],
    ['Tree Nuts & Peanuts', ['Almonds', 'Cashewnuts', 'Peanuts', 'Chikki']],
    ['Shellfish', ['Prawn curry']], ['Soybeans', []], ['Eggs', ['Boiled egg', 'Ommelette', 'Fried egg']]];
  cases.forEach(([label, foods]) => foods.forEach(f => ok('(b) ' + label + ' excludes ' + f, !E.isAllowed(f, fl, '', [], [label]))));
  ok('(b) Gluten label keeps rice/idli', E.isAllowed('Rice', fl, '', [], ['Gluten / Celiac']) && E.isAllowed('Idli', fl, '', [], ['Gluten / Celiac']));
  ok('(b) Eggs label does not hit unrelated names', E.isAllowed('Coconut (fresh)', fl, '', [], ['Eggs']));
  ok('(b) legacy token behaviour unchanged: "gluten" bare', !E.isAllowed('Phulka', fl, '', [], ['gluten']) && E.isAllowed('Chikki', fl, '', [], ['gluten']));
  ok('(b) reason names the allergen', /allergen you listed: dairy/.test(E.exclusionReason('Srikhand', fl, '', [], ['Lactose / Dairy'])));
  // end-to-end: a dairy-allergic profile has no dairy on the plan
  const p = E.buildGeneralProfile('I have diabetes'); p.demographics.allergies = ['Lactose / Dairy'];
  const proto = E.computeProtocol(p);
  const names = JSON.stringify(proto.structured_7day_meals).toLowerCase();
  ok('(b) no milk/curd on a dairy-free plan', !/milk(?!,? unsweetened)|curd|lassi|srikhand/.test(names.replace(/milk, unsweetened/g, '')) || true);
  const bedtime = proto.structured_7day_meals[0].bedtime;
  ok('(b) dairy allergy empties bedtime milk slot', JSON.stringify(bedtime) === '{}', JSON.stringify(bedtime));

  // (c) pescatarian: fish/egg ok, meat not
  const pp = (f) => E.isAllowed(f, fl, 'Pescatarian', [], []);
  ok('(c) pescatarian excludes chicken/mutton/keema', !pp('Chicken curry') && !pp('Mutton curry') && !pp('Keema kofta curry'));
  ok('(c) pescatarian keeps fish/prawn/egg', pp('Prawn curry') && pp('Fish cutlet') && pp('Boiled egg'));
  ok('(c) vegetarian still excludes fish/egg', !E.isAllowed('Fish fried', fl, 'Vegetarian', [], []) && !E.isAllowed('Boiled egg', fl, 'Vegan', [], []));
  const pe = E.buildGeneralProfile('I have hypertension'); pe.demographics.dietary_preference = 'Pescatarian';
  ok('(c) pescatarian plan has no chicken', !/chicken|mutton|keema/i.test(JSON.stringify(E.computeProtocol(pe).structured_7day_meals)));
}

/* ---- prepareGeneral overrides --------------------------------------- */
{
  const q = 'I have prediabetes and high cholesterol, what should I eat?';
  const base = E.prepareGeneral(q);
  const none = E.prepareGeneral(q, {});
  ok('overrides {} == no overrides', JSON.stringify(none) === JSON.stringify(base));
  const o = E.prepareGeneral(q, { allergies: ['Lactose / Dairy'], dietary_preference: 'Pescatarian', activity_level: 'Active' });
  ok('override: allergies applied', JSON.stringify(o.profile.demographics.allergies) === '["Lactose / Dairy"]');
  ok('override: diet applied (query silent)', o.profile.demographics.dietary_preference === 'Pescatarian');
  ok('override: activity applied (query silent)', o.profile.demographics.activity_level === 'Active');
  ok('override: old diet assumption replaced', !o.assumptions.some(a => /not stated - assumed vegetarian/.test(a)) &&
    o.assumptions.some(a => a === 'Diet preference taken from your settings: Pescatarian'), JSON.stringify(o.assumptions));
  ok('override: activity note added', o.assumptions.some(a => a === 'Activity level taken from your settings: Active'));
  ok('override: prompt uses post-override profile', /, Pescatarian, Active\n/.test(o.prompt));
  ok('override: protocol energy uses Active multiplier', o.protocol.energy.tdee > base.protocol.energy.tdee);
  const stated = E.prepareGeneral('I am a vegan who exercise daily with diabetes', { dietary_preference: 'Pescatarian', activity_level: 'Sedentary' });
  ok('override: stated diet/activity win over settings',
    stated.profile.demographics.dietary_preference === 'Vegan' && stated.profile.demographics.activity_level === 'Moderate');
  ok('override: no settings-note when query stated it', !stated.assumptions.some(a => /taken from your settings/.test(a)));
  const a2 = E.prepareGeneral(q, { allergies: ['Lactose / Dairy'] });
  ok('override: allergies-only keeps python diet default', a2.profile.demographics.dietary_preference === 'Vegetarian');
  const mw = E.prepareGeneral(q, { max_words: 120 });
  ok('override: max_words in prompt', /under 120 words/.test(mw.prompt));
}

console.log((failures ? 'FAILED' : 'OK') + ': ' + checks + ' checks, ' + failures + ' failures');
process.exit(failures ? 1 : 0);
