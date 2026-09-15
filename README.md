# 🩺 NutriAgent AI: Qwen Multi-Agent Clinical Lab & Precision Nutrition System

An end-to-end agentic application that transforms medical lab reports (PDFs) into personalized, clinically validated diet plans and physician briefs using local **Qwen2.5** models on **Ollama**.

---

## 🏗️ Architecture & Pipeline Flow

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

## 🤖 The 3 Specialized Qwen Agents

| Agent | Responsibility | Core Outputs |
| :--- | :--- | :--- |
| **1. Analysis Agent** | Deep diagnostic interpretation of extracted biomarkers, organ stress (Hepatic, Renal, Cardiovascular), and metabolic risks. | Executive Clinical Summary, Anomaly Breakdown, 3-Tier Risk Stratification, Metabolic Interconnections. |
| **2. Nutrition Agent** | Translates clinical findings & deterministic nutrition targets into a complete therapeutic meal plan. | 7-Day Actionable Meal Schedules (Breakfast to Dinner), Therapeutic Ingredient Rationales, Functional Superfoods. |
| **3. Evaluation Agent (Audit Gate)** | Rigorous medical audit checking contraindications, macro compliance, sodium/purine limits, and issuing handoff briefs. | Clinical Safety Score (0-100), Audit Verdict Badge, Doctor Brief (for Attending MD), Plain-Language Patient Summary. |

---

## ⚙️ Deterministic Clinical Engine

Before the Nutrition Agent generates meals, a deterministic rules engine calculates:
- **BMR & TDEE**: Accurate Mifflin-St Jeor formula adjusted for patient BMI and activity.
- **Biomarker-Driven Protocols**:
  - **Prediabetes / Diabetes**: Low-GI, 40% Carbs, Fiber $\ge$ 35g/day, restricted sugars.
  - **Dyslipidemia**: Cardioprotective Mediterranean, SFA $<$ 7%, high MUFA/PUFA, zero trans-fats.
  - **Hypertension (DASH)**: Sodium cap $<$ 1800 mg/day, high potassium-to-sodium ratio.
  - **Renal Impairment (eGFR $<$ 90)**: Protein moderation ($0.8\text{ g/kg}$), phosphorus/sodium control.
  - **Hyperuricemia (Gout)**: Low purine ($< 100\text{ mg/day}$), zero high-fructose corn syrup, hydration $\ge 3.0\text{ L/day}$.

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Ollama Setup
Install and start [Ollama](https://ollama.ai/), then pull the Qwen2.5 model:

```bash
# Pull Qwen 2.5 (choose 7B, 14B, or 32B based on your GPU/RAM)
ollama pull qwen2.5:7b

# Ensure Ollama is running
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

## 📂 Project Structure

- `app.py` — Main Streamlit application with drag-and-drop PDF upload, visual pipeline tracker, tabbed analysis, and export tools.
- `agents.py` — Ollama client and the 3 Qwen agents (`AnalysisAgent`, `NutritionAgent`, `EvaluationAgent`) with structured clinical prompts and built-in offline fallbacks.
- `extractor.py` — High-precision PDF parser for medical lab reports, extracting demographics and 25+ standard biomarkers with reference ranges.
- `deterministic_nutrition.py` — Scientific clinical rules engine (BMR, TDEE, macros, contraindications).
- `generate_sample_pdf.py` — Utility to generate realistic clinical lab report PDFs.
- `sample_blood_test_report.pdf` — Sample PDF lab report for instant testing.
- `test_pipeline.py` — Comprehensive unit and end-to-end verification script.

---

## 🧪 Testing with Sample Data

If you do not have a PDF report ready:
1. Open the app (`streamlit run app.py`).
2. In the sidebar, click **"📄 Load Pre-set Clinical Lab Report"** or upload `sample_blood_test_report.pdf`.
3. Click **"🚀 Execute Full Agentic Pipeline"** to watch the multi-agent pipeline execute live.
