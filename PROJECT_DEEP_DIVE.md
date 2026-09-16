# NutriAgent AI — Complete Project Deep Dive
### For: AI Engineer Interview Prep & Full Understanding
---

## What Is This Project, In One Sentence?

You upload a blood test PDF → the system reads it, understands what's wrong with your health → calculates exactly what you should eat → generates a 7-day personalized meal plan → has a doctor-grade AI double-check it → shows everything in a clean web dashboard → lets you ask follow-up questions in a chat window.

Everything runs **100% on your own laptop**. No data goes to any cloud. No API keys needed.

---

## The Big Picture — How It All Connects

```
Your blood test PDF
        ↓
[extractor.py] — Reads the PDF, pulls out your name/age/weight and all 25+ blood test values
        ↓
[extractor.py] — Validates: "Is this actually a medical report?"
        ↓
[extractor.py] — Builds a "Health Profile": organizes all data, flags what's abnormal
        ↓
[deterministic_nutrition.py] — Pure math & rules: calculates your exact calorie needs,
                                 macro splits, and what foods to avoid/eat based on your flags
        ↓
[agents.py — Analysis Agent] — AI reads your profile → writes clinical analysis report
        ↓
[agents.py — Nutrition Agent] — AI reads analysis + nutrition rules → writes 7-day meal plan
        ↓
[agents.py — Evaluation Agent] — AI reads everything → audits for safety → writes Doctor Brief
        ↓
[app.py — Streamlit Dashboard] — Displays all results in a tabbed web UI
        ↓
[agents.py — Consultant Agent] — Live chat: you ask questions, AI answers using your data
```

---

## The 5 Source Files — What Each One Does

### 1. `extractor.py` — The Lab Report Reader
**Job**: Turn a PDF into structured medical data.

**Three functions you need to know:**

**`extract_text_from_pdf(pdf_file)`**
- Tries `pdfplumber` first (best library for tables + text). If it fails, falls back to `pypdf`.
- Returns raw text (a big string) + any tables it found.
- Handles file objects, bytes, or streams — so Streamlit uploads work fine.

**`validate_lab_report(raw_text)`**
- Checks if the PDF is actually a medical report (not a receipt or contract).
- Scans for medical keywords: glucose, cholesterol, creatinine, mg/dL, etc.
- Returns a confidence score (0.0–1.0) and which "panels" it detected (Lipid Panel, CBC, etc.).
- Needs at least 3 keyword hits OR 1 detected section to pass as valid.

**`build_health_profile(raw_text)`** ← **Most important function in the file**
- Orchestrates everything. Calls the functions below and assembles the final profile dict.
- Returns: `{ validation, demographics, biomarkers, clinical_flags, raw_text_preview }`

Inside `build_health_profile`, two more functions run:

**`parse_patient_demographics(raw_text)`**
- Uses regex (pattern matching) to find: Name, Age, Gender, Weight, Height, BMI, Blood Pressure.
- Has smart fallbacks — if weight is missing from PDF, it defaults to 72kg (male) or 60kg (female).
- Handles real-world messy formats like "Age / Sex: 52 Yrs / Male" or "52 Years Old".

**`extract_biomarkers(raw_text, gender)`**
- The heavy lifter. Has regex patterns for 25 biomarkers.
- For each biomarker found, it computes status: Normal / High / Low / Critical High / Critical Low.
  - Critical High = value > 1.5× the upper limit
  - Critical Low = value < 0.7× the lower limit
- Gender matters: HDL, Uric Acid, and Hemoglobin have different reference ranges for male vs female.

After extracting biomarkers, `build_health_profile` runs **rule-based clinical flag detection**:
- HbA1c ≥ 6.5% → flags "Type 2 Diabetes Mellitus"
- HbA1c 5.7–6.4% → flags "Prediabetes"
- Cholesterol > 200 OR LDL > 100 OR Triglycerides > 150 → flags "Dyslipidemia"
- eGFR < 60 → flags "Renal Impairment"
- Uric Acid > 7.0 → flags "Hyperuricemia (Gout Risk)"
- ALT > 56 OR AST > 40 → flags "Elevated Transaminases (Hepatic Stress)"
- TSH > 4.5 → flags "Subclinical Hypothyroidism"
- BP ≥ 140/90 → flags "Stage 2 Hypertension"
- Vitamin D < 30 → flags "Vitamin D Deficiency"
- And more...

**The 25 biomarkers tracked:**
Fasting Glucose, Postprandial Glucose, HbA1c, Total Cholesterol, LDL, HDL, Triglycerides, Creatinine, eGFR, BUN, Uric Acid, ALT (SGPT), AST (SGOT), Bilirubin, Hemoglobin, WBC Count, Platelets, Vitamin D, Vitamin B12, Ferritin, TSH, Serum Potassium, Serum Sodium, Serum Calcium, Blood Pressure (from demographics).

---

### 2. `deterministic_nutrition.py` — The Clinical Rules Engine
**Job**: Pure math and rules. No AI. Calculates exactly what the patient needs nutritionally.

This is called **"deterministic"** because it always gives the same answer for the same inputs — no randomness, no LLM creativity here.

**`calculate_bmr_tdee(demographics, activity_level)`**

Uses the **Mifflin-St Jeor equation** — the gold standard for calorie calculation:
- Male BMR = (10 × weight_kg) + (6.25 × height_cm) − (5 × age) + 5
- Female BMR = (10 × weight_kg) + (6.25 × height_cm) − (5 × age) − 161

Then multiplies by activity factor (1.2 = sedentary up to 1.9 = very active) to get TDEE (Total Daily Energy Expenditure).

Then adjusts for BMI:
- BMI ≥ 30 (Obese): −500 kcal deficit (weight loss goal)
- BMI 25–30 (Overweight): −300 kcal deficit
- BMI < 18.5 (Underweight): +300 kcal surplus
- Minimum floor: 1,300 kcal (never goes below this)

**`compute_clinical_nutrition_protocol(health_profile)`** ← **Core function**

Reads the clinical flags and applies specific dietary protocols:

| If flagged as... | Protocol Applied | Key Changes |
|---|---|---|
| Diabetic/Prediabetic | Low-GI / Insulin Sensitizing | Carbs cut to 40%, protein to 25%, fiber ≥ 35g, avoid sugars |
| Dyslipidemia | Mediterranean / Lipid-Lowering | Saturated fat < 7%, zero trans fats, push omega-3s |
| Hypertension | DASH Protocol | Sodium < 1500–2000mg/day, push potassium-rich foods |
| Renal Risk | Renal Protective Protocol | Protein moderated to 0.8g/kg body weight |
| Gout/Hyperuricemia | Low-Purine / Alkaline Protocol | Purines < 100mg/day, hydration ≥ 3L/day |
| Liver Risk | Hepatic Anti-inflammatory | Zero alcohol, no industrial fructose |
| Low Potassium | Electrolyte Replenishment | Push coconut water, avocado, sweet potato |
| Hypothyroid | Thyroid Support | Brazil nuts (selenium), iodized salt, pumpkin seeds |

The output is a rich dict with:
- `energy`: BMR, TDEE, target calories
- `macros`: exact grams AND percentages for carbs, protein, fat
- `micronutrient_targets`: sodium cap, fiber floor, water target
- `protocols`: list of active dietary protocols
- `clinical_constraints`: specific rules (e.g. "Sodium < 1800mg/day")
- `strictly_avoid`: list of forbidden foods
- `strongly_recommend`: list of therapeutic foods

---

### 3. `agents.py` — The 4 AI Agents
**Job**: Contains all 4 AI-powered agents that talk to the local Qwen2.5 model via Ollama.

**`OllamaClient`** — The communication layer
- Hits `http://localhost:11434` (where Ollama runs locally)
- Uses `POST /api/generate` to send prompts and get text back
- Key settings: temperature=0.3 (low = more factual, less creative), context window 8192 tokens, streaming off
- Has a `check_connection()` method the sidebar "Verify Connection" button calls
- **Every agent has a fallback**: if Ollama is offline, a built-in template response is returned instead of crashing

**Agent 1: `AnalysisAgent`**
- System prompt: "You are an expert Clinical Diagnostic AI Agent"
- Input: demographics + biomarkers + clinical flags + raw PDF excerpt
- Temperature: 0.2 (very low = very factual)
- Asks Qwen to produce:
  1. Executive Clinical Summary (3-4 sentences)
  2. Breakdown of each abnormal marker with physiological explanation
  3. 3-tier risk stratification (High / Moderate / Nutritional)
  4. Metabolic interconnections (e.g. how insulin resistance drives high triglycerides)
  5. Directives for the Nutrition Agent

**Agent 2: `NutritionAgent`**
- System prompt: "You are a Lead Clinical Dietitian AI Agent"
- Input: demographics + analysis report + the full nutrition_protocol from deterministic engine
- Temperature: 0.3
- Critically: the deterministic constraints are passed as MANDATORY — calories, macros, avoid lists, recommend lists are all injected into the prompt
- Asks Qwen to produce:
  1. Diet strategy overview
  2. Full 7-day meal plan (Breakfast, Mid-Morning, Lunch, Snack, Dinner, Hydration)
  3. For each key food: biomarker therapeutic target explanation
  4. Cooking tips, hydration protocol

**Agent 3: `EvaluationAgent`** (The Audit Gate)
- System prompt: "You are a Senior Chief Medical Auditor AI Agent"
- Input: health profile + analysis + diet plan + nutrition protocol
- Temperature: 0.1 (lowest = most conservative, most rule-following)
- Extracts a safety score (0–100) from the response using regex
- Verdict: PASSED if score ≥ 80, CAUTION otherwise
- Asks Qwen to produce:
  1. Audit Verdict + Safety Score
  2. Clinical Validation Matrix (glycemic, cardiovascular, renal safety)
  3. Doctor Brief (formal memo for the attending physician)
  4. Patient-friendly plain language summary

**Agent 4: `ConsultantAgent`** (The Chatbot)
- System prompt: "You are the Senior Clinical Nutritionist & Lab Diagnostic Consultant"
- Input: full pipeline results + chat history (last 6 messages) + current question
- Temperature: 0.3
- Answers follow-up questions grounded in the patient's specific lab numbers
- History window: only uses last 6 messages to avoid token overflow

---

### 4. `app.py` — The Streamlit Web Interface
**Job**: The entire web UI, user interaction, and pipeline orchestration.

**Startup & Config (Sidebar)**
- Ollama endpoint URL (default: localhost:11434)
- Model selector: qwen2.5:7b / 14b / 32b / latest / Custom
- "Verify Connection" button
- Dietary preference (Omnivore, Vegan, etc.)
- Allergen multi-select (Gluten, Dairy, Nuts, etc.)
- Activity level slider (Sedentary → Very Active)

**Session State** (Streamlit's way of remembering things across reruns)
- `raw_pdf_text`: the extracted text from the uploaded PDF
- `source_name`: the filename
- `pipeline_results`: the entire output of all 3 agents + profiles (persists between reruns)
- `chat_messages`: chat history list
- `pending_prompt`: stores a clicked suggestion chip to be sent on next rerun

**Pipeline Execution Flow (when "Run Multi-Agent Pipeline" is clicked)**

The app shows a live animated execution monitor panel that updates in real-time:

```
Step 0: Profile Synthesis    → calls build_health_profile()
Step 1: Rules Engine         → calls compute_clinical_nutrition_protocol()
Step 2: Analysis Agent       → calls AnalysisAgent.run()
Step 3: Nutrition Agent      → calls NutritionAgent.run()
Step 4: Audit Gate           → calls EvaluationAgent.run()
```

After all 5 steps, `st.rerun()` is called to refresh the page and show the results dashboard.

**The 6 Output Tabs**

| Tab | Agent | What's Shown |
|---|---|---|
| 01. Diagnostic Analysis | Analysis Agent | Clinical flags with severity badges, full analysis report |
| 02. Safety Audit & Clearance | Evaluation Agent | Safety score, audit verdict, Doctor Brief, patient summary |
| 03. Precision Nutrition Protocol | Nutrition Agent | Macro breakdown, food lists, full 7-day meal plan |
| 04. Interactive Clinical Q&A | Consultant Agent | Chat interface with 4 suggestion chips |
| 05. Laboratory Biomarker Registry | Data Layer | Pandas table of all extracted biomarkers with status |
| 06. EHR Export | N/A | Download as Markdown or JSON |

**The Stepper Visual** at the top shows which pipeline stage is complete (1→6).

**Top KPI cards** show: Patient name/BMI, Prescribed calories, Macro split, # of diagnostic flags, Safety score.

---

### 5. `generate_sample_pdf.py` + `sample_blood_test_report.pdf`
- `generate_sample_pdf.py` uses `reportlab` to create a realistic fake blood test PDF for testing.
- The sample patient is **Robert Vance, 52M** — has prediabetes, dyslipidemia, mildly elevated uric acid, low Vitamin D, hypertension. A rich test case that triggers multiple protocols.
- The same patient data is also hardcoded as `SAMPLE_LAB_REPORT_TEXT` in `app.py` as a fallback.

---

## Complete Data Flow — Step by Step With Real Data

Using the sample patient Robert Vance (52M, 175cm, 86.5kg, BMI 28.2):

**Step 1 — PDF Upload**
User uploads PDF → `extract_text_from_pdf()` → ~1500 chars of raw text extracted

**Step 2 — Demographics Parsing**
Regex finds: Name="Robert Vance", Age=52, Gender=Male, Weight=86.5kg, Height=175cm, BP=138/88

**Step 3 — Biomarker Extraction**
Regex extracts 15+ values including:
- HbA1c = 6.4% → Status: High (ref: 4.0–5.6)
- LDL = 154 mg/dL → Status: Critical High (ref: 0–100; 154 > 150 = 1.5×100)
- Triglycerides = 198 mg/dL → Status: High (ref: 0–150)
- HDL = 38 mg/dL → Status: Low (ref for male: 40–100)
- Uric Acid = 7.8 → Status: High (ref male: 3.4–7.0)
- Vitamin D = 19.4 → Status: Low (ref: 30–100)
- eGFR = 78 → Status: Low (ref: 90–150)

**Step 4 — Clinical Flags Generated (deterministic rules)**
- Prediabetes/Impaired Fasting Glucose (HbA1c 6.4%)
- Dyslipidemia (Chol 232, LDL 154, TG 198)
- Stage 1 Hypertension (138/88 mmHg)
- Hyperuricemia / Gout Risk (Uric Acid 7.8)
- Vitamin D Deficiency (19.4 ng/mL)
- Renal borderline (eGFR 78)

**Step 5 — Nutrition Protocol Computed**
BMR = (10×86.5) + (6.25×175) − (5×52) + 5 = 865 + 1093.75 − 260 + 5 = **1703 kcal**
TDEE = 1703 × 1.375 (light activity) = **2342 kcal**
BMI = 28.2 → −300 kcal deficit
**Target = 2042 kcal** (rounded)

Active protocols: Low-GI + Mediterranean + DASH + Low-Purine
Macro split: Carbs 40%, Protein 25%, Fat 35%
Carbs: 2042 × 0.40 / 4 = **204g**
Protein: 2042 × 0.25 / 4 = **128g**
Fat: 2042 × 0.35 / 9 = **79g**
Sodium cap: 1800 mg/day (hypertensive)
Fiber floor: 35g/day (diabetic + dyslipidemia)
Water: 3.0L/day (hyperuricemia)

**Step 6 — Analysis Agent (Qwen2.5)**
All of the above is packed into a structured prompt and sent to Qwen. The AI writes a clinical narrative explaining what each abnormal value means, how they relate to each other (e.g. insulin resistance driving both high triglycerides and high uric acid), and what the nutrition plan must address.

**Step 7 — Nutrition Agent (Qwen2.5)**
Analysis report + all macro/micro targets + avoid/recommend food lists → Qwen writes a full 7-day meal plan that must stay within the deterministic targets.

**Step 8 — Evaluation Agent (Qwen2.5)**
Diet plan + all constraints → Qwen audits it, assigns a safety score, writes the Doctor Brief and patient summary. A regex extracts the numeric score (e.g. "96/100") from the response.

**Step 9 — Results Stored in Session State**
`pipeline_results` dict saved → `st.rerun()` → dashboard renders.

---

## Key Technical Decisions (What, Why, Trade-offs)

**Why Ollama + Qwen2.5 locally?**
- Full privacy: medical data never leaves the machine.
- No API costs. Can run without internet.
- Trade-off: needs GPU or fast CPU, slower than cloud APIs.

**Why is the nutrition engine "deterministic" (not AI)?**
- Medical safety. You cannot let an LLM freestyle calorie targets — if it hallucinates "1200 kcal" for an obese patient, that could be harmful. The math is verified, reproducible, and explainable.
- The AI's job is only to write the natural language description of what the math decided.

**Why three separate agents instead of one big prompt?**
- Separation of concerns: each agent has one job and one expert persona.
- Keeps individual prompts focused and shorter → better quality outputs.
- The Evaluation Agent being separate acts as a real audit — it can catch errors the Nutrition Agent made.

**Why temperature 0.1 for the Evaluation Agent?**
- This agent is making safety-critical judgments (contraindication checks). Lower temperature = more deterministic, conservative, less likely to hallucinate an approval.

**Why regex for biomarker extraction instead of AI?**
- Speed. Calling an LLM just to extract a number is 30–120 seconds wasted.
- Reliability. Regex on structured lab reports (which follow predictable formats) is more reliable than asking an LLM to parse numbers.
- Determinism. The same PDF always gives the same numbers.

**Why `pdfplumber` + `pypdf` fallback?**
- `pdfplumber` is better (handles tables, better layout analysis) but sometimes fails on complex PDFs.
- `pypdf` is a reliable fallback for simple text extraction.
- This makes the extractor robust against diverse PDF structures.

**The offline fallback system**
Every agent has a `_generate_fallback_*()` method. If Ollama isn't running, the app still works — it returns template-based responses built from the deterministic data. This is critical for demos and development.

---

## What Happens If Something Is Missing from the PDF

| Missing Data | What Happens |
|---|---|
| Weight/Height | Defaults: Male 72kg/172cm, Female 60kg/160cm |
| BMI | Calculated from weight/height if available |
| Age | Defaults to 45 |
| Gender | Tries multiple regex patterns; defaults to "Unknown" |
| A biomarker | Simply not included; the system works with whatever it found |
| Ollama offline | Fallback templates used for all 3 agents |
| Scanned PDF (image) | Validation fails with "may be a scanned image" message |

---

## The Tech Stack

| Layer | Technology | Why |
|---|---|---|
| UI | Streamlit | Rapid deployment of data apps in pure Python |
| LLM Runtime | Ollama | Local LLM serving, privacy-first |
| LLM Model | Qwen2.5:7b (or 14b/32b) | Strong multilingual medical reasoning |
| PDF Extraction | pdfplumber + pypdf | Robust dual-library fallback |
| Data Tables | Pandas | Biomarker table display |
| PDF Generation | ReportLab | Sample report generation |
| HTTP | requests | Talk to Ollama's REST API |

---

## Common Interview Questions You Might Get

**Q: How does the system handle a patient with multiple conditions?**
A: The conditions are not mutually exclusive. The `compute_clinical_nutrition_protocol()` function checks each condition independently with `if` statements (not `elif`), so all matching protocols stack. A patient with both diabetes and hypertension gets both Low-GI AND DASH protocols simultaneously. The avoid/recommend lists merge (deduplicated). Macro percentages use the most restrictive setting via `max()` calls.

**Q: What's the clinical accuracy of the biomarker extraction?**
A: It's regex-based with 25+ known patterns per biomarker, so it works well for standard Indian/US lab report formats. It's not perfect — unusual lab report formats, scanned PDFs, or labs using non-standard naming will miss. The system is transparent about this: if a biomarker isn't found, it's simply absent from the profile. It does not guess.

**Q: Why is the Evaluation Agent run AFTER the Nutrition Agent? Shouldn't safety come first?**
A: It's an audit pattern, not a pre-filter. The Evaluation Agent needs the full diet plan to audit against. You can't audit what hasn't been written yet. The deterministic engine already applies safety constraints before the Nutrition Agent even runs — the Evaluation Agent is a second layer of verification.

**Q: What does the safety score actually measure?**
A: The Evaluation Agent (Qwen) generates a written safety score as text (e.g. "96/100"). The Python code uses regex `r"(\d{2,3})\s*(?:\/|\s*out of\s*)\s*100"` to extract the number. If no score is found in the text, it defaults to 95. So the score is LLM-generated — it's as reliable as the audit prompt is well-specified.

**Q: How does the chat agent maintain context?**
A: It keeps the last 6 messages from `st.session_state["chat_messages"]` and injects them into the prompt as "Recent Conversation". Full pipeline results (analysis, diet, evaluation) are also injected, truncated to ~1200 chars each to avoid exceeding the 8192-token context window.

**Q: What's the token budget strategy?**
A: Each agent trims its inputs:
- Analysis Agent: raw PDF preview limited to 800 chars
- Nutrition Agent: analysis report limited to 1200 chars
- Evaluation Agent: diet plan limited to 2500 chars
- Consultant: analysis + diet each limited to 1200 chars, last 6 chat messages
Total context window configured as 8192 tokens in Ollama.

**Q: Could this be extended to support multiple patients or a clinic workflow?**
A: Currently it's single-session, single-patient (session state in Streamlit). To support multi-patient: add a patient selector in the sidebar, store results in a database (SQLite/PostgreSQL) keyed by patient ID, load/save `pipeline_results` from DB instead of session state. The EHR export (tab 06) already produces structured JSON suited for this.

**Q: Is this HIPAA-compliant or production-ready for clinical use?**
A: No. It's a research/demo platform. For real clinical use you'd need: proper auth/login, audit logging, data encryption at rest, formal clinical validation of the AI outputs, review by licensed clinicians, and compliance checks. The system itself is careful to label everything as "for informational purposes" and always generates a Doctor Brief for physician review.

---

## File Map — Quick Reference

```
NutriAgent-AI/
├── app.py                      ← Web UI, pipeline orchestration, all tabs
├── agents.py                   ← 4 AI agents (Analysis, Nutrition, Evaluation, Consultant)
├── extractor.py                ← PDF reading, biomarker extraction, health profile builder
├── deterministic_nutrition.py  ← BMR/TDEE math, clinical protocol rules engine
├── generate_sample_pdf.py      ← Utility to generate test PDFs using reportlab
├── sample_blood_test_report.pdf ← Pre-built test file (Robert Vance, 52M)
├── requirements.txt            ← 6 dependencies
└── README.md                   ← Project overview
```

---

## Dependencies (requirements.txt) — What Each Does

| Package | Version | Role |
|---|---|---|
| streamlit | ≥1.30.0 | The entire web UI framework |
| pdfplumber | ≥0.10.0 | Primary PDF text+table extractor |
| pypdf | ≥3.17.0 | Fallback PDF extractor |
| requests | ≥2.31.0 | HTTP calls to Ollama REST API |
| pandas | ≥2.0.0 | Biomarker dataframe + table display |
| reportlab | ≥4.0.0 | Generating the sample test PDF |

---

*Generated: 2026-09-15 | NutriAgent AI v2.4*
