/* agents.js - LLM layer for NutriAgent mobile.
 * Prompts are ported from agents.py / general_intake.py. Transport goes through the native Android bridge
 * (Ollama rejects browser Origins), falling back to fetch() when running in a normal browser for testing.
 * Every agent has a built-in fallback that is computed from the patient's own data - no canned "PASSED 95/100". */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory(); else root.NutriAgents = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const E = () => (typeof NutriEngine !== 'undefined' ? NutriEngine : (typeof globalThis !== 'undefined' && globalThis.NutriEngine));

  // ---------------------------------------------------------------- transport
  const pending = new Map();
  let seq = 0;
  if (typeof window !== 'undefined') {
    window.__nativeCb = function (id, ok, body) {
      const p = pending.get(id);
      if (!p) return;
      pending.delete(id);
      ok ? p.resolve(body) : p.reject(new Error(body));
    };
  }

  function makeSignal() {
    const cbs = [];
    return {
      cancelled: false,
      cancel() { if (this.cancelled) return; this.cancelled = true; cbs.splice(0).forEach(f => f()); },
      onCancel(f) { if (this.cancelled) f(); else cbs.push(f); },
    };
  }

  function http(method, url, body, timeoutSec, signal) {
    return new Promise((resolve, reject) => {
      if (signal && signal.cancelled) return reject(new Error('cancelled'));
      if (typeof window !== 'undefined' && window.Native && window.Native.http) {
        const id = 'h' + (++seq);
        pending.set(id, { resolve, reject });
        if (signal) signal.onCancel(() => { if (pending.delete(id)) reject(new Error('cancelled')); });
        window.Native.http(id, method, url, body || '', timeoutSec || 60);
        return;
      }
      const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timer = setTimeout(() => ctl && ctl.abort(), (timeoutSec || 60) * 1000);
      if (signal) signal.onCancel(() => { ctl && ctl.abort(); reject(new Error('cancelled')); });
      fetch(url, { method, body: body || undefined, headers: body ? { 'Content-Type': 'application/json' } : undefined, signal: ctl && ctl.signal })
        .then(r => r.text().then(t => (r.ok ? resolve(t) : reject(new Error('HTTP ' + r.status + ': ' + t)))))
        .catch(e => reject(e)).finally(() => clearTimeout(timer));
    });
  }

  // ---------------------------------------------------------------- Ollama client
  function Llm(cfg) {
    cfg = cfg || {};
    this.url = String(cfg.url || '').trim().replace(/\/+$/, '');
    if (this.url && !/^https?:\/\//i.test(this.url)) this.url = 'http://' + this.url;
    this.model = cfg.model || 'qwen2.5:7b';
    this.timeout = cfg.timeoutSec || 600;
    this.enabled = !!(cfg.enabled && this.url);
  }
  Llm.prototype.check = async function () {
    if (!this.url) return { state: 'off', message: 'No AI server address set.', models: [] };
    try {
      const txt = await http('GET', this.url + '/api/tags', '', 8);
      const models = (JSON.parse(txt).models || []).map(m => m.name);
      const base = this.model.split(':')[0];
      const ready = models.includes(this.model) || models.some(n => n.indexOf(base) !== -1);
      return ready
        ? { state: 'online', message: "Connected. Model '" + this.model + "' is ready.", models }
        : { state: 'nomodel', message: "Server reachable, but model '" + this.model + "' is not installed. Run: ollama pull " + this.model, models };
    } catch (e) {
      return { state: 'offline', message: friendlyNetError(e, this.url), models: [] };
    }
  };
  Llm.prototype.generate = async function (prompt, system, temperature, signal) {
    const payload = {
      model: this.model, prompt: prompt, system: system || '', stream: false, keep_alive: '30m',
      options: { temperature: temperature == null ? 0.3 : temperature, top_p: 0.9, num_ctx: 16384, num_predict: 4096 },
    };
    const txt = await http('POST', this.url + '/api/generate', JSON.stringify(payload), this.timeout, signal);
    const out = (JSON.parse(txt).response || '').trim();
    if (!out) throw new Error('The model returned an empty answer');
    return out;
  };

  function friendlyNetError(e, url) {
    const m = String((e && e.message) || e);
    if (/timeout|timed out/i.test(m)) return "The server at " + url + " did not answer in time. Is the PC on and Ollama running?";
    if (/refused|ECONNREFUSED/i.test(m)) return "Connection refused by " + url + ". Start Ollama on that machine (OLLAMA_HOST=0.0.0.0 ollama serve).";
    if (/UnknownHost|Unable to resolve|ENOTFOUND/i.test(m)) return "Could not find '" + url + "'. Check the address and that your phone is on the same Wi-Fi.";
    if (/Cleartext|CLEARTEXT/i.test(m)) return "Cleartext HTTP was blocked. Use an http:// address on your local network.";
    return m;
  }

  // ---------------------------------------------------------------- helpers
  const f = (v, d) => (v === undefined || v === null || v === '' ? (d === undefined ? 'N/A' : d) : v);
  const names = flags => (flags || []).map(x => x.condition);
  const abnormalOf = profile => Object.values(profile.biomarkers || {}).filter(b => b.status !== 'Normal');

  function followUps(profile) {
    const t = names(profile.clinical_flags).join(' | ').toLowerCase();
    const out = [];
    if (/diabet|glucose|glycem/.test(t)) out.push('HbA1c and fasting glucose in about 3 months');
    if (/lipid|cholesterol/.test(t)) out.push('Fasting lipid profile in about 12 weeks');
    if (/renal|ckd/.test(t)) out.push('Creatinine, eGFR and electrolytes in about 3 months');
    if (/uric|gout/.test(t)) out.push('Serum uric acid in 8-12 weeks');
    if (/liver|hepat/.test(t)) out.push('Liver function tests (ALT/AST) in about 12 weeks');
    if (/tsh|thyroid/.test(t)) out.push('TSH (and free T3/T4 if advised) in 6-8 weeks');
    if (/hypertension/.test(t)) out.push('Home blood-pressure log; clinical review in about 4 weeks');
    if (/vitamin d|vitamin b12/.test(t)) out.push('Re-check vitamin levels about 3 months after any supplementation');
    if (/potassium|kalemia/.test(t)) out.push('Repeat serum potassium within 1-2 weeks');
    if (!out.length) out.push('Routine annual health panel');
    return out;
  }

  // ---------------------------------------------------------------- built-in (offline) text
  function builtinAnalysis(profile, protocol) {
    const bms = Object.values(profile.biomarkers || {});
    const abn = abnormalOf(profile);
    const flags = profile.clinical_flags || [];
    const L = [];
    L.push('### Clinical summary');
    if (!bms.length && !flags.length) {
      L.push('No standard biomarkers could be read from this document, so no clinical flags were raised. The plan below uses your stated profile only.');
    } else {
      L.push('**' + bms.length + '** biomarkers were read from your report and **' + abn.length + '** sit outside the reference range. ' +
        (flags.length ? 'The engine raised **' + flags.length + '** clinical flag' + (flags.length > 1 ? 's' : '') + ': ' + names(flags).join(', ') + '.' : 'No clinical flags were raised.'));
    }
    if (flags.length) {
      L.push('', '### 1. Clinical indicators');
      flags.forEach(x => L.push('- **' + x.condition + '** (' + x.severity + ') - ' + x.marker + '. ' + (x.plain_meaning || '') + ' *Action:* ' + (x.action_tip || '')));
    }
    if (abn.length) {
      L.push('', '### 2. Markers outside the reference range');
      abn.forEach(b => L.push('- **' + b.name + '**: ' + b.value + ' ' + b.unit + ' (reference ' + b.range + ') - **' + b.status + '**. ' + (b.plain_desc || '')));
    }
    L.push('', '### 3. Directives for the nutrition plan');
    L.push('Active protocols: ' + (protocol.protocols || []).join('; ') + '.');
    (protocol.clinical_constraints || []).forEach(c => L.push('- ' + c));
    L.push('', '*Generated by the built-in on-device clinical engine. Connect an AI server in Settings for a deeper narrative analysis.*');
    return L.join('\n');
  }

  function builtinDietNotes(protocol) {
    const m = protocol.macros || {}, mi = protocol.micronutrient_targets || {};
    return [
      '### Diet strategy',
      '- **Daily energy**: ' + m.calories + ' kcal | Carbs ' + (m.carbs || {}).grams + 'g (' + (m.carbs || {}).percentage + '%) | Protein ' + (m.protein || {}).grams + 'g (' + (m.protein || {}).percentage + '%) | Fat ' + (m.fat || {}).grams + 'g (' + (m.fat || {}).percentage + '%)',
      '- **Targets**: fibre >= ' + mi.fiber_min_g + ' g, sodium < ' + mi.sodium_max_mg + ' mg, water ' + mi.water_intake_liters + ' L per day',
      '- **Emphasise**: ' + (protocol.strongly_recommend || []).join('; '),
      '- **Avoid**: ' + (protocol.strictly_avoid || []).join('; '),
    ].join('\n');
  }

  function builtinEvaluation(profile, protocol, audit) {
    const d = profile.demographics || {}, m = protocol.macros || {}, mi = protocol.micronutrient_targets || {};
    const flags = profile.clinical_flags || [], abn = abnormalOf(profile);
    const L = [];
    L.push('### 1. Audit result');
    L.push('- **Verdict**: ' + audit.verdict);
    L.push('- **Constraint score**: ' + audit.score + '/100');
    (audit.checks || []).forEach(c => L.push('- ' + (c[1] ? 'PASS' : 'FAIL') + ' - ' + c[0] + ' (' + c[2] + ')'));
    L.push('', '### 2. Doctor brief (for the attending physician)');
    L.push('- **Patient**: ' + f(d.name, 'Patient') + ' (' + f(d.age) + ' y, ' + f(d.gender) + ') | BMI ' + f(d.bmi) + ' | BP ' + f(d.bp_string));
    L.push('- **Clinical flags**: ' + (flags.length ? names(flags).join('; ') : 'none raised'));
    if (abn.length) L.push('- **Out-of-range markers**: ' + abn.map(b => b.name + ' ' + b.value + ' ' + b.unit + ' (' + b.status + ')').join('; '));
    L.push('- **Dietary prescription**: ' + m.calories + ' kcal/day, carbs ' + (m.carbs || {}).percentage + '% / protein ' + (m.protein || {}).percentage + '% / fat ' + (m.fat || {}).percentage + '%; sodium < ' + mi.sodium_max_mg + ' mg; fibre >= ' + mi.fiber_min_g + ' g; water ' + mi.water_intake_liters + ' L');
    L.push('- **Protocols applied**: ' + (protocol.protocols || []).join('; '));
    L.push('- **Suggested follow-up**:');
    followUps(profile).forEach(x => L.push('  - ' + x));
    L.push('', '### 3. Plain-language summary');
    (protocol.plain_summary || []).forEach(x => L.push('- ' + x));
    L.push('', '> This brief was produced by software from the numbers in the report. It is educational and does not replace clinical judgement.');
    return L.join('\n');
  }

  // ---------------------------------------------------------------- AI agents (prompts ported from agents.py)
  const SYS_ANALYSIS = "You are an expert Clinical Diagnostic & Medical Analysis AI Agent.\nYour role is to deeply analyze extracted medical lab biomarkers, patient demographics, and health metrics.\nYou must:\n1. Systematically interpret all abnormal biomarkers (Elevated, Low, Borderline).\n2. Identify underlying metabolic patterns, organ stress (Hepatic, Renal, Cardiovascular, Endocrine), and nutritional deficiencies.\n3. Group findings by priority: High Priority / Acute Risks vs. Secondary / Preventative Concerns.\n4. Maintain high clinical accuracy, citing specific biomarker values and reference ranges.\n5. Provide clear, objective physiological explanations for why these markers are altered and how they interconnect.";
  const SYS_NUTRITION = "You are a Lead Clinical Dietitian & Medical Nutrition Specialist AI Agent.\nYour role is to translate clinical analysis and strict deterministic nutrition parameters into an actionable, delicious, and medically precise Diet Plan.\nYou must:\n1. Adhere strictly to the provided Calorie targets, Macronutrient ratios (Carbs, Protein, Fats), and Clinical Constraints (Sodium, Fiber, Purines, Glycemic Index).\n2. Never include foods listed in the 'Strictly Avoid' list.\n3. Emphasize functional superfoods and ingredients listed in the 'Strongly Recommend' list.\n4. Structure clear, practical meal schedules (Breakfast, Mid-Morning Snack, Lunch, Evening Snack, Dinner, Hydration).\n5. For each meal, specify exact ingredients, approximate portion sizes, key macro contribution, and the therapeutic rationale (e.g. \"Contains oats rich in beta-glucan to reduce LDL cholesterol\").";
  const SYS_AUDIT = "You are a Senior Chief Medical Auditor & Clinical Quality Assurance AI Agent.\nYour job is to perform an exhaustive AUDIT on the proposed Diet Plan and Clinical Analysis.\nYou must:\n1. Verify Biomarker Safety & Contraindications: Check that NO prohibited ingredients for the patient's conditions are present.\n2. Verify Macro/Calorie Compliance: Confirm the meal plan matches the deterministic caloric and macronutrient targets.\n3. Compute an objective Clinical Safety Score from 0 to 100%.\n4. Issue an Audit Status: \"PASSED - Clinically Validated & Safe\" or \"REVISED - Minor Adjustments Advised\".\n5. Produce two dedicated deliverables:\n   A. **Doctor Brief**: Clinical, concise medical handoff memo for the primary care physician detailing biomarkers, rationale, and recommended follow-up tests.\n   B. **Patient Plain-Language Summary**: Encouraging, easy-to-understand lifestyle guide empowering the patient.";
  const SYS_CONSULT = "You are the Senior Clinical Nutritionist & Lab Diagnostic Consultant AI.\nYou have complete access to the patient's uploaded laboratory test results, extracted biomarkers, clinical analysis, tailored diet plan, and safety audit findings.\nYour role is to answer any follow-up questions from the patient or clinician with high accuracy, clarity, and empathy.\nGuidelines:\n1. Ground your answers directly in the patient's specific lab numbers, reference ranges, and prescribed diet plan.\n2. Provide actionable, practical advice (e.g. food substitutions, daily routine tips, timing of meals/tests, explanation of medical terms).\n3. If the user asks for food swaps, ensure the substitutes strictly respect their clinical constraints (e.g., low GI, low sodium, hepatic-friendly, low-purine).\n4. Maintain a supportive, professional, and clear tone without unnecessary fluff.\nKeep answers short enough to read comfortably on a phone.";
  const SYS_PLAIN = 'You are a general-purpose AI assistant. Answer health and nutrition questions to the best of your ability based on your training knowledge. Do not use emojis.';

  function analysisPrompt(profile) {
    const d = profile.demographics || {};
    const bm = Object.values(profile.biomarkers || {}).map(i => '- **' + i.name + '**: ' + i.value + ' ' + i.unit + ' [Normal: ' + i.range + '] -> **' + i.status + '**');
    const fl = (profile.clinical_flags || []).map(x => '- ' + x.condition + ' (Severity: ' + x.severity + ', Marker: ' + x.marker + ')');
    return '### Patient Profile:\n- Age: ' + f(d.age) + ' | Gender: ' + f(d.gender) + '\n- BMI: ' + f(d.bmi) + ' | Blood Pressure: ' + f(d.bp_string) +
      '\n- Weight: ' + f(d.weight_kg) + ' kg | Height: ' + f(d.height_cm) + ' cm\n\n### Extracted Biomarker Values:\n' + (bm.length ? bm.join('\n') : 'No specific biomarkers parsed by regex.') +
      '\n\n### Pre-identified Clinical Flags:\n' + fl.join('\n') + '\n\n### Lab Document Excerpt:\n' + (profile.raw_text_preview || '') +
      '\n\n---\n### Your Task as Analysis Agent:\nPlease produce a comprehensive, structured clinical analysis:\n1. **Executive Clinical Summary**: A concise 3-4 sentence overview of the patient\'s overall metabolic and physiological health state.\n2. **Key Biomarker Anomalies & Pathophysiological Impact**:\n   - Breakdown of each elevated/low marker.\n   - Explain the physiological mechanism (e.g. how high LDL + low HDL impacts endothelial health, or how HbA1c correlates with average glucose and microvascular risks).\n3. **Primary Health Risk Stratification**:\n   - **Tier 1 (High Priority / Immediate Attention)**\n   - **Tier 2 (Moderate Priority / Lifestyle Reversible)**\n   - **Tier 3 (Nutritional & Micronutrient Optimization)**\n4. **Metabolic Interconnections**: Explain how the findings relate to one another (e.g. metabolic syndrome triad, insulin resistance driving dyslipidemia or uric acid elevation).\n5. **Key Dietary & Clinical Directives for the Nutrition Agent**: Explicit physiological recommendations for what dietary levers must be targeted.';
  }

  function nutritionPrompt(profile, analysisText, protocol) {
    const d = profile.demographics || {}, m = protocol.macros || {}, en = protocol.energy || {}, mi = protocol.micronutrient_targets || {};
    let nin = '';
    try { nin = E().buildNinReferenceBlock(profile, protocol) || ''; } catch (e) { nin = ''; }
    return '### Patient Demographics:\n- Age: ' + f(d.age) + ' | Gender: ' + f(d.gender) + ' | Weight: ' + f(d.weight_kg) + ' kg | BMI: ' + f(d.bmi) +
      '\n\n### Clinical Analysis Insights:\n' + String(analysisText || '').slice(0, 1200) +
      '\n\n### Deterministic Nutrition Targets (MANDATORY CLINICAL CONSTRAINTS):\n- **Target Calories**: ' + f(m.calories, 1800) + ' kcal/day (BMR: ' + en.bmr + ' kcal, TDEE: ' + en.tdee + ' kcal)' +
      '\n- **Macronutrient Distribution**:\n  * Carbohydrates: ' + (m.carbs || {}).grams + 'g (' + (m.carbs || {}).percentage + '%) - Focus on Low Glycemic Index & High Fiber' +
      '\n  * Protein: ' + (m.protein || {}).grams + 'g (' + (m.protein || {}).percentage + '%) - Lean, high biological value' +
      '\n  * Healthy Fats: ' + (m.fat || {}).grams + 'g (' + (m.fat || {}).percentage + '%) - High MUFA & Omega-3, SFA < 7%' +
      '\n- **Micronutrient Rules**:\n  * Max Sodium: ' + mi.sodium_max_mg + ' mg/day\n  * Min Fiber: ' + mi.fiber_min_g + ' g/day\n  * Water Intake: ' + mi.water_intake_liters + ' Liters/day' +
      '\n- **Active Protocols**: ' + (protocol.protocols || []).join(', ') + '\n- **Clinical Constraints**: ' + (protocol.clinical_constraints || []).join('; ') +
      '\n- **STRICTLY AVOID FOODS**: ' + (protocol.strictly_avoid || []).join(', ') + '\n- **STRONGLY RECOMMENDED FOODS**: ' + (protocol.strongly_recommend || []).join(', ') +
      '\n\n' + nin + '\n\n---\n### Your Task as Nutrition Agent:\nGenerate a thorough, personalized, clinical diet plan.\nBuild meals from the VERIFIED INDIAN FOOD TABLE above wherever it covers the slot,\nquoting its NIN calorie values verbatim; fall back to a non-Indian item only when the\ntable has no equivalent, and mark any such item "(non-NIN estimate)".\n1. **Clinical Diet Strategy Overview**: Explanation of how this macro/micro distribution specifically targets the patient\'s abnormal biomarkers.\n2. **7-Day Comprehensive Meal Framework**:\n   - Provide a detailed Day 1-7 plan with specific meal breakdowns for each day:\n     * **Breakfast** (with estimated kcal & carbs/protein/fat)\n     * **Mid-Morning Booster** (e.g. herbal infusions, specific nuts/seeds)\n     * **Lunch** (balanced whole food main meal)\n     * **Afternoon Snack / Energy Fuel**\n     * **Dinner** (light, anti-inflammatory, low-sodium evening meal)\n     * **Bedtime / Hydration Protocol**\n   - For key items, explain the *Biomarker Therapeutic Target* (e.g. "Walnuts: rich in ALA omega-3 to improve endothelial health and lower triglycerides").\n3. **Daily Preparation & Culinary Tips**: Smart cooking methods (steaming, poaching, air-frying with EVOO vs deep frying), spice integration (turmeric, garlic, cinnamon, fenugreek), and dining out guidance.\n4. **Hydration & Herbal Infusion Protocol**: Timing of fluids, electrolyte balance, and kidney/liver protective teas.';
  }

  function auditPrompt(profile, analysisText, dietText, protocol) {
    const d = profile.demographics || {}, m = protocol.macros || {};
    const bl = Object.values(profile.biomarkers || {}).map(b => b.name + ': ' + b.value + ' ' + b.unit + ' (' + b.status + ')');
    return '### Patient Profile:\n- Age: ' + f(d.age, 'None') + ' | Gender: ' + f(d.gender, 'None') + ' | BMI: ' + f(d.bmi, 'None') + ' | BP: ' + f(d.bp_string, 'None') +
      '\n\n### Clinical Flags & Biomarkers:\n- Flags: ' + names(profile.clinical_flags).join(', ') + '\n- Biomarkers: ' + bl.join('; ') +
      '\n\n### Mandatory Clinical Constraints:\n- Target Calories: ' + m.calories + ' kcal (Carbs: ' + (m.carbs || {}).percentage + '%, Protein: ' + (m.protein || {}).percentage + '%, Fat: ' + (m.fat || {}).percentage + '%)' +
      '\n- Constraints: ' + (protocol.clinical_constraints || []).join('; ') + '\n- Forbidden Foods: ' + (protocol.strictly_avoid || []).join(', ') +
      '\n\n### Proposed Diet Plan to Audit:\n' + String(dietText || '').slice(0, 2500) +
      '\n\n---\n### Your Task as Evaluation & Audit Agent:\nPerform a comprehensive clinical safety audit and format your response with these exact sections:\n\n### 1. Audit Verdict & Safety Metric\n- **Audit Verdict**: [PASSED - Clinically Validated & Safe / CAUTION - Needs Adjustment]\n- **Safety & Compliance Score**: [e.g. 96/100]\n- **Contraindication Verification**: [State whether any prohibited foods were mistakenly included and confirm compliance]\n\n### 2. Clinical Validation Matrix\n- **Glycemic Safety**: Evaluation of carbohydrate quality and glycemic load.\n- **Cardiovascular Safety**: Evaluation of saturated fat limits and sodium thresholds.\n- **Renal & Metabolic Safety**: Evaluation of protein burden and purine/electrolyte balance.\n\n### 3. Doctor Brief (For Attending Physician)\n*Format as an executive clinical memo:*\n- **Patient**: ' + f(d.name, 'Patient') + ' (' + f(d.age) + ' y/o ' + f(d.gender) + ')\n- **Primary Clinical Concerns**: Summary of key abnormal biomarkers.\n- **Dietary Prescription Rationale**: Justification for the specific caloric and macronutrient targets.\n- **Recommended Follow-up & Lab Monitoring**: Specific repeat tests (e.g. repeat Lipid profile in 12 weeks, HbA1c in 3 months, renal function panel).\n\n### 4. Patient Friendly Empowerment Summary\n*In clear, compassionate, non-intimidating language:*\n- What your lab numbers mean in simple terms.\n- The 3 biggest positive changes this diet plan will bring to your daily energy and health.\n- Quick practical tips for sticking to the plan easily.';
  }

  function consultPrompt(question, history, ctx) {
    const profile = ctx.profile, protocol = ctx.protocol, d = profile.demographics || {}, m = protocol.macros || {};
    const bm = Object.values(profile.biomarkers || {}).map(b => b.name + ': ' + b.value + ' ' + b.unit + ' (' + b.status + ', Ref: ' + b.range + ')');
    const hist = (history || []).slice(-6).map(x => (x.role === 'user' ? 'Patient' : 'Consultant') + ': ' + x.content).join('\n');
    return '### Patient Context:\n- Name: ' + f(d.name, 'Patient') + ' | Age: ' + f(d.age) + ' | Sex: ' + f(d.gender) + ' | BMI: ' + f(d.bmi) + ' kg/m2 | BP: ' + f(d.bp_string) +
      '\n- Clinical Flags: ' + (names(profile.clinical_flags).join(', ') || 'None') + '\n- Key Biomarkers: ' + bm.join('; ') +
      '\n- Prescribed Energy: ' + f(m.calories, 1800) + ' kcal (C:' + (m.carbs || {}).percentage + '%, P:' + (m.protein || {}).percentage + '%, F:' + (m.fat || {}).percentage + '%)' +
      '\n- Clinical Protocols: ' + (protocol.protocols || []).join(', ') + '\n- Strictly Avoided Foods: ' + (protocol.strictly_avoid || []).join(', ') + '\n- Strongly Recommended Foods: ' + (protocol.strongly_recommend || []).join(', ') +
      '\n\n### Summary of Clinical Analysis:\n' + String(ctx.analysis || '').slice(0, 1200) + '\n\n### Summary of Diet Plan:\n' + String(ctx.diet || '').slice(0, 1200) +
      '\n\n### Recent Conversation:\n' + hist + '\n\n### Patient\'s Current Question:\n"' + question + '"\n\n---\nPlease provide a thorough, precise, and helpful response directly addressing the patient\'s question based on their laboratory report and clinical nutrition plan:';
  }

  // run an agent: AI when enabled and reachable, otherwise the built-in text. Never throws except on cancel.
  async function ask(llm, prompt, system, temp, signal, fallbackFn) {
    if (llm && llm.enabled) {
      try { return { text: await llm.generate(prompt, system, temp, signal), source: 'ai' }; }
      catch (e) {
        if (signal && signal.cancelled) throw e;
        return { text: fallbackFn(), source: 'builtin', error: friendlyNetError(e, llm.url) };
      }
    }
    return { text: fallbackFn(), source: 'builtin' };
  }

  const runAnalysis = (llm, profile, protocol, signal) =>
    ask(llm, analysisPrompt(profile), SYS_ANALYSIS, 0.2, signal, () => builtinAnalysis(profile, protocol));
  const runNutrition = (llm, profile, analysisText, protocol, signal) =>
    ask(llm, nutritionPrompt(profile, analysisText, protocol), SYS_NUTRITION, 0.3, signal, () => builtinDietNotes(protocol));
  async function runEvaluation(llm, profile, analysisText, dietText, protocol, audit, signal) {
    const r = await ask(llm, auditPrompt(profile, analysisText, dietText, protocol), SYS_AUDIT, 0.1, signal, () => builtinEvaluation(profile, protocol, audit));
    let aiScore = null;
    if (r.source === 'ai') { const mm = /(\d{2,3})\s*(?:\/|\s*out of\s*)\s*100/.exec(r.text); if (mm) aiScore = Math.min(100, +mm[1]); }
    return Object.assign(r, { aiScore });
  }

  // ---------------------------------------------------------------- offline Q&A (uses the real engine rules)
  const MARKER_WORDS = {
    fasting_glucose: ['fasting glucose', 'fasting sugar', 'fbs', 'blood sugar', 'glucose'], postprandial_glucose: ['postprandial', 'ppbs', 'after meal'],
    hba1c: ['hba1c', 'a1c', 'glycated', 'glycosylated'], total_cholesterol: ['total cholesterol', 'cholesterol'], ldl_cholesterol: ['ldl'],
    hdl_cholesterol: ['hdl'], triglycerides: ['triglyceride', 'tg'], creatinine: ['creatinine'], egfr: ['egfr', 'gfr', 'kidney function'],
    bun: ['bun', 'urea'], uric_acid: ['uric acid', 'gout', 'urate'], alt_sgpt: ['alt', 'sgpt'], ast_sgot: ['ast', 'sgot'], bilirubin_total: ['bilirubin'],
    hemoglobin: ['hemoglobin', 'haemoglobin', 'anemia', 'anaemia'], wbc_count: ['wbc', 'white blood'], platelets: ['platelet'],
    vitamin_d: ['vitamin d', 'vit d'], vitamin_b12: ['b12'], serum_ferritin: ['ferritin', 'iron'], tsh: ['tsh', 'thyroid'],
    serum_potassium: ['potassium'], serum_sodium: ['sodium level'], serum_calcium: ['calcium'],
  };
  const STOP = new Set('can eat have take with without what which should would could the and for are is it my me i a an of to in on or any some much many how why when does do be safe okay ok allowed avoid food foods diet today every day daily'.split(' '));

  function answerOffline(question, ctx) {
    const q = String(question || '').toLowerCase();
    const { profile, protocol } = ctx;
    const eng = E();
    const m = protocol.macros || {}, mi = protocol.micronutrient_targets || {};
    const out = [];

    // 1. biomarker questions
    const bms = profile.biomarkers || {};
    Object.keys(bms).forEach(k => {
      const words = MARKER_WORDS[k] || [];
      if (words.some(w => new RegExp('\\b' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b').test(q))) {
        const b = bms[k];
        out.push('**' + b.name + '**: ' + b.value + ' ' + b.unit + ' (reference ' + b.range + ') - **' + b.status + '**.', b.plain_desc || '');
      }
    });

    // 2. food questions against the real NIN tables + this patient's constraints
    const flags = eng.flagSet ? eng.flagSet(profile) : [];
    const demo = profile.demographics || {};
    const foods = eng.allFoods ? eng.allFoods() : [];
    const toks = q.replace(/[^a-z' ]/g, ' ').split(/\s+/).filter(t => t.length >= 3 && !STOP.has(t));
    const exact = [], partial = [];
    foods.forEach(r => {
      const n = r.food.toLowerCase();
      const whole = new RegExp('\\b' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b').test(q) || toks.some(t => n === t || n === t + 's');
      const part = !whole && toks.some(t => t.length >= 4 && n.split(/[\s/,()]+/).indexOf(t) !== -1);
      if (whole && !exact.some(h => h.food === r.food)) exact.push(r);
      else if (part && !partial.some(h => h.food === r.food)) partial.push(r);
    });
    const hits = exact.length ? exact : partial;   // "rice" should not also drag in "Rice puttu"

    if (hits.length) {
      hits.slice(0, 4).forEach(r => {
        const why = eng.exclusionReason(r.food, flags, demo.dietary_preference || '', protocol.strictly_avoid || [], demo.allergies || []);
        out.push(why
          ? '**' + r.food + '** - not advised for you. ' + why + '.'
          : '**' + r.food + '** - fine for your profile (' + r.portion + ' = ' + r.kcal + ' kcal, NIN table).');
      });
    } else {
      const avoidHit = (protocol.strictly_avoid || []).filter(a => toks.some(t => a.toLowerCase().indexOf(t) !== -1));
      if (avoidHit.length) out.push('That falls under your **avoid list**: ' + avoidHit.join('; ') + '.');
    }

    // 3. swaps
    if (/swap|replace|instead|alternative|substitut/.test(q)) {
      const cat = /breakfast/.test(q) ? 'Cereal' : /(lunch|dinner)/.test(q) ? 'Pulse' : null;
      const pool = foods.filter(r => (!cat || r.category === cat) && !eng.exclusionReason(r.food, flags, demo.dietary_preference || '', protocol.strictly_avoid || [], demo.allergies || []));
      if (pool.length) out.push('Allowed alternatives from the NIN tables: ' + pool.slice(0, 6).map(r => r.food + ' (' + r.portion + ', ' + r.kcal + ' kcal)').join('; ') + '.');
    }

    // 4. targets
    if (/calori|kcal|energy|macro|protein|carb|fat|how much/.test(q))
      out.push('Your daily target is **' + m.calories + ' kcal**: carbohydrate ' + (m.carbs || {}).grams + ' g, protein ' + (m.protein || {}).grams + ' g, fat ' + (m.fat || {}).grams + ' g.');
    if (/water|hydrat|fluid/.test(q)) out.push('Aim for about **' + mi.water_intake_liters + ' L** of fluids a day.');
    if (/salt|sodium/.test(q)) out.push('Keep sodium below **' + mi.sodium_max_mg + ' mg** a day.');
    if (/fib(er|re)/.test(q)) out.push('Fibre target: at least **' + mi.fiber_min_g + ' g** a day.');

    if (!out.length) {
      out.push('Here is what your plan says right now:',
        '- Energy **' + m.calories + ' kcal**/day, protocols: ' + (protocol.protocols || []).join('; '),
        '- Emphasise: ' + (protocol.strongly_recommend || []).slice(0, 4).join('; '),
        '- Avoid: ' + (protocol.strictly_avoid || []).slice(0, 4).join('; '));
    }
    out.push('', '*Answered on-device from your report. Connect an AI server in Settings for open-ended conversation.*');
    return out.join('\n\n').replace(/\n\n- /g, '\n- ');
  }

  // ---------------------------------------------------------------- general (no-report) questions
  async function runGeneral(llm, prep, signal) {
    if (!(llm && llm.enabled)) return { text: '', source: 'builtin' };
    try { return { text: await llm.generate(prep.prompt, prep.system, 0.3, signal), source: 'ai' }; }
    catch (e) { if (signal && signal.cancelled) throw e; return { text: '', source: 'builtin', error: friendlyNetError(e, llm.url) }; }
  }
  async function runPlain(llm, query, signal) {
    if (!(llm && llm.enabled)) return { text: '', source: 'builtin' };
    try { return { text: await llm.generate(query, SYS_PLAIN, 0.5, signal), source: 'ai' }; }
    catch (e) { if (signal && signal.cancelled) throw e; return { text: '', source: 'builtin', error: friendlyNetError(e, llm.url) }; }
  }
  async function runConsultant(llm, question, history, ctx, signal) {
    return ask(llm, consultPrompt(question, history, ctx), SYS_CONSULT, 0.3, signal, () => answerOffline(question, ctx));
  }

  return {
    Llm, makeSignal, http, friendlyNetError, followUps,
    runAnalysis, runNutrition, runEvaluation, runConsultant, runGeneral, runPlain,
    builtinAnalysis, builtinDietNotes, builtinEvaluation, answerOffline,
    prompts: { analysisPrompt, nutritionPrompt, auditPrompt, consultPrompt },
  };
});
