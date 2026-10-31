/*
 * engine.js - JavaScript port of NutriAgent's deterministic engine.
 * Ports: extractor.py (profile building), deterministic_nutrition.py, indian_foods.py, general_intake.py.
 * Keys stay snake_case and Python-shaped so the output can be diffed against the Python originals
 * (see tests/parity.test.js). Documented deviations live in tests/DEVIATIONS.md.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.NutriEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  /* ------------------------------------------------------------------ */
  /* Python-compat helpers                                               */
  /* ------------------------------------------------------------------ */

  /** Python's truthiness for numbers / None. */
  function T(x) { return x !== null && x !== undefined && x !== 0 && !Number.isNaN(x) && x !== ''; }

  /** Python round(): half-even for ints, exact-decimal half-even for ndigits. */
  function pyRound(x, nd) {
    nd = nd || 0;
    if (!isFinite(x)) return x;
    var neg = x < 0, a = Math.abs(x), r;
    if (nd === 0) {
      var fl = Math.floor(a), diff = a - fl;
      if (diff < 0.5) r = fl; else if (diff > 0.5) r = fl + 1; else r = (fl % 2 === 0) ? fl : fl + 1;
    } else {
      var s = a.toFixed(Math.min(100, nd + 40));
      var dot = s.indexOf('.');
      var keep = s.slice(0, dot + 1 + nd), rest = s.slice(dot + 1 + nd);
      var tie = rest.charAt(0) === '5' && /^50*$/.test(rest);
      if (tie) {
        var lastDigit = parseInt(keep.charAt(keep.length - 1), 10);
        r = (lastDigit % 2 === 0) ? Number(keep) : Number(a.toFixed(nd));
      } else {
        r = Number(a.toFixed(nd));
      }
    }
    if (r === 0) return 0;
    return neg ? -r : r;
  }

  /** str(float) for values that are floats in Python (118.0 -> "118.0"). */
  function pf(x) {
    if (x === null || x === undefined) return 'None';
    if (typeof x === 'number') return Number.isInteger(x) ? x.toFixed(1) : String(x);
    return String(x);
  }
  /** "%s" of an int-or-None. */
  function pyS(x) { return (x === null || x === undefined) ? 'None' : String(x); }
  function capitalize(s) { s = String(s); return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase(); }
  function escapeRe(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
  function uniq(a) { return Array.from(new Set(a)); }
  function startsWithAny(s, list) { return list.some(function (p) { return s.indexOf(p) === 0; }); }
  function includesAny(s, list) { return list.some(function (k) { return s.indexOf(k) !== -1; }); }

  /* ------------------------------------------------------------------ */
  /* Reference ranges (extractor.py)                                     */
  /* ------------------------------------------------------------------ */

  // Literals are strings so `range` can reproduce Python's str() of int vs float ("4.0" vs "70").
  function R(min, max, unit, name, category, desc) {
    var o = { min: Number(min), max: Number(max), unit: unit, name: name, category: category, plain_desc: desc };
    Object.defineProperty(o, '_minS', { value: min, enumerable: false });
    Object.defineProperty(o, '_maxS', { value: max, enumerable: false });
    return o;
  }
  var STANDARD_REFERENCE_RANGES = {
    fasting_glucose: R('70', '99', 'mg/dL', 'Fasting Blood Glucose', 'Blood Sugar & Diabetes', 'Blood sugar after an overnight fast. Key early indicator for diabetes and insulin resistance.'),
    postprandial_glucose: R('70', '140', 'mg/dL', 'Postprandial Glucose', 'Blood Sugar & Diabetes', 'Blood sugar 2 hours after a meal. Shows how efficiently your body clears carbohydrates.'),
    hba1c: R('4.0', '5.6', '%', 'HbA1c (Glycated Hemoglobin)', 'Blood Sugar & Diabetes', 'Your 3-month average blood sugar score. Standard metric for diagnosing prediabetes and diabetes.'),
    total_cholesterol: R('125', '200', 'mg/dL', 'Total Cholesterol', 'Heart & Lipids', 'Total amount of cholesterol circulating in your bloodstream.'),
    ldl_cholesterol: R('0', '100', 'mg/dL', 'LDL Cholesterol (Bad)', 'Heart & Lipids', "'Bad' cholesterol that can form plaque in blood vessels when elevated."),
    hdl_cholesterol_male: R('40', '100', 'mg/dL', 'HDL Cholesterol (Good, Male)', 'Heart & Lipids', "'Good' protective cholesterol that sweeps excess fats out of your arteries."),
    hdl_cholesterol_female: R('50', '100', 'mg/dL', 'HDL Cholesterol (Good, Female)', 'Heart & Lipids', "'Good' protective cholesterol that sweeps excess fats out of your arteries."),
    triglycerides: R('0', '150', 'mg/dL', 'Triglycerides', 'Heart & Lipids', 'Fat molecules from unused calories. High levels increase heart and liver risk.'),
    creatinine: R('0.6', '1.2', 'mg/dL', 'Serum Creatinine', 'Kidney & Uric Acid', 'Natural waste product filtered by healthy kidneys. Rises if kidney filtration slows down.'),
    egfr: R('90', '150', 'mL/min/1.73m²', 'eGFR (Kidney Filtration)', 'Kidney & Uric Acid', 'Estimated kidney filtration efficiency. Higher (above 90) means robust kidney cleansing.'),
    bun: R('7', '20', 'mg/dL', 'Blood Urea Nitrogen (BUN)', 'Kidney & Uric Acid', 'Measures waste nitrogen from protein digestion; reflects kidney and hydration status.'),
    uric_acid_male: R('3.4', '7.0', 'mg/dL', 'Uric Acid (Male)', 'Kidney & Uric Acid', 'Waste from purine breakdown. High levels can cause painful gout or kidney stones.'),
    uric_acid_female: R('2.4', '6.0', 'mg/dL', 'Uric Acid (Female)', 'Kidney & Uric Acid', 'Waste from purine breakdown. High levels can cause painful gout or kidney stones.'),
    alt_sgpt: R('7', '56', 'U/L', 'ALT (SGPT)', 'Liver Function', 'Liver-specific enzyme. Elevated values signal liver inflammation or fatty liver stress.'),
    ast_sgot: R('10', '40', 'U/L', 'AST (SGOT)', 'Liver Function', 'Enzyme found in liver and muscle tissue; rises during cellular stress or injury.'),
    bilirubin_total: R('0.2', '1.2', 'mg/dL', 'Total Bilirubin', 'Liver Function', 'Yellow pigment from red blood cell breakdown; reflects liver processing and bile flow.'),
    hemoglobin_male: R('13.5', '17.5', 'g/dL', 'Hemoglobin (Male)', 'Blood Count (CBC)', 'Oxygen-carrying protein in red blood cells. Low values indicate anemia and fatigue.'),
    hemoglobin_female: R('12.0', '15.5', 'g/dL', 'Hemoglobin (Female)', 'Blood Count (CBC)', 'Oxygen-carrying protein in red blood cells. Low values indicate anemia and fatigue.'),
    wbc_count: R('4.5', '11.0', '10^3/µL', 'White Blood Cell Count', 'Blood Count (CBC)', 'Immune defense cells. High values indicate infection or inflammation; low means lowered immunity.'),
    platelets: R('150', '450', '10^3/µL', 'Platelet Count', 'Blood Count (CBC)', 'Cell fragments essential for normal blood clotting and wound healing.'),
    vitamin_d: R('30', '100', 'ng/mL', 'Vitamin D (25-OH)', 'Vitamins & Minerals', 'Crucial hormone-vitamin for calcium absorption, bone strength, immunity, and insulin sensitivity.'),
    vitamin_b12: R('200', '900', 'pg/mL', 'Vitamin B12', 'Vitamins & Minerals', 'Essential for nerve health, DNA synthesis, and red blood cell formation.'),
    serum_ferritin: R('20', '250', 'ng/mL', 'Serum Ferritin (Iron Stores)', 'Vitamins & Minerals', "Your body's master iron storage bank. Low levels mean iron deficiency before anemia appears."),
    tsh: R('0.4', '4.0', 'µIU/mL', 'Thyroid Stimulating Hormone (TSH)', 'Thyroid & Hormones', 'Brain signal that regulates thyroid speed. High TSH means thyroid is sluggish (hypothyroid).'),
    systolic_bp: R('90', '120', 'mmHg', 'Systolic Blood Pressure', 'Vitals & Blood Pressure', 'Pressure in arteries when heart beats (top blood pressure number).'),
    diastolic_bp: R('60', '80', 'mmHg', 'Diastolic Blood Pressure', 'Vitals & Blood Pressure', 'Pressure in arteries when heart rests between beats (bottom blood pressure number).'),
    serum_potassium: R('3.5', '5.0', 'mEq/L', 'Serum Potassium (K+)', 'Electrolytes', 'Vital mineral for heart rhythm, muscle contractions, and fluid balance.'),
    serum_sodium: R('135', '145', 'mEq/L', 'Serum Sodium (Na+)', 'Electrolytes', 'Main mineral for fluid volume and blood pressure regulation.'),
    serum_calcium: R('8.5', '10.2', 'mg/dL', 'Serum Calcium', 'Electrolytes', 'Essential for bone density, nerve signaling, and muscle function.')
  };

  /* ------------------------------------------------------------------ */
  /* Option lists used by the UI                                         */
  /* ------------------------------------------------------------------ */

  var DIET_OPTIONS = ['Omnivore / Standard', 'Vegetarian', 'Vegan', 'Pescatarian', 'Low-Carb / Mediterranean'];
  var ACTIVITY_OPTIONS = ['Sedentary', 'Light', 'Moderate', 'Active', 'Very Active'];
  // Deviation (b): the sidebar labels now map to real NIN food-name aliases.
  var ALLERGEN_OPTIONS = [
    { label: 'Gluten / Celiac', key: 'gluten', aliases: ['wheat', 'phulka', 'chapati', 'chappathi', 'roti', 'paratha', 'puri', 'bread', 'semolina', 'upma', 'toast', 'cereal flakes', 'cornflakes', 'sandwich', 'pizza', 'noodles', 'pasta', 'maida', 'dalia', 'rava', 'puff', 'biscuit', 'cake', 'vada', 'bonda', 'samosa', 'kachori', 'pakori'] },
    { label: 'Lactose / Dairy', key: 'dairy', aliases: ['milk', 'buttermilk', 'curd', 'dahi', 'lassi', 'paneer', 'cheese', 'srikhand', 'butter', 'ghee', 'ice cream', 'ice-cream', 'custard', 'sandesh', 'khoa', 'kheer', 'chocolate'] },
    { label: 'Tree Nuts & Peanuts', key: 'nuts', aliases: ['almond', 'cashew', 'cashewnut', 'walnut', 'pista', 'pistachio', 'hazelnut', 'peanut', 'groundnut', 'chikki', 'coconut/groundnuts/til', 'poha', 'upma'] }  /* poha and upma are routinely tempered with groundnuts/cashews */,
    { label: 'Shellfish', key: 'shellfish', aliases: ['prawn', 'shrimp', 'crab', 'lobster', 'shellfish'] },
    { label: 'Soybeans', key: 'soy', aliases: ['soya', 'soy', 'soybean', 'tofu'] },
    { label: 'Eggs', key: 'eggs', aliases: ['egg', 'omelette', 'ommelette'] }
  ];
  function allergenOption(alg) {
    var l = String(alg).toLowerCase().trim();
    for (var i = 0; i < ALLERGEN_OPTIONS.length; i++) {
      // Label match only: bare tokens such as "gluten" keep Python's legacy alias behaviour.
      if (ALLERGEN_OPTIONS[i].label.toLowerCase() === l) return ALLERGEN_OPTIONS[i];
    }
    return null;
  }

  /* ------------------------------------------------------------------ */
  /* extractor.py: validation, demographics, biomarkers, profile         */
  /* ------------------------------------------------------------------ */

  function validateLabReport(rawText) {
    if (!rawText || rawText.trim().length < 50) {
      return {
        valid: false, confidence: 0.0,
        reason: 'The uploaded PDF is empty or text could not be extracted (may be a scanned image).',
        detected_sections: [], biomarker_hits: 0
      };
    }
    var medical = ['glucose', 'cholesterol', 'lipid', 'triglycerides', 'hba1c', 'creatinine',
      'egfr', 'hemoglobin', 'hdl', 'ldl', 'uric acid', 'sgot', 'sgpt', 'alt', 'ast',
      'bilirubin', 'wbc', 'platelet', 'vitamin', 'tsh', 'blood', 'urine', 'lab',
      'reference', 'specimen', 'patient', 'fasting', 'mg/dl', 'u/l', 'g/dl', 'mmol/l'];
    var t = rawText.toLowerCase();
    var matched = medical.filter(function (k) { return t.indexOf(k) !== -1; });
    var hits = matched.length;
    var sections = [];
    if (includesAny(t, ['lipid', 'cholesterol', 'triglyceride', 'hdl', 'ldl'])) sections.push('Lipid Panel');
    if (includesAny(t, ['glucose', 'hba1c', 'glycated', 'fasting sugar', 'sugar'])) sections.push('Glycemic / Diabetic Profile');
    if (includesAny(t, ['creatinine', 'egfr', 'bun', 'urea', 'kidney', 'renal'])) sections.push('Renal Function Panel');
    if (includesAny(t, ['alt', 'ast', 'sgot', 'sgpt', 'bilirubin', 'liver', 'hepatic'])) sections.push('Liver Function Panel');
    if (includesAny(t, ['hemoglobin', 'wbc', 'rbc', 'platelet', 'cbc', 'complete blood'])) sections.push('Complete Blood Count (CBC)');
    if (includesAny(t, ['vitamin d', 'vitamin b12', 'ferritin', 'iron'])) sections.push('Micronutrients & Vitamins');
    if (includesAny(t, ['tsh', 't3', 't4', 'thyroid'])) sections.push('Thyroid Profile');
    if (includesAny(t, ['potassium', 'sodium', 'calcium', 'electrolyte'])) sections.push('Electrolyte Panel');
    var confidence = Math.min(1.0, hits / 10.0);
    var valid = hits >= 3 || sections.length >= 1;
    return {
      valid: valid, confidence: pyRound(confidence, 2),
      reason: valid ? 'Valid medical lab report detected.' : 'Insufficient medical markers found.',
      detected_sections: sections, biomarker_hits: hits, matched_keywords: matched.slice(0, 12)
    };
  }

  function parsePatientDemographics(rawText) {
    var d = {
      name: 'Patient', age: 45, gender: 'Unknown', weight_kg: null, height_cm: null, bmi: null,
      systolic_bp: null, diastolic_bp: null, bp_string: null
    };
    var m, v;

    m = /(?:Patient\s*Name|Name|Pt\s*Name)\s*[:\-]?\s*([A-Za-z\s\.\,\'\_\-]+?)(?:\n|\r|\t|Age|Gender|Sex|DOB|Date|Patient\s*ID|Ref\s*No|$)/i.exec(rawText);
    if (m) {
      var nm = m[1].trim();
      nm = nm.replace(/^(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s*/, '').trim();
      if (nm.length >= 2 && nm.length < 40 &&
          !includesAny(nm.toLowerCase(), ['report', 'test', 'specimen', 'hospital', 'patient id', 'date'])) {
        d.name = nm;
      }
    }

    m = /\bAge(?:\s*[\/\&]\s*(?:Sex|Gender))?\s*[:\-]?\s*(\d{1,3})\s*(?:Y|Yrs|Years)?\b/i.exec(rawText);
    if (m) {
      v = parseInt(m[1], 10);
      if (v >= 5 && v <= 115) d.age = v;
    } else {
      m = /\b(\d{1,3})\s*(?:Y|Yrs|Years\s*Old)\b/i.exec(rawText);
      if (m) {
        v = parseInt(m[1], 10);
        if (v >= 5 && v <= 115) d.age = v;
      }
    }

    m = /\b(?:Gender|Sex)\s*[:\-]?\s*(?:(?:Yrs|Years|\d+)\s*[\/\-]\s*)?(Male|Female|M|F|Other)\b/i.exec(rawText);
    if (m) {
      var g = m[1].trim().toUpperCase();
      if (g === 'M' || g === 'MALE') d.gender = 'Male';
      else if (g === 'F' || g === 'FEMALE') d.gender = 'Female';
    } else {
      if (/\b(?:Male)\b/i.test(rawText) && !/\bFemale\b/i.test(rawText)) d.gender = 'Male';
      else if (/\b(?:Female)\b/i.test(rawText)) d.gender = 'Female';
    }

    m = /\b(?:Height\s*[\/\&]\s*Weight)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*(?:cm|cms|m)?\s*[\/\&]\s*(\d{2,3}(?:\.\d+)?)\s*(?:kg|kgs|lbs)?\b/i.exec(rawText);
    if (m) {
      var h = parseFloat(m[1]), w = parseFloat(m[2]);
      if (h < 3.0) h *= 100;
      d.height_cm = h; d.weight_kg = w;
    }

    if (!T(d.weight_kg)) {
      m = /(?<!Height\s[\/\&])\b(?:Weight|Wt)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*(?:kg|kgs|lbs)?\b/i.exec(rawText);
      if (m) {
        v = parseFloat(m[1]);
        if (v >= 25.0 && v <= 300.0) d.weight_kg = v;
      }
    }

    if (!T(d.height_cm)) {
      m = /\b(?:Height|Ht)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*(?:cm|cms|m)?\b/i.exec(rawText);
      if (m) {
        v = parseFloat(m[1]);
        if (v < 3.0) v = v * 100;
        if (v >= 80.0 && v <= 250.0) d.height_cm = v;
      }
    }

    m = /\b(?:BMI|Body Mass Index)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)\b/i.exec(rawText);
    if (m) {
      d.bmi = parseFloat(m[1]);
    } else if (T(d.weight_kg) && T(d.height_cm)) {
      var hm = d.height_cm / 100.0;
      d.bmi = pyRound(d.weight_kg / (hm * hm), 1);
    }

    m = /(?:Blood\s*Pressure|BP)\s*[:\-]?\s*(\d{2,3})\s*[\/\-]\s*(\d{2,3})/i.exec(rawText);
    if (m) {
      var sbp = parseInt(m[1], 10), dbp = parseInt(m[2], 10);
      if (sbp >= 70 && sbp <= 240 && dbp >= 40 && dbp <= 140) {
        d.systolic_bp = sbp; d.diastolic_bp = dbp; d.bp_string = sbp + '/' + dbp + ' mmHg';
      }
    }
    return d;
  }

  var NUM = String.raw`([0-9]+(?:\.[0-9]+)?)`;
  var BIOMARKER_PATTERNS = {
    fasting_glucose: [
      String.raw`(?:fasting\s+(?:blood\s+)?(?:glucose|sugar)(?:\s*\([^\)]+\))?|glucose\s*[\-\,]?\s*fasting|fbs)\s*[:\-\s]*` + NUM,
      String.raw`(?:plasma\s+glucose\s*-\s*fasting|glucose\s*\(f\))\s*[:\-\s]*` + NUM
    ],
    postprandial_glucose: [
      String.raw`(?:post\s*prandial(?:\s+glucose)?(?:\s*\([^\)]+\))?|ppbs|glucose\s*[\-\,]?\s*pp|post\s*meal\s*glucose)\s*[:\-\s]*` + NUM
    ],
    hba1c: [String.raw`(?:glycated\s+hemoglobin|hba1c|haemoglobin\s*a1c|glycohemoglobin)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    total_cholesterol: [String.raw`(?:total\s+cholesterol|cholesterol\s*[\-\,]?\s*total)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    ldl_cholesterol: [String.raw`(?:ldl\s+cholesterol|ldl\s*-\s*c|ldl\s+direct|low\s+density\s+lipoprotein)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    hdl_cholesterol: [String.raw`(?:hdl\s+cholesterol|hdl\s*-\s*c|high\s+density\s+lipoprotein)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    triglycerides: [String.raw`(?:triglycerides|serum\s+triglycerides|tg)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    creatinine: [String.raw`(?:serum\s+creatinine|creatinine\s*[\-\,]?\s*serum|creatinine)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    egfr: [String.raw`(?:egfr|estimated\s+(?:gfr|glomerular\s+filtration\s+rate)|gfr\s*\(ckd-epi\))(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    bun: [String.raw`(?:blood\s+urea\s+nitrogen|bun|serum\s+urea)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    uric_acid: [String.raw`(?:uric\s+acid|serum\s+uric\s+acid)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    alt_sgpt: [String.raw`(?:alt\s*\([^\)]+\)|sgpt\s*\([^\)]+\)|alanine\s+aminotransferase|sgpt|alt)\s*[:\-\s]*` + NUM],
    ast_sgot: [String.raw`(?:ast\s*\([^\)]+\)|sgot\s*\([^\)]+\)|aspartate\s+aminotransferase|sgot|ast)\s*[:\-\s]*` + NUM],
    bilirubin_total: [String.raw`(?:total\s+bilirubin|bilirubin\s*[\-\,]?\s*total)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    hemoglobin: [String.raw`(?:hemoglobin|haemoglobin|hb)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    wbc_count: [String.raw`(?:total\s+leukocyte\s+count|wbc|total\s+wbc|tlc)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    platelets: [String.raw`(?:platelet\s+count|platelets)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    vitamin_d: [String.raw`(?:vitamin\s+d3?|25\s*-\s*(?:oh|hydroxy)\s*vitamin\s+d|25-hydroxyvitamin\s+d)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    vitamin_b12: [String.raw`(?:vitamin\s+b12|b12|cyanocobalamin)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    serum_ferritin: [String.raw`(?:ferritin|serum\s+ferritin)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    tsh: [String.raw`(?:tsh|thyroid\s+stimulating\s+hormone|ultra\s+tsh)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    serum_potassium: [String.raw`(?:potassium|serum\s+potassium|k\+)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    serum_sodium: [String.raw`(?:sodium|serum\s+sodium|na\+)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM],
    serum_calcium: [String.raw`(?:calcium|serum\s+calcium|ca\+\+)(?:\s*\([^\)]+\))?\s*[:\-\s]*` + NUM]
  };
  var BIOMARKER_REGEX = {};
  Object.keys(BIOMARKER_PATTERNS).forEach(function (k) {
    BIOMARKER_REGEX[k] = BIOMARKER_PATTERNS[k].map(function (p) { return new RegExp(p, 'i'); });
  });

  function titleCase(key) {
    return key.replace(/_/g, ' ').replace(/\w\S*/g, function (w) { return w.charAt(0).toUpperCase() + w.slice(1).toLowerCase(); });
  }

  function extractBiomarkers(rawText, gender) {
    gender = gender || 'Male';
    var out = {};
    Object.keys(BIOMARKER_REGEX).forEach(function (key) {
      var val = null;
      var list = BIOMARKER_REGEX[key];
      for (var i = 0; i < list.length; i++) {
        var m = list[i].exec(rawText);
        if (m) {
          var f = parseFloat(m[1]);
          if (!Number.isNaN(f)) { val = f; break; }
        }
      }
      if (val === null) return;

      var refKey = key;
      if (key === 'hdl_cholesterol') refKey = gender === 'Female' ? 'hdl_cholesterol_female' : 'hdl_cholesterol_male';
      else if (key === 'uric_acid') refKey = gender === 'Female' ? 'uric_acid_female' : 'uric_acid_male';
      else if (key === 'hemoglobin') refKey = gender === 'Female' ? 'hemoglobin_female' : 'hemoglobin_male';

      var ref = STANDARD_REFERENCE_RANGES[refKey];
      var minV, maxV, minS, maxS, unit, name, category, desc;
      if (ref) {
        minV = ref.min; maxV = ref.max; minS = ref._minS; maxS = ref._maxS;
        unit = ref.unit; name = ref.name; category = ref.category; desc = ref.plain_desc;
      } else {
        minV = 0; maxV = 9999; minS = '0'; maxS = '9999'; unit = ''; name = titleCase(key);
        category = 'General Metabolic'; desc = 'Clinical biomarker measuring metabolic health.';
      }
      var status = 'Normal';
      if (val > maxV) status = val > (maxV * 1.5) ? 'Critical High' : 'High';
      else if (val < minV) status = val < (minV * 0.7) ? 'Critical Low' : 'Low';

      out[key] = {
        name: name, value: val, unit: unit, range: minS + ' - ' + maxS + ' ' + unit,
        min: minV, max: maxV, status: status, category: category, plain_desc: desc
      };
    });
    return out;
  }

  function bval(biomarkers, key) { return biomarkers[key] ? biomarkers[key].value : undefined; }

  function buildHealthProfile(rawText) {
    var validation = validateLabReport(rawText);
    var demographics = parsePatientDemographics(rawText);
    var biomarkers = extractBiomarkers(rawText, demographics.gender || 'Male');
    var flags = [];

    var hba1c = bval(biomarkers, 'hba1c'), fbs = bval(biomarkers, 'fasting_glucose');
    if (T(hba1c)) {
      if (hba1c >= 6.5) {
        flags.push({
          condition: 'Type 2 Diabetes Mellitus', severity: 'High', marker: 'HbA1c: ' + pf(hba1c) + '%',
          organ: 'Blood Sugar / Metabolism',
          plain_meaning: 'Average blood sugar over the last 3 months is in the diabetic range.',
          action_tip: 'Focus on low-glycemic complex carbs, high fiber (>35g/day), and zero sugary beverages.'
        });
      } else if (hba1c >= 5.7) {
        flags.push({
          condition: 'Prediabetes / Impaired Fasting Glucose', severity: 'Moderate', marker: 'HbA1c: ' + pf(hba1c) + '%',
          organ: 'Blood Sugar / Metabolism',
          plain_meaning: 'Blood sugar is slightly elevated above normal. Fully reversible with dietary and lifestyle adjustments.',
          action_tip: 'Replace refined carbs with phulka/chapati, dalia, idli and dals (NIN GI: chapati 52 vs white rice 73), plus daily light physical activity.'
        });
      }
    } else if (T(fbs)) {
      if (fbs >= 126) {
        flags.push({
          condition: 'Hyperglycemia / Diabetes Suspect', severity: 'High', marker: 'FBS: ' + pf(fbs) + ' mg/dL',
          organ: 'Blood Sugar / Metabolism',
          plain_meaning: 'Fasting blood sugar is higher than standard clinical thresholds.',
          action_tip: 'Adopt low-glycemic, fiber-rich meals and consult physician for confirmatory HbA1c test.'
        });
      } else if (fbs >= 100) {
        flags.push({
          condition: 'Impaired Fasting Glucose', severity: 'Moderate', marker: 'FBS: ' + pf(fbs) + ' mg/dL',
          organ: 'Blood Sugar / Metabolism',
          plain_meaning: 'Fasting glucose is in the prediabetes warning zone.',
          action_tip: 'Avoid late-night heavy snacking and minimize refined carbohydrates and sweet drinks.'
        });
      }
    }

    var chol = bval(biomarkers, 'total_cholesterol'), ldl = bval(biomarkers, 'ldl_cholesterol');
    var tg = bval(biomarkers, 'triglycerides');
    if ((T(chol) && chol > 200) || (T(ldl) && ldl > 100) || (T(tg) && tg > 150)) {
      var det = [];
      if (T(chol) && chol > 200) det.push('Chol: ' + pf(chol));
      if (T(ldl) && ldl > 100) det.push('LDL: ' + pf(ldl));
      if (T(tg) && tg > 150) det.push('TG: ' + pf(tg));
      flags.push({
        condition: 'Dyslipidemia / Elevated Cholesterol', severity: 'Moderate', marker: det.join(', '),
        organ: 'Heart & Arteries',
        plain_meaning: 'Elevated circulating bad fats (LDL/Triglycerides) that can stress cardiovascular vessels over time.',
        action_tip: 'Switch deep-fried items (puri, vada, samosa) for steamed idli and dhokla; cook with mustard or groundnut oil and add flaxseed (alsi).'
      });
    }

    var creat = bval(biomarkers, 'creatinine'), egfr = bval(biomarkers, 'egfr');
    if ((T(creat) && creat > 1.2) || (T(egfr) && egfr < 60)) {
      flags.push({
        condition: 'Renal Impairment / CKD Risk', severity: (T(egfr) && egfr < 45) ? 'High' : 'Moderate',
        marker: 'Creatinine: ' + pf(creat) + ', eGFR: ' + pf(egfr), organ: 'Kidneys & Filtration',
        plain_meaning: 'Kidney filtering rate is slightly reduced or serum waste levels are elevated.',
        action_tip: 'Moderate daily protein to ~0.8g/kg, limit high-sodium foods, and maintain clean hydration.'
      });
    }

    var uric = bval(biomarkers, 'uric_acid');
    if (T(uric) && uric > 7.0) {
      flags.push({
        condition: 'Hyperuricemia (Uric Acid & Gout Risk)', severity: 'Moderate', marker: 'Uric Acid: ' + pf(uric) + ' mg/dL',
        organ: 'Uric Acid & Joints',
        plain_meaning: 'High uric acid in blood; can crystallize in joints (gout) or form kidney stones if unmanaged.',
        action_tip: 'Drink at least 3.0L water daily, avoid beer/spirits and high-purine organ meats, enjoy tart cherries.'
      });
    }

    var alt = bval(biomarkers, 'alt_sgpt'), ast = bval(biomarkers, 'ast_sgot');
    if ((T(alt) && alt > 56) || (T(ast) && ast > 40)) {
      flags.push({
        condition: 'Elevated Liver Enzymes (Hepatic Stress / NAFLD)', severity: (T(alt) && alt > 100) ? 'High' : 'Moderate',
        marker: 'ALT: ' + pf(alt) + ', AST: ' + pf(ast), organ: 'Liver Function',
        plain_meaning: 'Liver cells are experiencing mild metabolic stress or inflammation (common in fatty liver).',
        action_tip: 'Eliminate alcohol and high-fructose syrups; add cruciferous greens (broccoli), green tea, and turmeric.'
      });
    }

    var tsh = bval(biomarkers, 'tsh');
    if (T(tsh) && tsh > 4.5) {
      flags.push({
        condition: 'Elevated TSH (Sluggish Thyroid / Hypothyroidism)', severity: tsh < 8.0 ? 'Mild' : 'Moderate',
        marker: 'TSH: ' + pf(tsh) + ' µIU/mL', organ: 'Thyroid & Metabolism',
        plain_meaning: 'Pituitary gland is working harder to stimulate a sluggish thyroid gland.',
        action_tip: 'Eat 1-2 Brazil nuts daily for selenium, ensure adequate zinc/iodine, and cook cruciferous veggies thoroughly.'
      });
    } else if (T(tsh) && tsh < 0.4) {
      flags.push({
        condition: 'Low TSH (Overactive Thyroid Risk)', severity: 'Moderate', marker: 'TSH: ' + pf(tsh) + ' µIU/mL',
        organ: 'Thyroid & Metabolism',
        plain_meaning: 'Thyroid hormone levels may be elevated, speeding up metabolic processes.',
        action_tip: 'Consult physician for free T3/T4 testing and monitor caffeine intake.'
      });
    }

    var k = bval(biomarkers, 'serum_potassium');
    if (T(k) && k < 3.5) {
      flags.push({
        condition: 'Hypokalemia (Low Potassium)', severity: k >= 3.0 ? 'Mild' : 'High', marker: 'K+: ' + pf(k) + ' mEq/L',
        organ: 'Electrolytes & Heart Rhythm',
        plain_meaning: 'Low blood potassium, which can cause muscle cramps, weakness, or irregular heartbeats.',
        action_tip: 'Incorporate potassium-rich tender coconut water, bottle gourd, spinach, banana and buttermilk.'
      });
    } else if (T(k) && k > 5.0) {
      flags.push({
        condition: 'Hyperkalemia (High Potassium)', severity: 'High', marker: 'K+: ' + pf(k) + ' mEq/L',
        organ: 'Electrolytes & Heart Rhythm',
        plain_meaning: 'High potassium in blood; requires dietary care if kidneys are filtering slowly.',
        action_tip: 'Moderate high-potassium supplements and follow renal dietitian guidance.'
      });
    }

    var sbp = demographics.systolic_bp, dbp = demographics.diastolic_bp;
    if (T(sbp) && T(dbp)) {
      if (sbp >= 140 || dbp >= 90) {
        flags.push({
          condition: 'Stage 2 Hypertension', severity: 'High', marker: sbp + '/' + dbp + ' mmHg',
          organ: 'Blood Pressure & Vessels',
          plain_meaning: 'Blood pressure is significantly elevated, putting excess strain on heart and arteries.',
          action_tip: 'Strict DASH protocol: limit sodium <1800mg/day, boost potassium/magnesium, and reduce stress.'
        });
      } else if (sbp >= 130 || dbp >= 80) {
        flags.push({
          condition: 'Stage 1 Hypertension', severity: 'Moderate', marker: sbp + '/' + dbp + ' mmHg',
          organ: 'Blood Pressure & Vessels',
          plain_meaning: 'Blood pressure is in the mild high range; very responsive to sodium moderation and diet.',
          action_tip: 'Reduce processed/packaged salty foods, use fresh herbs/lemon for seasoning, eat leafy greens.'
        });
      }
    }

    var vd = bval(biomarkers, 'vitamin_d');
    if (T(vd) && vd < 30) {
      flags.push({
        condition: 'Vitamin D Deficiency', severity: vd >= 20 ? 'Mild' : 'Moderate', marker: 'Vit D: ' + pf(vd) + ' ng/mL',
        organ: 'Immunity & Bone Health',
        plain_meaning: 'Low circulating Vitamin D, affecting bone density, immune strength, and insulin signaling.',
        action_tip: 'Get 15-20 min gentle morning sunlight, consume fortified foods/egg yolks, and discuss D3 supplementation.'
      });
    }
    var b12 = bval(biomarkers, 'vitamin_b12');
    if (T(b12) && b12 < 200) {
      flags.push({
        condition: 'Vitamin B12 Deficiency', severity: 'Moderate', marker: 'B12: ' + pf(b12) + ' pg/mL',
        organ: 'Nerve & Energy Vitality',
        plain_meaning: 'Low B12 stores can lead to fatigue, brain fog, and low red blood cell production.',
        action_tip: 'Consume fortified nutritional yeast, dairy/eggs/lean meats, or discuss sublingual B12 with your doctor.'
      });
    }

    return {
      validation: validation, demographics: demographics, biomarkers: biomarkers, clinical_flags: flags,
      raw_text_length: rawText.length,
      raw_text_preview: rawText.slice(0, 800) + (rawText.length > 800 ? '...' : '')
    };
  }

  /* ------------------------------------------------------------------ */
  /* indian_foods.py                                                     */
  /* ------------------------------------------------------------------ */

  var NIN = {};
  function setNinData(obj) { NIN = obj || {}; }
  function hasNin() { return Object.keys(NIN).length > 0; }

  var FRIED = ['puri', 'paratha', 'bajji', 'pakora', 'vada', 'samosa', 'bonda', 'kachori', 'fried', 'puff', 'cheese balls', 'chips'];
  var HIGH_GI = ['rice', 'cornflakes', 'cereal flakes', 'bread', 'potato', 'french fries', 'glucose', 'honey', 'toast'];
  var SUGARY = ['barfi', 'chikki', 'cake', 'puttu', 'sandesh', 'meetha', 'halwa', 'jelly', 'jam', 'custard', 'srikhand',
    'chocolate', 'ice-cream', 'ice cream', 'cold drinks', 'squash', 'syrups', 'sharabats', 'sugar'];
  var HIGH_PURINE = ['mutton', 'keema', 'prawn', 'fish', 'liver', 'organ'];
  var HIGH_SODIUM = ['pizza', 'sandwich', 'chat', 'papad', 'pickle'];
  var NON_VEG = ['egg', 'ommelette', 'omelette', 'mutton', 'chicken', 'fish', 'prawn', 'keema'];
  var MEAT_ONLY = ['mutton', 'chicken', 'keema'];   // deviation (c): pescatarian exclusions

  var ALLERGY_ALIASES = {
    peanut: ['groundnut', 'peanuts'], peanuts: ['groundnut', 'peanuts'], groundnut: ['peanut'],
    nuts: ['almond', 'cashew', 'peanut', 'groundnut', 'walnut', 'til'],
    'tree nuts': ['almond', 'cashew', 'walnut'],
    milk: ['curd', 'lassi', 'milk', 'paneer', 'cheese', 'srikhand'],
    dairy: ['curd', 'lassi', 'milk', 'paneer', 'cheese', 'srikhand'],
    lactose: ['curd', 'lassi', 'milk', 'paneer', 'cheese'],
    gluten: ['wheat', 'phulka', 'paratha', 'puri', 'bread', 'semolina', 'upma', 'toast'],
    wheat: ['phulka', 'paratha', 'puri', 'bread', 'semolina', 'upma', 'toast'],
    soy: ['soya', 'soybean'], shellfish: ['prawn'], egg: ['ommelette', 'omelette']
  };

  function allFoods() {
    var out = [];
    ['cooked_preparations', 'nuts_salads_fruits', 'low_calorie_produce', 'high_calorie_produce'].forEach(function (key) {
      (NIN[key] || []).forEach(function (r) { out.push(Object.assign({}, r, { table: key })); });
    });
    return out;
  }

  function flagSetObj(profile) {
    var text = (profile.clinical_flags || []).map(function (f) { return f.condition || ''; }).join(' ').toLowerCase();
    var s = new Set();
    if (includesAny(text, ['diabet', 'glucose', 'glycem'])) s.add('diabetes');
    if (includesAny(text, ['lipid', 'cholesterol'])) s.add('dyslipidemia');
    if (text.indexOf('hypertension') !== -1 || text.indexOf('blood pressure') !== -1) s.add('hypertension');
    if (text.indexOf('uric') !== -1 || text.indexOf('gout') !== -1) s.add('gout');
    if (text.indexOf('renal') !== -1 || text.indexOf('kidney') !== -1) s.add('renal');
    if (text.indexOf('hepat') !== -1 || text.indexOf('liver') !== -1) s.add('liver');
    return s;
  }
  function flagSet(profile) { return Array.from(flagSetObj(profile)); }

  function asList(value) {
    if (!value) return [];
    if (typeof value === 'string') {
      return value.split(/[,;\/]/).map(function (v) { return v.trim(); }).filter(Boolean);
    }
    return Array.from(value).map(function (v) { return String(v).trim(); }).filter(Boolean);
  }

  function aliasHit(alias, f) {
    return new RegExp('\\b' + escapeRe(alias) + '(?:e?s)?\\b').test(f);
  }

  /** Why a food is excluded (same rules/order as Python is_allowed), or null if allowed. */
  function exclusionReason(food, flags, dietPref, strictlyAvoid, allergies) {
    var fl = flags instanceof Set ? flags : new Set(flags || []);
    var f = food.toLowerCase();
    var list = asList(allergies);
    for (var i = 0; i < list.length; i++) {
      var alg = list[i];
      var opt = allergenOption(alg);
      if (opt) {
        for (var j = 0; j < opt.aliases.length; j++) {
          if (aliasHit(opt.aliases[j], f)) return 'Contains an allergen you listed: ' + opt.key;
        }
        continue;
      }
      var token = alg.toLowerCase().replace(/[^a-z ]/g, '').trim();
      if (token && f.indexOf(token) !== -1) return 'Contains an allergen you listed: ' + token;
      var al = ALLERGY_ALIASES[token] || [];
      for (var a = 0; a < al.length; a++) {
        if (f.indexOf(al[a]) !== -1) return 'Contains an allergen you listed: ' + token;
      }
    }
    var dp = (dietPref || '').toLowerCase();
    if (startsWithAny(dp, ['veg', 'vegan'])) {
      if (includesAny(f, NON_VEG)) return 'Not vegetarian';
    } else if (dp.indexOf('pesc') === 0) {
      if (includesAny(f, MEAT_ONLY)) return 'Meat - not pescatarian';
    }
    var avoid = strictlyAvoid || [];
    for (var s = 0; s < avoid.length; s++) {
      var t = String(avoid[s]).toLowerCase().replace(/[^a-z ]/g, '').trim();
      if (t && (t.indexOf(f) !== -1 || f.indexOf(t) !== -1)) return 'On your strictly-avoid list: ' + avoid[s];
    }
    if (fl.has('diabetes')) {
      if (includesAny(f, SUGARY)) return 'Added sugar - not advised with diabetes';
      if (includesAny(f, HIGH_GI)) return 'High glycaemic index - not advised with diabetes/prediabetes';
    }
    if (fl.has('dyslipidemia') && includesAny(f, FRIED)) return 'Fried food - not advised with high cholesterol/fatty liver';
    if (fl.has('hypertension') && includesAny(f, HIGH_SODIUM)) return 'High sodium - not advised with hypertension';
    if (fl.has('gout') && includesAny(f, HIGH_PURINE)) return 'High purine - not advised with gout';
    if (fl.has('liver') && includesAny(f, FRIED)) return 'Fried food - not advised with high cholesterol/fatty liver';
    return null;
  }
  function isAllowed(food, flags, dietPref, strictlyAvoid, allergies) {
    return exclusionReason(food, flags, dietPref, strictlyAvoid, allergies) === null;
  }

  var ALIAS = { 'With gravy': 'Mixed vegetable curry (with gravy)', 'Dry': 'Dry sauteed seasonal vegetable' };
  var PLAIN_MILK = { food: 'Milk, unsweetened', portion: '1 cup (200 ml)', kcal: 140, category: 'Beverages', table: 'portion_macros' };
  function alias(n) { return Object.prototype.hasOwnProperty.call(ALIAS, n) ? ALIAS[n] : n; }

  function findFood(name) {
    var target = name.toLowerCase().trim();
    var foods = allFoods(), i;
    for (i = 0; i < foods.length; i++) if (foods[i].food.toLowerCase() === target) return foods[i];
    var re = new RegExp('\\b' + escapeRe(target) + '\\b');
    for (i = 0; i < foods.length; i++) if (re.test(foods[i].food.toLowerCase())) return foods[i];
    return null;
  }

  function fmtG(x) { return String(Number(x)); }

  function compose(parts, why, guard) {
    var names = [], portions = [], kcal = 0;
    parts.forEach(function (p) {
      var rec = p[0] === PLAIN_MILK.food ? PLAIN_MILK : findFood(p[0]);
      if (!rec) return;
      if (guard && !guard(rec.food)) return;
      names.push(alias(rec.food));
      var qty = rec.portion;
      if (p[1] !== 1) qty = fmtG(p[1]) + ' x ' + qty;
      portions.push(qty + ' (' + alias(rec.food) + ')');
      kcal += pyRound(rec.kcal * p[1]);
    });
    if (!names.length) return {};
    return { name: names.join(' + '), portion: portions.join(' + '), kcal: kcal, why: why, source: 'NIN Dietary Guidelines for Indians' };
  }

  var BREAKFAST = [
    [[['Idli', 2]], 'Steamed, fermented and oil-free; fermentation improves mineral bioavailability.'],
    [[['Dosa', 1]], 'Rice-lentil batter gives complementary proteins without added fat.'],
    [[['Upma', 1]], 'Semolina with vegetables delivers slow-release carbohydrate.'],
    [[['Wheat porridge', 1]], 'Whole wheat porridge is high in soluble fibre that blunts the glucose curve.'],
    [[['Poha', 1]], 'Flattened rice with vegetables and groundnut for sustained morning energy.'],
    [[['Cereal flakes with milk', 1]], 'Quick wholegrain start paired with milk protein.'],
    [[['Bread', 1]], 'Wholegrain slices kept light, paired with the mid-morning protein.']
  ];
  var MID_MORNING = [
    [[['Guava', 1]], 'Very high vitamin C and fibre for a low glycemic load.'],
    [[['Almonds', 1]], 'MUFA and magnesium support insulin sensitivity and vascular tone.'],
    [[['Papaya', 1]], 'Papain aids digestion; carotenoids support hepatic antioxidant defence.'],
    [[['Mosambi/orange', 1]], 'Citrus flavonoids improve endothelial function.'],
    [[['Apple', 1]], 'Pectin, a soluble fibre, binds cholesterol in the gut.'],
    [[['Cashewnuts', 1]], 'Plant protein and healthy fat to steady mid-morning appetite.'],
    [[['Peanuts', 1]], 'Affordable ALA-bearing protein with a low glycemic index.']
  ];
  var VEG_MAIN = [
    ['Plain dhal', 'Pulses supply lysine-rich protein that complements cereal.'],
    ['Sambar', 'Lentils with vegetables add fibre, folate and potassium.']
  ];
  var NONVEG_MAIN = [
    ['Chicken curry', 'Lean high-biological-value protein without red-meat purines.'],
    ['Boiled egg', 'Complete protein with choline for hepatic fat metabolism.']
  ];
  var SNACK = [
    [[['Tomato', 1]], 'Lycopene-rich and near-zero calorie.'],
    [[['Cucumber', 1]], 'Hydrating, potassium-bearing and naturally low in sodium.'],
    [[['Carrot', 1]], 'Beta-carotene supports mucosal and immune health.'],
    [[['Radish', 1]], 'Very low calorie with natural diuretic action.'],
    [[['Beetroot', 1]], 'Dietary nitrates support healthy blood pressure.'],
    [[['Onion', 1]], 'Quercetin, an anti-inflammatory flavonoid.'],
    [[['Orange juice', 1]], 'Light citrus refresher with vitamin C.']
  ];
  var THEMES = [
    ['Metabolic Reset', 'Fermented, oil-free carbohydrate with high-fibre pulses'],
    ['Glycemic Balance', 'Low-GI cereals paired with lysine-rich dhal'],
    ['Cardioprotective Day', 'Soluble fibre and MUFA-bearing nuts'],
    ['Renal & Urate Ease', 'Moderated protein with high fluid volume'],
    ['Micronutrient Density', 'Green leafy vegetables and citrus'],
    ['Digestive Rest', 'Light, steamed preparations'],
    ['Sustained Energy', 'Whole grains with balanced pulse protein']
  ];

  function buildIndian7DayMeals(profile, protocol) {
    if (!hasNin()) return [];
    var flags = flagSetObj(profile);
    var demo = profile.demographics || {};
    var dietPref = demo.dietary_preference || '';
    var allergies = demo.allergies || [];
    var avoid = protocol.strictly_avoid || [];
    var target = Math.trunc(Number(((protocol.macros || {}).calories !== undefined ? protocol.macros.calories : 1800)));
    var vegetarian = startsWithAny(dietPref.toLowerCase(), ['veg', 'vegan']) || !dietPref;

    function guard(food) { return isAllowed(food, flags, dietPref, avoid, allergies); }
    function ok(parts) { return parts.every(function (p) { return guard(p[0]); }); }
    function pick(pool, day) {
      for (var i = 0; i < pool.length; i++) {
        var e = pool[(day + i) % pool.length];
        if (ok(e[0])) return e;
      }
      return [null, null];
    }

    var days = [];
    for (var d = 0; d < 7; d++) {
      var bp = pick(BREAKFAST, d), mp = pick(MID_MORNING, d), sp = pick(SNACK, d);
      var mains = vegetarian ? VEG_MAIN : NONVEG_MAIN.concat(VEG_MAIN);
      var mainName = null, mainWhy = null;
      for (var i = 0; i < mains.length; i++) {
        var cand = mains[(d + i) % mains.length];
        if (guard(cand[0])) { mainName = cand[0]; mainWhy = cand[1]; break; }
      }
      if (mainName === null) { mainName = VEG_MAIN[0][0]; mainWhy = VEG_MAIN[0][1]; }

      var staples = flags.has('diabetes') ? ['Phulka', 'Rice'] : ['Rice', 'Phulka'];
      staples = staples.concat(['Idli', 'Dosa', 'Kichidi']);
      var cereal = null;
      for (var c = 0; c < staples.length; c++) if (guard(staples[c])) { cereal = staples[c]; break; }
      var cerealMult = cereal === 'Phulka' ? 2.0 : 1.0;

      var build = (function (cerealL, mainNameL, mainWhyL) {
        return function (mult, vegItem) {
          var base = cerealL ? [[cerealL, mult]] : [];
          var lunch = compose(
            base.concat([[mainNameL, 1], [vegItem, 1]]),
            cerealL === 'Phulka' ? mainWhyL + " Chapati is chosen over white rice on NIN's GI table (52 vs 73)." : mainWhyL,
            guard);
          var dinner = compose(
            (cerealL ? [[cerealL, Math.max(1.0, mult - 0.5)]] : []).concat([['Plain dhal', 1], [vegItem === 'With gravy' ? 'Dry' : 'With gravy', 1]]),
            'A lighter evening mirror of lunch eases overnight digestion.',
            guard);
          return [lunch, dinner];
        };
      })(cereal, mainName, mainWhy);

      var vegItem = d % 2 === 0 ? 'With gravy' : 'Dry';
      var mult = cerealMult;
      var breakfast = bp[0] ? compose(bp[0], bp[1], guard) : {};
      var mid = mp[0] ? compose(mp[0], mp[1], guard) : {};
      var snack = sp[0] ? compose(sp[0], sp[1], guard) : {};
      var milk = guard("Cow's milk (2 tsp sugar)") ? "Cow's milk" : PLAIN_MILK.food;
      var bedtime = compose([[milk, milk === PLAIN_MILK.food ? 1 : 0.5]], 'Milk supplies calcium and tryptophan for restful sleep.', guard);

      var lunchM, dinnerM, total = 0;
      for (var it = 0; it < 14; it++) {
        var ld = build(mult, vegItem);
        lunchM = ld[0]; dinnerM = ld[1];
        total = [breakfast, mid, lunchM, snack, dinnerM, bedtime].reduce(function (a, x) { return a + (x.kcal || 0); }, 0);
        if (total < target - 120 && mult < 8) mult += 0.5;
        else if (total > target + 120 && mult > 0.5) mult -= 0.5;
        else break;
      }
      days.push({
        day: d + 1, title: THEMES[d][0], focus: THEMES[d][1], breakfast: breakfast, mid_morning: mid,
        lunch: lunchM, snack: snack, dinner: dinnerM, bedtime: bedtime, day_total_kcal: total,
        cuisine: 'Indian (NIN-sourced)'
      });
    }
    return days;
  }

  function buildNinReferenceBlock(profile, protocol, maxPerGroup) {
    maxPerGroup = maxPerGroup === undefined ? 12 : maxPerGroup;
    if (!hasNin()) return '';
    var flags = flagSetObj(profile);
    var demo = profile.demographics || {};
    var dietPref = demo.dietary_preference || '';
    var allergies = demo.allergies || [];
    var avoid = protocol.strictly_avoid || [];

    var groups = {}, order = [];
    (NIN.cooked_preparations || []).forEach(function (r) {
      if (!isAllowed(r.food, flags, dietPref, avoid, allergies)) return;
      var cat = r.category || 'Other';
      if (!groups[cat]) { groups[cat] = []; order.push(cat); }
      if (groups[cat].length < maxPerGroup) {
        groups[cat].push(alias(r.food) + ' (' + r.portion + ') = ' + Math.trunc(r.kcal) + ' kcal');
      }
    });
    var fruitNuts = (NIN.nuts_salads_fruits || [])
      .filter(function (r) { return isAllowed(r.food, flags, dietPref, avoid, allergies); })
      .map(function (r) { return r.food + ' (' + r.portion + ') = ' + Math.trunc(r.kcal) + ' kcal'; })
      .slice(0, maxPerGroup * 2);

    var lines = [
      "### VERIFIED INDIAN FOOD TABLE - NIN / ICMR 'Dietary Guidelines for Indians'",
      'Use THESE foods and THESE calorie values when building meals. Do not invent kcal.',
      'Items contraindicated for this patient have already been removed from this list.'
    ];
    order.forEach(function (cat) { lines.push('- **' + cat + '**: ' + groups[cat].join('; ')); });
    if (fruitNuts.length) lines.push('- **Fruits / Nuts / Salads**: ' + fruitNuts.join('; '));

    var macros = NIN.portion_macros || [];
    if (macros.length) {
      lines.push('- **NIN portion macros (per portion)**: ' + macros.map(function (m) {
        return m.food_group + ' ' + pyS(m.g_per_portion) + 'g = ' + pf(m.kcal) + ' kcal, P ' + pf(m.protein_g) +
          'g, C ' + pf(m.carb_g) + 'g, F ' + pf(m.fat_g) + 'g';
      }).join('; '));
    }
    var gi = NIN.glycemic_index || [];
    if (gi.length && flags.has('diabetes')) {
      var low = gi.filter(function (g) { return g.glycemic_index < 56; })
        .map(function (g, i) { return [g, i]; })
        .sort(function (a, b) { return (a[0].glycemic_index - b[0].glycemic_index) || (a[1] - b[1]); })
        .map(function (x) { return x[0]; });
      lines.push('- **Low-GI choices (NIN GI table)**: ' + low.slice(0, 14).map(function (g) {
        return g.food + ' GI ' + Math.trunc(g.glycemic_index);
      }).join('; '));
    }
    lines.push('Prefer these Indian preparations; use a Western item only where NIN has no equivalent.');
    return lines.join('\n');
  }

  function buildIndianGroceryCategories(profile, protocol) {
    if (!hasNin()) return {};
    var flags = flagSetObj(profile);
    var demo = profile.demographics || {};
    var dietPref = demo.dietary_preference || '';
    var allergies = demo.allergies || [];
    var avoid = protocol.strictly_avoid || [];
    function keep(n) { return isAllowed(n, flags, dietPref, avoid, allergies); }

    var produce = (NIN.low_calorie_produce || []).filter(function (r) { return keep(r.food); });
    var rich = (NIN.high_calorie_produce || []).filter(function (r) { return keep(r.food); });
    var fruitsNuts = (NIN.nuts_salads_fruits || []).filter(function (r) { return keep(r.food); });
    var cooked = NIN.cooked_preparations || [];

    var cats = {};
    cats['Fresh Vegetables & Greens (NIN low-calorie list)'] =
      produce.slice(0, 8).map(function (r) { return alias(r.food) + ' - ' + Math.trunc(r.kcal) + ' kcal/100g'; });
    cats['Cereals, Millets & Pulses'] = cooked
      .filter(function (r) { return (r.category === 'Cereal' || r.category === 'Pulse') && keep(r.food); })
      .slice(0, 8)
      .map(function (r) { return alias(r.food) + ' (' + r.portion + ', ' + Math.trunc(r.kcal) + ' kcal)'; });
    cats['Fruits, Nuts & Salads'] =
      fruitsNuts.slice(0, 10).map(function (r) { return alias(r.food) + ' - ' + r.portion + ', ' + Math.trunc(r.kcal) + ' kcal'; });
    cats['Energy-dense staples (use measured portions)'] =
      rich.slice(0, 6).map(function (r) { return alias(r.food) + ' - ' + Math.trunc(r.kcal) + ' kcal/100g'; });
    var out = {};
    Object.keys(cats).forEach(function (k) { if (cats[k].length) out[k] = cats[k]; });
    return out;
  }

  function buildIndianRecommendations(profile, protocol) {
    if (!hasNin()) return [];
    var flags = flagSetObj(profile);
    var demo = profile.demographics || {};
    var dietPref = demo.dietary_preference || '';
    var allergies = demo.allergies || [];
    var avoid = protocol.strictly_avoid || [];
    function keep(n) { return isAllowed(n, flags, dietPref, avoid, allergies); }

    var recs = [];
    var gi = {};
    (NIN.glycemic_index || []).forEach(function (g) { gi[g.food.toLowerCase()] = g.glycemic_index; });

    if (flags.has('diabetes')) {
      var low = (NIN.glycemic_index || []).filter(function (g) { return g.glycemic_index < 56; })
        .map(function (g, i) { return [g.food, g.glycemic_index, i]; })
        .sort(function (a, b) { return (a[1] - b[1]) || (a[2] - b[2]); }).slice(0, 5);
      if (low.length) recs.push('Low-GI staples per NIN: ' + low.map(function (x) { return x[0] + ' (GI ' + Math.trunc(x[1]) + ')'; }).join(', '));
      if (T(gi['chappathi']) && T(gi['white boiled rice'])) {
        recs.push('Chapati/phulka (GI ' + gi['chappathi'] + ') in place of white rice (GI ' + gi['white boiled rice'] + ')');
      }
    }
    var pulses = (NIN.cooked_preparations || []).filter(function (r) { return r.category === 'Pulse' && keep(r.food); }).map(function (r) { return r.food; });
    if (pulses.length) recs.push('Daily pulses for complementary protein: ' + pulses.join(', '));

    var greens = (NIN.low_calorie_produce || []).filter(function (r) {
      return keep(r.food) && ['GLV', 'OTHER VEGETABLES'].indexOf((r.category || '').toUpperCase()) !== -1;
    }).map(function (r) { return r.food; });
    if (greens.length) recs.push('High-volume, low-calorie vegetables (NIN < 20 kcal/100 g): ' + greens.slice(0, 6).join(', '));

    var steamed = (NIN.cooked_preparations || []).filter(function (r) {
      return r.category === 'Cereal' && keep(r.food) && ['Idli', 'Dosa', 'Upma', 'Phulka', 'Wheat porridge'].indexOf(r.food) !== -1;
    }).map(function (r) { return r.food; });
    if (steamed.length) recs.push('Steamed / griddle-cooked preparations instead of fried: ' + steamed.join(', '));

    var fruits = (NIN.nuts_salads_fruits || []).filter(function (r) {
      return keep(r.food) && (r.category || '').toLowerCase().indexOf('fresh fruit') === 0;
    }).map(function (r) { return r.food; }).slice(0, 5);
    if (fruits.length) recs.push('Whole seasonal fruit rather than juice: ' + fruits.join(', '));

    if (flags.has('hypertension')) recs.push('Season with fresh herbs, lemon and tamarind; NIN caps salt at under 5 g/day');
    if (flags.has('gout') || flags.has('renal')) recs.push('Generous fluids through the day: buttermilk, lemon water, tender coconut water');
    return recs;
  }

  /* ------------------------------------------------------------------ */
  /* deterministic_nutrition.py                                          */
  /* ------------------------------------------------------------------ */

  var MULTIPLIERS = { sedentary: 1.2, light: 1.375, moderate: 1.55, active: 1.725, very_active: 1.9 };

  function calculateBmrTdee(demographics, activityLevel) {
    if (activityLevel === undefined) activityLevel = 'light';
    var age = Number(T(demographics.age) ? demographics.age : 45);
    var gender = capitalize(T(demographics.gender) ? demographics.gender : 'Male');

    var weight = demographics.weight_kg;
    weight = (weight === null || weight === undefined) ? (gender === 'Male' ? 72.0 : 60.0) : Number(weight);
    var height = demographics.height_cm;
    height = (height === null || height === undefined) ? (gender === 'Male' ? 172.0 : 160.0) : Number(height);

    // Deviation (a): normalise "Very Active" -> very_active
    var key = String(activityLevel).toLowerCase().trim().replace(/[\s\-]+/g, '_');
    var mult = Object.prototype.hasOwnProperty.call(MULTIPLIERS, key) ? MULTIPLIERS[key] : 1.375;

    var bmr = gender.toLowerCase() === 'female'
      ? (10.0 * weight) + (6.25 * height) - (5.0 * age) - 161.0
      : (10.0 * weight) + (6.25 * height) - (5.0 * age) + 5.0;
    var tdee = bmr * mult;
    var bmi = demographics.bmi;
    if (!T(bmi) && T(weight) && T(height)) bmi = pyRound(weight / Math.pow(height / 100.0, 2), 1);

    var adj = 0, goal = 'Weight Maintenance & Metabolic Optimization';
    if (T(bmi)) {
      if (bmi >= 30.0) { adj = -500; goal = 'Gradual Caloric Deficit (Weight Loss & Insulin Sensitivity)'; }
      else if (bmi >= 25.0) { adj = -300; goal = 'Mild Deficit (Metabolic Health & Weight Normalization)'; }
      else if (bmi < 18.5) { adj = 300; goal = 'Caloric Surplus (Nourishment & Lean Mass Gain)'; }
    }
    var target = Math.max(1300, pyRound(tdee + adj));
    return {
      bmr: pyRound(bmr), tdee: pyRound(tdee), target_calories: target,
      bmi: (bmi === undefined ? null : bmi), goal: goal, activity_level: activityLevel,
      calculated_weight_kg: weight, calculated_height_cm: height
    };
  }

  var GROCERY_WESTERN = {
    'Fresh Vegetables & Greens': ['Baby spinach, Tuscan kale, Swiss chard', 'Broccoli crowns & cauliflower (sulforaphane rich)', 'English cucumbers & celery stalks (natural diuretics)', 'Bell peppers (red/yellow for Vitamin C)', 'Zucchini, asparagus, and button mushrooms'],
    'Whole Grains & Complex Starches': ['Steel-cut oats (high beta-glucan)', 'Organic tri-color quinoa', 'Sprouted brown lentils & black chickpeas (chana)', 'Pearl barley or buckwheat', 'Sweet potatoes / Japanese yams (potassium-rich)'],
    'Lean Proteins & Plant Power': ['Wild Alaskan salmon or rainbow trout fillets', 'Organic pasture-raised eggs / liquid egg whites', 'Skinless chicken breast or turkey tenderloins', 'Organic firm non-GMO tofu / tempeh', 'Sprouted mung beans and edamame'],
    'Heart-Healthy Fats & Seeds': ['Extra virgin olive oil (cold-pressed, unrefined)', 'Raw walnuts (ALA Omega-3 powerhouse)', 'Raw soaked almonds & pumpkin seeds (zinc)', 'Chia seeds & ground golden flaxseed', 'Fresh Hass avocados'],
    'Therapeutic Teas & Seasonings': ['Ceylon cinnamon (improves insulin sensitivity)', 'Organic turmeric powder + black pepper (piperine)', 'Fresh ginger root and whole garlic cloves', 'Organic chamomile, peppermint, and hibiscus teas', 'Lemons and limes for clean alkaline hydration']
  };
  var LIFESTYLE_HABITS = [
    { title: '10-Minute Post-Meal Walk', desc: 'A gentle 10-minute walk after lunch and dinner significantly blunts post-meal blood sugar and triglyceride spikes.' },
    { title: 'Hydration Rhythm', desc: 'Drink a large glass of water upon waking and space fluids evenly between meals to assist kidney filtration.' },
    { title: 'Fiber First Principle', desc: 'Eat your vegetables and salad before your main carbs to create a natural fiber mesh in the stomach that slows sugar absorption.' },
    { title: 'Restful Sleep & Stress Care', desc: 'Aim for 7-8 hours of quality sleep to prevent cortisol spikes that drive insulin resistance and blood pressure.' }
  ];

  function computeProtocol(profile) {
    var demographics = profile.demographics || {};
    var flags = profile.clinical_flags || [];
    var energy = calculateBmrTdee(demographics, demographics.activity_level !== undefined ? demographics.activity_level : 'light');
    var targetKcal = energy.target_calories;
    var weightKg = energy.calculated_weight_kg !== undefined ? energy.calculated_weight_kg : 70.0;

    function anyC(words) { return flags.some(function (f) { return words.some(function (w) { return f.condition.indexOf(w) !== -1; }); }); }
    var isDiabetic = anyC(['Diabetes', 'Glucose']);
    var isDyslipidemic = anyC(['Dyslipidemia', 'Hypercholesterolemia']);
    var isHypertensive = anyC(['Hypertension']);
    var isHyperuricemic = anyC(['Hyperuricemia', 'Gout']);
    var isRenal = anyC(['Renal', 'CKD']);
    var isLiver = anyC(['Transaminases', 'Liver', 'Hepatic']);
    var isHypokalemic = anyC(['Hypokalemia', 'Potassium']);
    var isHypothyroid = anyC(['TSH', 'Hypothyroidism']);
    var vitDLow = anyC(['Vitamin D']);
    var vitB12Low = anyC(['Vitamin B12']);

    var carbPct = 50, proteinPct = 20, fatPct = 30;
    var protocols = ['Balanced Whole-Foods Protocol'];
    var constraints = [], avoid = [], recommend = [];
    function push(arr, items) { items.forEach(function (x) { arr.push(x); }); }

    if (isDiabetic) {
      protocols.push('Low Glycemic Index (Low-GI) / Insulin Sensitizing Protocol');
      carbPct = 40; proteinPct = 25; fatPct = 35;
      constraints.push('Max Net Carbs: 150-180g/day; Glycemic Load per meal < 15.');
      constraints.push('Dietary Fiber target: >= 35g/day with high soluble fiber (beta-glucan, psyllium, legumes).');
      push(avoid, ['Refined sugars & sweetened beverages', 'White bread, white rice, refined pastries', 'Fruit juices & high-fructose corn syrups']);
      push(recommend, ['Steel-cut oats, quinoa, barley', 'Non-starchy cruciferous vegetables', 'Chia seeds, flaxseeds, cinnamon', 'Legumes with complex resistant starches']);
    }
    if (isDyslipidemic) {
      protocols.push('Cardioprotective Mediterranean / Lipid-Lowering Protocol');
      fatPct = Math.max(fatPct, 30);
      constraints.push('Saturated Fatty Acids (SFA): < 7% of total daily calories (~12-15g max).');
      constraints.push('Zero trans-fats; prioritize Monounsaturated (MUFA) and Omega-3 Polyunsaturated Fats (PUFA).');
      constraints.push('Dietary soluble fiber: >= 30g/day to bind intestinal bile acids.');
      push(avoid, ['Deep fried foods, palm oil, hydrogenated fats', 'Processed meats (sausages, bacon, hot dogs)', 'High-fat dairy & commercial baked goods']);
      push(recommend, ['Extra virgin olive oil (cold-pressed)', 'Wild-caught fatty fish (salmon, sardines, mackerel) or algal EPA/DHA', 'Walnuts and raw almonds', 'Avocado & psyllium husk']);
    }
    if (isHypertensive) {
      protocols.push('DASH (Dietary Approaches to Stop Hypertension) Protocol');
      constraints.push('Sodium restriction: < 1500 - 2000 mg/day (equivalent to ~1 level tsp salt).');
      constraints.push('Potassium-to-Sodium ratio target >= 3:1 (ensure potassium rich foods if kidney function normal).');
      constraints.push('Magnesium target: >= 400 mg/day.');
      push(avoid, ['Canned soups, packaged noodles, salty snacks, pickles', 'Monosodium glutamate (MSG) & soy sauce in high amounts', 'Processed cured meats']);
      push(recommend, ['Dark leafy greens (spinach, kale, Swiss chard)', 'Pomegranate, beetroot (rich in nitric oxide donors)', 'Pumpkin seeds, unsalted almonds', 'Potassium-rich foods (sweet potato, coconut water)']);
    }
    if (isRenal) {
      protocols.push('Renal Protective Protocol (Stage-Specific)');
      var targetProtein = pyRound(weightKg * 0.8);
      constraints.push('Protein moderation: ~' + targetProtein + 'g/day (0.8g/kg body weight) to ease glomerular workload.');
      constraints.push('Sodium restriction: < 2000 mg/day.');
      constraints.push('Serum potassium & phosphorus monitoring (moderate high-potassium/phosphorus additives if prescribed).');
      push(avoid, ['Inorganic phosphate food additives (E-numbers in processed snacks)', 'Excessive protein powders / high-dose creatine', 'High-sodium processed meals']);
      push(recommend, ['Controlled portions of high biological value protein (egg whites, poultry, tofu)', 'Adequate clean hydration (2.5L/day unless fluid restricted)']);
    }
    if (isHyperuricemic) {
      protocols.push('Low-Purine / Alkaline Uric Acid Control Protocol');
      constraints.push('Strict restriction of high-purine foods (< 100mg purines/day).');
      constraints.push('Eliminate high-fructose corn syrup & alcohol (especially beer).');
      constraints.push('Hydration target: >= 3.0 Liters clean water daily for renal clearance of urate.');
      push(avoid, ['Organ meats (liver, kidneys), red meat, venison', 'Beer, spirits, high-purine seafood (anchovies, sardines, shellfish)', 'High fructose corn syrup sweetened beverages']);
      push(recommend, ['Tart cherry juice / cherries (anthocyanins reduce urate)', 'Low-fat dairy / yogurt (uricosuric effect of orotic acid)', 'Lemon water, celery seeds, cucumbers', 'Ample alkaline vegetables']);
    }
    if (isLiver) {
      protocols.push('Hepatic Antioxidant & Anti-Inflammatory Protocol');
      push(constraints, ['Eliminate all alcohol consumption.', 'Strict avoidance of industrial fructose.']);
      push(avoid, ['Alcoholic beverages', 'Saturated fats & ultra-processed snacks', 'Excessive acetaminophen / OTC hepatotoxins']);
      push(recommend, ['Cruciferous vegetables (sulforaphane for phase II liver detox)', 'Artichokes, milk thistle tea, green tea (EGCG)', 'Garlic and turmeric (curcumin with black pepper)']);
    }
    if (isHypokalemic) {
      protocols.push('Electrolyte & Potassium Replenishment Protocol');
      constraints.push('Include potassium-dense whole foods daily (target 3500-4000 mg/day).');
      push(recommend, ['Tender coconut water', 'Avocados, bananas, spinach', 'Baked sweet potatoes', 'White beans / lentils']);
    }
    if (isHypothyroid) {
      protocols.push('Thyroid & Metabolic Support Protocol');
      constraints.push('Ensure adequate dietary iodine, selenium, and zinc; cook cruciferous vegetables thoroughly to neutralize goitrogens.');
      push(recommend, ['Brazil nuts (1-2 per day for selenium)', 'Iodized sea salt / sea vegetables', 'Pumpkin seeds (zinc)']);
    }

    var carbCal = targetKcal * (carbPct / 100.0);
    var proteinCal = targetKcal * (proteinPct / 100.0);
    var fatCal = targetKcal * (fatPct / 100.0);
    var carbG = pyRound(carbCal / 4.0), proteinG = pyRound(proteinCal / 4.0), fatG = pyRound(fatCal / 9.0);

    avoid = uniq(avoid); recommend = uniq(recommend);

    var plain = [];
    if (isDiabetic) plain.push("Swap white rice, maida breads, and sweets for phulka/chapati, dalia, idli, and dals - NIN's own GI table puts chapati at 52 against white rice at 73.");
    if (isDyslipidemic) plain.push('Replace ghee-heavy and deep-fried snacks (puri, vada, samosa, pakora) with steamed idli, dhokla, and roasted chana, and cook with mustard or groundnut oil.');
    if (isHypertensive) plain.push('Keep added salt under 1 teaspoon a day (NIN advises less than 5 g), skip pickles and papad, and lean on tender coconut water, spinach, and bottle gourd for potassium.');
    if (isHyperuricemic) plain.push('Stay well-hydrated with at least 3 liters of water daily and steer clear of beer, sodas, and organ meats to flush uric acid.');
    if (!plain.length) plain.push('Focus on colorful whole foods, clean protein, ample hydration, and 30 minutes of daily brisk walking.');

    var protocol = {
      energy: energy,
      protocols: protocols,
      macros: {
        calories: targetKcal,
        carbs: { grams: carbG, percentage: carbPct, calories: pyRound(carbCal) },
        protein: { grams: proteinG, percentage: proteinPct, calories: pyRound(proteinCal) },
        fat: { grams: fatG, percentage: fatPct, calories: pyRound(fatCal) }
      },
      micronutrient_targets: {
        sodium_max_mg: (isHypertensive || isRenal) ? 1800 : 2300,
        potassium_target_mg: (isHypertensive && !isRenal) ? 3800 : 3000,
        fiber_min_g: (isDiabetic || isDyslipidemic) ? 35 : 28,
        water_intake_liters: isHyperuricemic ? 3.0 : 2.5,
        vit_d_supplementation: vitDLow ? 'High Priority (Suggested 2000-4000 IU/day with doctor confirmation)' : 'Maintenance',
        vit_b12_supplementation: vitB12Low ? 'Suggested 500-1000 mcg sublingual with doctor confirmation' : 'Adequate dietary intake'
      },
      clinical_constraints: constraints,
      strictly_avoid: avoid.length ? avoid : ['Ultra-processed fast foods', 'Refined sugary drinks', 'Industrial trans-fats'],
      strongly_recommend: recommend.length ? recommend : ['Diverse colorful vegetables', 'Lean proteins', 'Healthy unsaturated fats', 'High fiber whole foods'],
      plain_summary: plain,
      lifestyle_habits: LIFESTYLE_HABITS.map(function (h) { return { title: h.title, desc: h.desc }; }),
      grocery_categories: JSON.parse(JSON.stringify(GROCERY_WESTERN)),
      structured_7day_meals: [],
      cuisine: 'Unavailable (NIN data not loaded)'
    };

    var days = [];
    try { days = buildIndian7DayMeals(profile, protocol); }
    catch (e) { days = []; protocol.indian_plan_error = e.name + ': ' + e.message; }
    if (days.length) {
      protocol.indian_7day_meals = days;
      protocol.structured_7day_meals = days;
      protocol.cuisine = 'Indian / hybrid (NIN-sourced)';
      var grocery = {};
      try { grocery = buildIndianGroceryCategories(profile, protocol); }
      catch (e) { protocol.indian_plan_error = 'grocery: ' + e.name + ': ' + e.message; }
      if (Object.keys(grocery).length) protocol.grocery_categories = grocery;
      var recs = [];
      try { recs = buildIndianRecommendations(profile, protocol); }
      catch (e) { protocol.indian_plan_error = 'recommendations: ' + e.name + ': ' + e.message; }
      if (recs.length) protocol.strongly_recommend = recs;
    }
    return protocol;
  }

  /* ------------------------------------------------------------------ */
  /* general_intake.py                                                   */
  /* ------------------------------------------------------------------ */

  var CONDITION_PATTERNS = [
    [['type 2 diabetes', 't2dm', 'diabetic', 'diabetes'], 'Type 2 Diabetes Mellitus', 'Blood Sugar / Metabolism', 'Severe'],
    [['prediabetes', 'pre-diabetes', 'prediabetic', 'impaired fasting glucose', 'borderline sugar'], 'Prediabetes / Impaired Fasting Glucose', 'Blood Sugar / Metabolism', 'Moderate'],
    [['cholesterol', 'dyslipid', 'triglyceride', 'ldl', 'lipid'], 'Dyslipidemia / Elevated Cholesterol', 'Heart & Arteries', 'Moderate'],
    [['kidney', 'renal', 'ckd', 'creatinine', 'egfr', 'nephro'], 'Renal Impairment / CKD Risk', 'Kidney Function', 'Moderate'],
    [['gout', 'uric acid', 'purine', 'hyperuricemia'], 'Hyperuricemia (Uric Acid & Gout Risk)', 'Uric Acid & Joints', 'Moderate'],
    [['fatty liver', 'nafld', 'liver', 'hepatic', 'sgpt', 'sgot'], 'Elevated Liver Enzymes (Hepatic Stress / NAFLD)', 'Liver Function', 'Moderate'],
    [['hypothyroid', 'thyroid', 'tsh'], 'Elevated TSH (Sluggish Thyroid / Hypothyroidism)', 'Thyroid', 'Moderate'],
    [['high blood pressure', 'hypertension', 'hypertensive', 'bp is high', 'high bp'], 'Stage 1 Hypertension', 'Blood Pressure & Vessels', 'Moderate'],
    [['vitamin d', 'vit d', 'vitamin-d'], 'Vitamin D Deficiency', 'Immunity & Bone Health', 'Moderate'],
    [['vitamin b12', 'b12'], 'Vitamin B12 Deficiency', 'Nerves & Blood', 'Moderate']
  ];
  var GNUM = '(\\d{1,3}(?:\\.\\d+)?)';
  var DIET_ASSUMPTION = 'Diet preference not stated - assumed vegetarian';

  function parseGeneralQuery(query) {
    var q = query.toLowerCase();
    var out = { assumptions: [] };
    var h = new RegExp(GNUM + '\\s*(?:cm\\b|centim)').exec(q) || new RegExp(GNUM + '\\s*m\\b').exec(q);
    var w = new RegExp(GNUM + '\\s*(?:kgs?\\b|kilo)').exec(q);
    var lb = new RegExp(GNUM + '\\s*(?:lbs?\\b|pounds?)').exec(q);
    var age = new RegExp('(?:age[d]?\\s*(?:is|:)?\\s*)' + GNUM).exec(q) ||
      new RegExp(GNUM + '\\s*(?:years?\\s*old|yrs?\\s*old|y/?o\\b)').exec(q) ||
      new RegExp('\\bi\\s*am\\s*' + GNUM + '(?!\\s*(?:cm|kg|kgs|m\\b|lbs))').exec(q) ||
      new RegExp('\\b' + GNUM + '\\s*(?:year|yr)s?\\b').exec(q);

    var height = h ? parseFloat(h[1]) : null;
    if (height !== null && height < 3.0) height *= 100.0;
    var weight = w ? parseFloat(w[1]) : (lb ? pyRound(parseFloat(lb[1]) * 0.453592, 1) : null);

    var gender;
    if (/\b(female|woman|girl|she|her)\b/.test(q)) gender = 'Female';
    else if (/\b(male|man|boy|he|his)\b/.test(q)) gender = 'Male';
    else { gender = 'Male'; out.assumptions.push('Sex not stated - Mifflin-St Jeor computed as male'); }

    if (!age) out.assumptions.push('Age not stated - assumed 45 years');
    if (!height || !weight) out.assumptions.push('Height/weight not stated - used clinical baseline for the energy target');

    var diet, dietStated = true;
    if (/\b(vegan)\b/.test(q)) diet = 'Vegan';
    else if (/\b(non-?veg|chicken|egg|fish|meat|mutton)\b/.test(q)) diet = 'Non-Vegetarian';
    else if (/\b(veg|vegetarian)\b/.test(q)) diet = 'Vegetarian';
    else { diet = 'Vegetarian'; dietStated = false; out.assumptions.push(DIET_ASSUMPTION); }

    var activity = 'Sedentary', activityStated = true;
    if (/\b(very active|athlete|heavy work|gym daily)\b/.test(q)) activity = 'Very Active';
    else if (/\b(active|exercise|workout|walk daily|moderate)\b/.test(q)) activity = 'Moderate';
    else activityStated = false;
    out.diet_stated = dietStated; out.activity_stated = activityStated;

    out.height_cm = height; out.weight_kg = weight;
    out.age = age ? Math.trunc(parseFloat(age[1])) : null;
    out.gender = gender; out.dietary_preference = diet; out.activity_level = activity;
    return out;
  }

  function detectConditions(query) {
    var q = query.toLowerCase();
    var flags = [], seen = new Set();
    CONDITION_PATTERNS.forEach(function (p) {
      var condition = p[1];
      if (seen.has(condition)) return;
      if (p[0].some(function (k) { return q.indexOf(k) !== -1; })) {
        if (condition === 'Prediabetes / Impaired Fasting Glucose' && seen.has('Type 2 Diabetes Mellitus')) return;
        if (condition === 'Type 2 Diabetes Mellitus' && q.indexOf('prediabet') !== -1) return;
        flags.push({
          condition: condition, severity: p[3], marker: 'Self-reported (no laboratory value supplied)', organ: p[2],
          plain_meaning: 'Stated by the user rather than measured from a lab report.',
          action_tip: 'Upload a blood test PDF to replace this with measured biomarker values.'
        });
        seen.add(condition);
      }
    });
    return flags;
  }

  function buildGeneralProfile(query) {
    var parsed = parseGeneralQuery(query);
    var bmi = null;
    if (T(parsed.height_cm) && T(parsed.weight_kg)) {
      var hm = parsed.height_cm / 100.0;
      bmi = pyRound(parsed.weight_kg / (hm * hm), 1);
    }
    var male = parsed.gender === 'Male';
    return {
      demographics: {
        name: 'Guest', age: T(parsed.age) ? parsed.age : 45, gender: parsed.gender,
        weight_kg: T(parsed.weight_kg) ? parsed.weight_kg : (male ? 70.0 : 58.0),
        height_cm: T(parsed.height_cm) ? parsed.height_cm : (male ? 170.0 : 158.0),
        bmi: bmi, bp_string: 'Not measured', dietary_preference: parsed.dietary_preference, allergies: [],
        activity_level: parsed.activity_level
      },
      biomarkers: {}, clinical_flags: detectConditions(query), raw_text_preview: query,
      data_source: 'user statement (no laboratory report)', assumptions: parsed.assumptions
    };
  }

  var MEAL_SLOTS = ['breakfast', 'mid_morning', 'lunch', 'snack', 'dinner', 'bedtime'];

  function checkConstraintCompliance(protocol) {
    var macros = protocol.macros || {};
    var target = macros.calories || 0;
    var days = protocol.structured_7day_meals || [];
    var avoid = (protocol.strictly_avoid || []).map(function (a) { return a.toLowerCase(); });

    var checks = [], passed = 0, deviations = [];
    days.forEach(function (d) {
      var tot = d.day_total_kcal;
      if (tot === null || tot === undefined) {
        tot = MEAL_SLOTS.reduce(function (a, s) { return a + ((d[s] || {}).kcal || 0); }, 0);
      }
      deviations.push(Math.abs(tot - target));
    });
    var worst = deviations.length ? Math.max.apply(null, deviations) : null;

    var okCal = worst !== null && !!target && worst <= Math.max(150, 0.1 * target);
    checks.push(['Daily calories converge on the prescribed target', okCal,
      'max deviation ' + (worst !== null ? pyRound(worst) : 'n/a') + ' kcal']);
    passed += okCal ? 1 : 0;

    var leaked = [];
    days.forEach(function (d) {
      MEAL_SLOTS.forEach(function (slot) {
        var name = ((d[slot] || {}).name || '').toLowerCase();
        avoid.forEach(function (a) {
          var token = a.replace(/[^a-z ]/g, '').trim();
          if (token && name.indexOf(token) !== -1) leaked.push('Day ' + d.day + ' ' + slot + ': ' + name);
        });
      });
    });
    var okAvoid = leaked.length === 0;
    checks.push(['No contraindicated food appears in any meal', okAvoid,
      okAvoid ? 'clean across ' + days.length + ' days' : leaked.slice(0, 3).join('; ')]);
    passed += okAvoid ? 1 : 0;

    var nProt = (protocol.protocols || []).length;
    var okProt = nProt >= 1;
    checks.push(['Clinical protocols stacked for the stated conditions', okProt, nProt + ' active']);
    passed += okProt ? 1 : 0;

    var okSrc = days.length > 0 && days.some(function (d) {
      return ['breakfast', 'lunch', 'dinner'].some(function (s) { return !!(d[s] || {}).source; });
    });
    checks.push(['Meal calories traceable to a published food table', okSrc, okSrc ? 'NIN / ICMR tables' : 'not sourced']);
    passed += okSrc ? 1 : 0;

    var score = checks.length ? pyRound(100.0 * passed / checks.length) : 0;
    return {
      checks: checks, score: score,
      verdict: score === 100 ? 'PASSED - constraint compliance' : (score >= 50 ? 'PARTIAL - review flagged rows' : 'FAILED'),
      scope: 'Constraint compliance only - no biomarker cross-check (no lab report supplied)'
    };
  }

  function buildComparisonRows(profile, protocol, audit) {
    var macros = protocol.macros || {};
    var energy = protocol.energy || {};
    var flags = (profile.clinical_flags || []).map(function (f) { return f.condition; });
    var protos = (protocol.protocols || []).filter(function (p) { return p !== 'Balanced Whole-Foods Protocol'; });
    var avoid = protocol.strictly_avoid || [];
    var days = protocol.structured_7day_meals || [];
    function g(key) { return (macros[key] || {}).grams; }

    var rows = [
      { dimension: 'Energy target', llm: 'Not computed - no BMR/TDEE arithmetic',
        agent: pyS(macros.calories) + ' kcal/day (BMR ' + pyS(energy.bmr) + ', TDEE ' + pyS(energy.tdee) + ', Mifflin-St Jeor)' },
      { dimension: 'Macronutrient split', llm: 'Not prescribed in grams',
        agent: 'Carb ' + pyS(g('carbs')) + 'g / Protein ' + pyS(g('protein')) + 'g / Fat ' + pyS(g('fat')) + 'g' },
      { dimension: 'Conditions detected', llm: 'Read as prose only', agent: flags.length ? flags.join(', ') : 'None stated' },
      { dimension: 'Clinical protocols stacked', llm: 'None - single pass, no rules engine',
        agent: protos.length ? protos.join('; ') : 'Balanced whole-foods baseline' },
      { dimension: 'Contraindicated foods enforced', llm: 'Not enforced - may suggest anything',
        agent: avoid.length + ' items excluded before generation' },
      { dimension: 'Food calorie source', llm: "Model's training data - not verifiable",
        agent: "ICMR-NIN 'Dietary Guidelines for Indians' tables" },
      { dimension: '7-day meal plan', llm: 'Prose only, calories self-estimated',
        agent: days.length + ' structured days, portions and kcal from the NIN tables' },
      { dimension: 'Safety audit', llm: 'None', agent: pyS(audit.score !== undefined ? audit.score : 0) + '/100 - ' + (audit.verdict !== undefined ? audit.verdict : 'n/a') },
      { dimension: 'Reproducibility', llm: 'Varies between runs (temperature 0.5)',
        agent: 'Identical output for identical input (deterministic engine)' },
      { dimension: 'Evidence basis', llm: 'General training knowledge',
        agent: 'Self-reported conditions - no laboratory values (upload a PDF for biomarker grounding)' }
    ];
    var giSwap = flags.some(function (f) { return f.indexOf('Diabet') !== -1 || f.indexOf('Glucose') !== -1 || f.indexOf('Prediabet') !== -1; });
    if (giSwap) {
      rows.splice(6, 0, { dimension: 'Glycemic-index aware staple', llm: 'No GI table consulted',
        agent: 'Chapati/phulka (GI 52) substituted for white rice (GI 73), NIN Annexure 10' });
    }
    return rows;
  }

  var GENERAL_SYSTEM = "You are the NutriAgent clinical nutrition engine's writing layer. " +
    'You never invent calorie figures: every number you state was supplied to you above.';

  /**
   * overrides (all optional): {allergies: string[], dietary_preference, activity_level, max_words}.
   * allergies always apply; diet / activity apply only when the query did not state them.
   * Without overrides the result is identical to Python's run_nutriagent_general.
   */
  function prepareGeneral(query, overrides) {
    overrides = overrides || {};
    var maxWords = overrides.max_words === undefined ? 380 : overrides.max_words;
    var profile = buildGeneralProfile(query);
    var parsed = parseGeneralQuery(query);
    var demoO = profile.demographics;
    if (overrides.allergies && overrides.allergies.length) demoO.allergies = overrides.allergies.slice();
    if (overrides.dietary_preference && !parsed.diet_stated) {
      demoO.dietary_preference = overrides.dietary_preference;
      profile.assumptions = profile.assumptions.filter(function (a) { return a !== DIET_ASSUMPTION; });
      profile.assumptions.push('Diet preference taken from your settings: ' + overrides.dietary_preference);
    }
    if (overrides.activity_level && !parsed.activity_stated) {
      demoO.activity_level = overrides.activity_level;
      profile.assumptions.push('Activity level taken from your settings: ' + overrides.activity_level);
    }
    var protocol = computeProtocol(profile);
    var audit = checkConstraintCompliance(protocol);
    var rows = buildComparisonRows(profile, protocol, audit);
    var ninBlock = '';
    try { ninBlock = buildNinReferenceBlock(profile, protocol); } catch (e) { ninBlock = ''; }

    var macros = protocol.macros || {};
    var demo = profile.demographics;
    var energy = protocol.energy || {};
    var prompt = '### User question:\n' + query + '\n\n' +
      '### Deterministic targets already computed for this person (use these exact numbers):\n' +
      '- Energy: ' + pyS(macros.calories) + ' kcal/day (BMR ' + pyS(energy.bmr) + ', TDEE ' + pyS(energy.tdee) + ')\n' +
      '- Carbohydrate ' + pyS((macros.carbs || {}).grams) + 'g | Protein ' + pyS((macros.protein || {}).grams) + 'g | Fat ' + pyS((macros.fat || {}).grams) + 'g\n' +
      '- Profile: ' + pyS(demo.age) + 'y ' + demo.gender + ', ' + pf(demo.weight_kg) + 'kg, ' + pf(demo.height_cm) + 'cm, BMI ' + pf(demo.bmi) + ', ' + demo.dietary_preference + ', ' + demo.activity_level + '\n' +
      '- Active clinical protocols: ' + (protocol.protocols || []).join(', ') + '\n' +
      '- STRICTLY AVOID: ' + (protocol.strictly_avoid || []).join(', ') + '\n\n' +
      ninBlock + '\n\n' +
      '### Task:\n' +
      "Answer the user's question in under " + maxWords + ' words, using the numbers above verbatim.\n' +
      'Build meals from the verified Indian food table; quote its kcal values.\n' +
      'State clearly that these targets come from the stated details, not from blood tests.\n' +
      'Do not use emojis.';

    return {
      profile: profile, protocol: protocol, audit: audit, comparison_rows: rows,
      assumptions: profile.assumptions || [], nin_block: ninBlock, prompt: prompt, system: GENERAL_SYSTEM
    };
  }

  return {
    setNinData: setNinData,
    buildHealthProfile: buildHealthProfile,
    validateLabReport: validateLabReport,
    parsePatientDemographics: parsePatientDemographics,
    extractBiomarkers: extractBiomarkers,
    calculateBmrTdee: calculateBmrTdee,
    computeProtocol: computeProtocol,
    buildNinReferenceBlock: buildNinReferenceBlock,
    buildIndian7DayMeals: buildIndian7DayMeals,
    buildIndianGroceryCategories: buildIndianGroceryCategories,
    buildIndianRecommendations: buildIndianRecommendations,
    prepareGeneral: prepareGeneral,
    buildGeneralProfile: buildGeneralProfile,
    parseGeneralQuery: parseGeneralQuery,
    detectConditions: detectConditions,
    checkConstraintCompliance: checkConstraintCompliance,
    buildComparisonRows: buildComparisonRows,
    isAllowed: isAllowed,
    exclusionReason: exclusionReason,
    flagSet: flagSet,
    allFoods: allFoods,
    pyRound: pyRound,
    STANDARD_REFERENCE_RANGES: STANDARD_REFERENCE_RANGES,
    ALLERGEN_OPTIONS: ALLERGEN_OPTIONS,
    DIET_OPTIONS: DIET_OPTIONS,
    ACTIVITY_OPTIONS: ACTIVITY_OPTIONS
  };
});
