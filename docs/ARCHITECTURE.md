# Architecture notes

These are my notes on how NutriAgent is put together and why I made the choices I did. The README covers what it does and how to run it.

## Data flow

```
PDF -> extractor.py -> health profile -> deterministic_nutrition.py -> agents.py -> app.py
```

1. **Extraction** (`extractor.py`): `pdfplumber` first, `pypdf` as a fallback. `validate_lab_report` rejects PDFs that don't look like lab reports (keyword and section hits, with a confidence score). Image-only PDFs fail validation with a "may be a scanned image" message.
2. **Health profile** (`build_health_profile`): regex parsing of demographics (name, age, sex, height, weight, BMI, blood pressure) and 25+ biomarkers. Each biomarker gets a status of Normal, High, Low, Critical High (above 1.5x the upper limit) or Critical Low (below 0.7x the lower limit). A few ranges depend on sex (HDL, uric acid, haemoglobin). Rule-based clinical flags are derived from the values, for example HbA1c 5.7-6.4 % as prediabetes, eGFR below 60 as renal impairment, uric acid above 7.0 as hyperuricaemia.
3. **Deterministic engine** (`deterministic_nutrition.py`): Mifflin-St Jeor BMR, multiplied by an activity factor (1.2 sedentary to 1.9 very active) to get TDEE. The target is adjusted by BMI (-500 kcal if obese, -300 if overweight, +300 if underweight) with a floor of 1,300 kcal. Each flagged condition then adds a protocol and its constraints.
4. **Food layer** (`indian_foods.py`): builds the 7-day plan from the ICMR-NIN food tables in `nin_food_data.json`, filtered by diet preference, allergens and flags, with glycaemic-index-aware swaps and a grocery list.
5. **Agents** (`agents.py`): the engine's output goes into the prompts as mandatory constraints.
6. **UI** (`app.py`): Streamlit. A live stepper shows each stage, then six tabs (analysis, audit and Doctor Brief, nutrition plan, Q&A chat, biomarker table, export).

## Worked example: the sample patient

The synthetic sample report is a 52-year-old man, 175 cm, 86.5 kg (BMI 28.2), with prediabetes, dyslipidaemia, raised uric acid, low vitamin D and borderline blood pressure.

- BMR = 10x86.5 + 6.25x175 - 5x52 + 5, about 1,704 kcal
- TDEE at light activity (x1.375), about 2,343 kcal
- Overweight adjustment (-300), target about 2,043 kcal
- Stacked protocols (low-GI, Mediterranean, DASH, low-purine) give a 40 / 25 / 35 carb / protein / fat split, so about 204 g carbs, 128 g protein and 79 g fat

## Protocol stacking

Conditions are checked independently (`if`, not `elif`), so several protocols can be active at once. A patient with diabetes and hypertension gets low-GI and DASH together. Avoid and recommend lists are merged and de-duplicated, and where two protocols disagree on a number the more restrictive one is used.

| Flag | Protocol | Main effect |
| :--- | :--- | :--- |
| Diabetes / prediabetes | Low-GI | 40 % carbs, 25 % protein, fibre of at least 35 g, restricted sugars |
| Dyslipidaemia | Mediterranean | Saturated fat under 7 %, no trans fats, more omega-3 |
| Hypertension | DASH | Sodium cap, potassium-rich foods |
| Reduced eGFR | Renal-protective | Protein about 0.8 g/kg |
| Hyperuricaemia | Low-purine | Purines under 100 mg/day, at least 3 L fluids |
| Liver stress | Hepatic | No alcohol, no industrial fructose |
| Low potassium | Electrolyte | Coconut water, avocado, sweet potato |
| Hypothyroid | Thyroid support | Selenium and iodine sources |

## The LLM layer

All four agents talk to Ollama's `/api/generate` through one `OllamaClient` (default `http://localhost:11434`, model `qwen2.5:7b`, 16k context, 600 s timeout, `keep_alive` of 30 minutes so the model stays loaded between calls).

| Agent | Temperature | Notes |
| :--- | :--- | :--- |
| Analysis | 0.2 | Summary, abnormal-marker breakdown, risk tiers, directives for the nutrition agent |
| Nutrition | 0.3 | Receives the engine's targets and avoid/recommend lists as mandatory constraints |
| Evaluation | 0.1 | Lowest temperature because it writes the conservative, rule-following review. The score does not come from the model (see below) |
| Consultant | 0.3 | Uses the last 6 chat messages plus the pipeline results |

Each agent trims its inputs (PDF preview, analysis, diet plan) so the prompt stays inside the context window. Every agent also has an offline fallback built from the deterministic data, so a missing or slow model degrades the prose and nothing else.

**How the audit score works.** The score is computed by code, not read from the model's text. `check_constraint_compliance` (in `general_intake.py`, shared with the report-free path) checks the generated 7-day plan against its own prescription: daily calories within tolerance of the target, no contraindicated food in any meal, at least one protocol stacked, and meals traceable to the NIN tables. The score is the percentage of checks that pass, and the model is told those results as facts and asked not to invent a number. This verifies the plan against its own rules. It is not a clinical safety score. An earlier version regex-parsed a `NN/100` from the model's reply and fell back to a fixed 95 when it was offline. I replaced that because a placeholder presented as a clinical result is misleading.

## Decisions and trade-offs

- **Local model, local data.** Lab reports are sensitive, so nothing leaves the machine. The cost is hardware: a 7B model on CPU can take minutes for a meal-plan prompt.
- **Rules for numbers, LLM for words.** A model that guesses a calorie target can guess wrong, and its answer changes between runs. The engine is reproducible and explainable, and the model only describes what it decided.
- **Regex over an LLM for extraction.** Faster, repeatable, and good enough for standard lab layouts. The cost is that unusual layouts are missed. Missing markers are omitted rather than inferred.
- **Separate agents.** Each prompt stays short and focused, and the audit step is a genuinely separate pass over the finished plan.
- **Audit after generation.** The engine already enforces constraints before the nutrition agent runs. The audit agent is a second check on the written plan.

## Missing data defaults

| Missing | Behaviour |
| :--- | :--- |
| Weight / height | Defaults by sex (male 72 kg / 172 cm, female 60 kg / 160 cm) |
| Age | Defaults to 45 |
| A biomarker | Left out |
| Ollama offline | Fallback templates for all agents |
| Scanned PDF | Validation fails with a message |

## Mobile port

`mobile/web/js/engine.js` re-implements the extractor, engine, NIN plan builder and general-intake parser in JavaScript. It runs inside a WebView shell (`mobile/android/`), with pdf.js reading the PDF on the device. The build script avoids Gradle: `aapt2`, `javac`, `d8`, `zipalign`, `apksigner`. Parity with the Python code is enforced by `mobile/tests/parity.test.js`, and the intentional differences are documented in `mobile/tests/DEVIATIONS.md`.

## Where I'd take it next

- Real clinical review of the protocols and the food filters
- OCR for scanned reports
- Multi-patient storage, authentication and audit logging before any real-world use
