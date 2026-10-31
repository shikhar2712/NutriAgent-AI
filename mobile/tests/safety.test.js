// Safety regression: with an allergen selected, no planned meal may contain that allergen's foods;
// diet and flag exclusions must hold across the whole 7-day plan.
const E = require('../web/js/engine.js'); E.setNinData(require('../../nin_food_data.json'));
const fs = require('fs'), vm = require('vm');
const ctx = { window: {} }; vm.runInNewContext(fs.readFileSync(__dirname + '/../web/js/sample.js', 'utf8'), ctx);
const SLOTS = ['breakfast', 'mid_morning', 'lunch', 'snack', 'dinner', 'bedtime'];
let fails = 0;
const must = (c, m) => { if (!c) { fails++; console.log('FAIL', m); } };
const plan = (alg, diet) => {
  const p = E.buildHealthProfile(ctx.window.NUTRI_SAMPLE_REPORT);
  Object.assign(p.demographics, { allergies: alg, dietary_preference: diet, activity_level: 'Light' });
  return E.computeProtocol(p);
};
const names = pr => [].concat(...pr.structured_7day_meals.map(d => SLOTS.map(s => ((d[s] || {}).name || '').toLowerCase())));
const words = s => s.split(/[^a-z']+/).filter(Boolean);

E.ALLERGEN_OPTIONS.forEach(a => {
  const nm = names(plan([a.label], 'Omnivore / Standard'));
  must(nm.some(Boolean), a.label + ': plan is not empty');
  nm.forEach(n => a.aliases.forEach(al => { if (!al.includes('/') && words(n).includes(al)) must(false, a.label + ': "' + n + '" contains ' + al); }));
});
const nuts = names(plan(['Tree Nuts & Peanuts'], 'Omnivore / Standard')).join(' | ');
must(!/upma|poha|almond|cashew|peanut|groundnut/.test(nuts), 'nuts: no upma/poha/almond/cashew/peanut anywhere -> ' + nuts);
const veg = names(plan([], 'Vegetarian')).join(' | ');
must(!/chicken|egg|mutton|fish|prawn|keema/.test(veg), 'vegetarian: no meat/egg -> ' + veg);
const pesc = names(plan([], 'Pescatarian')).join(' | ');
must(!/chicken|mutton|keema/.test(pesc), 'pescatarian: no chicken/mutton -> ' + pesc);
// the sample patient has uric acid 7.8 (gout) + prediabetes: no fish/organ meat, no white rice
const base = names(plan([], 'Omnivore / Standard')).join(' | ');
must(!/fish|prawn|liver|mutton|keema/.test(base), 'gout flag: no purine-rich foods -> ' + base);
must(!/\brice\b(?! puttu)/.test(base.replace(/rice puttu/g, '')) , 'prediabetes flag: no white rice -> ' + base);
console.log(fails ? fails + ' FAILURES' : 'OK: allergen/diet/flag safety checks passed');
process.exit(fails ? 1 : 0);
