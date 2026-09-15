# NutriAgent AI: Qwen Multi-Agent Clinical Lab & Precision Nutrition System

NutriAgent AI is a fully local, privacy-respecting clinical intelligence platform that converts raw medical laboratory reports into actionable, personalized nutrition therapy — no cloud API calls, no data leaves your machine.

Three specialized Qwen2.5 agents run sequentially on your local Ollama instance: the Analysis Agent performs deep pathophysiological risk stratification of your biomarkers; the Audit Gate cross-checks every dietary recommendation against clinical contraindications and produces a Doctor Brief; and the Nutrition Agent generates a tailored 7-day meal plan grounded in deterministic caloric and macronutrient calculations. An interactive Q&A consultant lets you ask any follow-up question about your report in plain language.

---

## Architecture & Pipeline Flow

```
PDF Upload
    ↓
Extraction (pdfplumber & pypdf)
    ↓
Validation & Health Profile Synthesis
    ↓
Qwen Analysis Agent (Pathophysiological Risk Stratification)
    ↓
Deterministic Nutrition Engine (BMR/TDEE, Macros, Clinical Constraints)
    ↓
Qwen Nutrition Agent (7-Day Tailored Meal Plan with Rationale)
    ↓
Qwen Evaluation Agent / Audit Gate (Contraindication & Safety Verification)
    ↓
Doctor Brief + Patient Empowerment Guide
    ↓
Streamlit Interactive Dashboard & Export
```

---

## The 3 Specialized Qwen Agents

| Agent | Responsibility | Core Outputs |
| :--- | :--- | :--- |
| **1. Analysis Agent** | Deep diagnostic interpretation of extracted biomarkers, organ stress (Hepatic, Renal, Cardiovascular), and metabolic risks. | Executive Clinical Summary, Anomaly Breakdown, 3-Tier Risk Stratification, Metabolic Interconnections. |
| **2. Nutrition Agent** | Translates clinical findings & deterministic nutrition targets into a complete therapeutic meal plan. | 7-Day Actionable Meal Schedules (Breakfast to Dinner), Therapeutic Ingredient Rationales, Functional Superfoods. |
| **3. Evaluation Agent (Audit Gate)** | Rigorous medical audit checking contraindications, macro compliance, sodium/purine limits, and issuing handoff briefs. | Clinical Safety Score (0-100), Audit Verdict Badge, Doctor Brief (for Attending MD), Plain-Language Patient Summary. |

---

## Deterministic Clinical Engine

Before the Nutrition Agent generates meals, a deterministic rules engine calculates:
- **BMR & TDEE**: Accurate Mifflin-St Jeor formula adjusted for patient BMI and activity.
- **Biomarker-Driven Protocols**:
  - **Prediabetes / Diabetes**: Low-GI, 40% Carbs, Fiber >= 35g/day, restricted sugars.
  - **Dyslipidemia**: Cardioprotective Mediterranean, SFA < 7%, high MUFA/PUFA, zero trans-fats.
  - **Hypertension (DASH)**: Sodium cap < 1800 mg/day, high potassium-to-sodium ratio.
  - **Renal Impairment (eGFR < 90)**: Protein moderation (0.8 g/kg), phosphorus/sodium control.
  - **Hyperuricemia (Gout)**: Low purine (< 100 mg/day), zero high-fructose corn syrup, hydration >= 3.0 L/day.

---

## Quick Start Guide

### 1. Prerequisites & Ollama Setup
Install and start [Ollama](https://ollama.ai/), then pull the Qwen2.5 model:

```bash
ollama pull qwen2.5:7b
ollama serve
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch the Streamlit App
```bash
streamlit run app.py
```

---

## Project Structure

- `app.py` — Main Streamlit application with PDF upload, animated pipeline tracker, tabbed results, and EHR export.
- `agents.py` — Ollama client and 4 Qwen agents (Analysis, Nutrition, Evaluation, Consultant Q&A) with offline fallbacks.
- `extractor.py` — High-precision PDF parser extracting demographics and 25+ standard biomarkers with reference ranges.
- `deterministic_nutrition.py` — Scientific clinical rules engine (BMR, TDEE, macros, contraindications).
- `generate_sample_pdf.py` — Utility to generate realistic clinical lab report PDFs.
- `sample_blood_test_report.pdf` — Sample PDF lab report for instant testing.
- `test_pipeline.py` — Comprehensive unit and end-to-end verification script.

---

## Testing with Sample Data

If you do not have a PDF report ready:
1. Open the app (`streamlit run app.py`).
2. Upload `sample_blood_test_report.pdf` from the project folder.
3. Click **Run Multi-Agent Pipeline** to watch the animated agent execution monitor run live.
