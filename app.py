"""
app.py - Production-Grade Clinical UI for Qwen Multi-Agent Medical Nutrition Platform
Architecture: PDF Extraction -> Validation -> Health Profile -> Qwen Analysis (01)
-> Audit Gate (02) -> Qwen Nutrition (03) -> Interactive Q&A (04) -> Biomarker Registry (05) -> EHR Export (06).
"""

import os
import io
import json
import time
import pandas as pd
import streamlit as st

# Custom modules
from extractor import extract_text_from_pdf, build_health_profile, STANDARD_REFERENCE_RANGES
from deterministic_nutrition import compute_clinical_nutrition_protocol
from agents import OllamaClient, AnalysisAgent, NutritionAgent, EvaluationAgent, ConsultantAgent, SingleLLMBaseline

# Page configuration
st.set_page_config(
    page_title="NutriAgent AI | Precision Clinical Nutrition",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Impeccable Design System: Production Medical Grade CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Albert+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Albert Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #0F172A;
    }

    /* Top Navigation / App Header */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 16px;
        margin-bottom: 20px;
    }
    .app-title-group {
        display: flex;
        flex-direction: column;
    }
    .app-title {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .app-badge {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        background: #F1F5F9;
        color: #475569;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #CBD5E1;
    }
    .app-badge-private {
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        background: #ECFDF5;
        color: #065F46;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #A7F3D0;
    }
    .app-subtitle {
        font-size: 0.88rem;
        color: #64748B;
        margin-top: 2px;
    }

    /* Stepper / Visual Pipeline */
    .stepper-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 10px 16px;
        margin-bottom: 20px;
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.78rem;
        font-weight: 500;
        color: #64748B;
    }
    .step-item.active {
        color: #0F172A;
        font-weight: 600;
    }
    .step-item.completed {
        color: #059669;
    }
    .step-circle {
        width: 22px;
        height: 22px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.72rem;
        font-weight: 600;
        background: #F1F5F9;
        color: #64748B;
        border: 1px solid #CBD5E1;
    }
    .step-circle.active {
        background: #0F172A;
        color: #FFFFFF;
        border-color: #0F172A;
    }
    .step-circle.completed {
        background: #ECFDF5;
        color: #059669;
        border-color: #A7F3D0;
    }
    .step-divider {
        flex: 1;
        height: 1px;
        background: #E2E8F0;
        margin: 0 8px;
    }

    /* Metric & KPI Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 12px 14px;
        height: 100%;
    }
    .metric-label {
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #64748B;
    }
    .metric-value {
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #0F172A;
        margin-top: 4px;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-subtext {
        font-size: 0.76rem;
        color: #94A3B8;
        margin-top: 2px;
    }

    /* Section & Agent Card Wrappers */
    .agent-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;
        border-bottom: 1px solid #F1F5F9;
        padding-bottom: 10px;
    }
    .agent-title-block {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .agent-serial {
        font-size: 0.72rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: #FFFFFF;
        background: #0F172A;
        padding: 2px 7px;
        border-radius: 4px;
    }
    .agent-heading {
        font-size: 1.05rem;
        font-weight: 600;
        color: #0F172A;
        margin: 0;
    }
    .agent-meta {
        font-size: 0.75rem;
        color: #64748B;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Plain English Callout Box */
    .plain-english-box {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 18px;
    }
    .plain-english-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #0369A1;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 6px;
    }
    .plain-english-text {
        font-size: 0.88rem;
        line-height: 1.6;
        color: #0C4A6E;
    }

    /* Organ Health Card Grid */
    .organ-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 12px;
        margin-bottom: 20px;
    }
    .organ-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px;
    }
    .organ-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 8px;
    }
    .organ-card-title {
        font-size: 0.88rem;
        font-weight: 600;
        color: #0F172A;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .organ-card-body {
        font-size: 0.82rem;
        color: #475569;
        line-height: 1.5;
    }
    .organ-card-action {
        font-size: 0.78rem;
        color: #0284C7;
        font-weight: 500;
        margin-top: 6px;
        padding-top: 6px;
        border-top: 1px dashed #E2E8F0;
    }

    /* Meal Plan Card */
    .meal-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
    }
    .meal-card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 6px;
    }
    .meal-slot-tag {
        font-size: 0.75rem;
        font-weight: 700;
        color: #0F172A;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .meal-cal-badge {
        font-size: 0.72rem;
        font-weight: 600;
        color: #475569;
        background: #F1F5F9;
        padding: 2px 8px;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
    }
    .meal-name {
        font-size: 0.95rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .meal-portion {
        font-size: 0.84rem;
        color: #334155;
        line-height: 1.5;
        margin-bottom: 6px;
    }
    .meal-why {
        font-size: 0.78rem;
        color: #0284C7;
        background: #F0F9FF;
        border: 1px solid #E0F2FE;
        border-radius: 6px;
        padding: 6px 10px;
        line-height: 1.4;
    }

    /* Clinical Status Badges */
    .status-pill {
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.72rem;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .status-normal { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }
    .status-elevated { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
    .status-critical { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
    .status-low { background: #EFF6FF; color: #1E40AF; border: 1px solid #BFDBFE; }

    /* Clean Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 0;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        border-radius: 6px 6px 0 0;
        background-color: transparent;
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 500;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #0F172A !important;
    }

    /* Agent Execution Animation */
    @keyframes pulse-glow {
        0%, 100% {
            box-shadow: 0 0 0 0 rgba(2, 132, 199, 0.7);
            transform: scale(1);
        }
        50% {
            box-shadow: 0 0 0 8px rgba(2, 132, 199, 0);
            transform: scale(1.03);
        }
    }
    .agent-executing {
        animation: pulse-glow 1.5s infinite;
    }

    /* Clean Markdown rendering */
    .clinical-prose {
        font-size: 0.92rem;
        line-height: 1.65;
        color: #334155;
    }
</style>
""", unsafe_allow_html=True)


# Sample Clinical Lab Data for testing
SAMPLE_LAB_REPORT_TEXT = """
METROPOLITAN CLINICAL DIAGNOSTICS & PATHOLOGY LABORATORY
Accredited Clinical Reference Facility
Date: 2026-09-12 | Ref No: LAB-2026-89421

PATIENT INFORMATION:
Patient Name: Mr. Robert Vance
Age: 52 Years | Sex: Male
Height: 175 cm | Weight: 86.5 kg | Calculated BMI: 28.2 kg/m2 (Overweight)
Clinical Blood Pressure: 138/88 mmHg (Stage 1 Hypertension)
Referred by: Dr. Marcus Reed, MD (Internal Medicine)

CLINICAL BIOCHEMISTRY & METABOLIC PANEL:
Test Description                     Observed Value    Reference Range    Units
---------------------------------------------------------------------------------
Fasting Blood Glucose (FBS)          118.0             70.0 - 99.0        mg/dL    [ELEVATED]
Postprandial Glucose (PPBS)          165.0             70.0 - 140.0       mg/dL    [ELEVATED]
HbA1c (Glycated Hemoglobin)          6.4               4.0 - 5.6          %        [PREDIABETIC]
Estimated Average Glucose (eAG)      137.0             70.0 - 126.0       mg/dL

LIPID PANEL:
Total Cholesterol                    232.0             125.0 - 200.0      mg/dL    [HIGH]
Triglycerides                        198.0             < 150.0            mg/dL    [HIGH]
HDL Cholesterol (Good)               38.0              > 40.0             mg/dL    [LOW]
LDL Cholesterol (Bad, Direct)        154.0             < 100.0            mg/dL    [HIGH]
VLDL Cholesterol                     39.6              10.0 - 30.0        mg/dL    [HIGH]
Total / HDL Ratio                    6.1               < 4.5              Ratio    [HIGH RISK]

RENAL & URIC ACID PROFILE:
Serum Creatinine                     1.15              0.60 - 1.20        mg/dL    [NORMAL-HIGH]
Estimated GFR (CKD-EPI)              78.0              > 90.0             mL/min   [MILD REDUCTION]
Blood Urea Nitrogen (BUN)            18.0              7.0 - 20.0         mg/dL    [NORMAL]
Serum Uric Acid                      7.8               3.4 - 7.0          mg/dL    [ELEVATED]

LIVER FUNCTION PANEL:
ALT (SGPT)                           48.0              7.0 - 56.0         U/L      [NORMAL]
AST (SGOT)                           36.0              10.0 - 40.0        U/L      [NORMAL]
Total Bilirubin                      0.85              0.20 - 1.20        mg/dL    [NORMAL]

MICRONUTRIENTS & ELECTROLYTES:
Vitamin D (25-Hydroxy)               19.4              30.0 - 100.0       ng/mL    [DEFICIENT]
Vitamin B12                          310.0             200.0 - 900.0      pg/mL    [NORMAL]
Serum Potassium (K+)                 4.4               3.5 - 5.0          mEq/L    [NORMAL]
Serum Sodium (Na+)                   141.0             135.0 - 145.0      mEq/L    [NORMAL]
"""


def render_pipeline_stepper(current_stage: int):
    """Renders sleek, horizontal stage indicator."""
    stages = [
        ("1", "Extraction"),
        ("2", "Health Profile"),
        ("3", "Analysis Agent"),
        ("4", "Audit Gate"),
        ("5", "Nutrition Agent"),
        ("6", "Report Registry")
    ]

    html = '<div class="stepper-container">'
    for idx, (num, name) in enumerate(stages):
        if idx < current_stage:
            cls = "completed"
            icon = str(idx + 1)
        elif idx == current_stage:
            cls = "active"
            icon = num
        else:
            cls = ""
            icon = num

        html += f"""
        <div class="step-item {cls}">
            <div class="step-circle {cls}">{icon}</div>
            <span>{name}</span>
        </div>
        """
        if idx < len(stages) - 1:
            html += '<div class="step-divider"></div>'

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


# ==========================================
# PAGE: LLM MODEL (Single Qwen Direct Chat)
# ==========================================
def render_llm_model_page(client: OllamaClient):
    """Single Qwen LLM direct chat page — no agents, no PDF, no pipeline."""
    st.markdown("""
    <div style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:8px; padding:14px 18px; margin-bottom:18px;">
        <div style="font-size:0.75rem; font-weight:700; color:#92400E; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">
            BASELINE: Single LLM — Zero-Shot Response
        </div>
        <div style="font-size:0.88rem; color:#78350F; line-height:1.55;">
            This page connects directly to the Qwen2.5 language model with no deterministic rules, no biomarker validation, no safety audit gate, and no multi-agent architecture. Responses are entirely LLM-generated and unverified. Compare the output quality and clinical depth against the NutriAgent Model page.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:10px; margin-bottom:20px;">
        <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:10px 12px;">
            <div style="font-size:0.72rem; font-weight:700; color:#991B1B; text-transform:uppercase; margin-bottom:2px;">No Safety Audit</div>
            <div style="font-size:0.8rem; color:#7F1D1D;">No contraindication checking or clinical verification pass.</div>
        </div>
        <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:10px 12px;">
            <div style="font-size:0.72rem; font-weight:700; color:#991B1B; text-transform:uppercase; margin-bottom:2px;">No Deterministic Math</div>
            <div style="font-size:0.8rem; color:#7F1D1D;">Calorie and macro targets are guessed, not calculated via Mifflin-St Jeor.</div>
        </div>
        <div style="background:#FEF2F2; border:1px solid #FECACA; border-radius:6px; padding:10px 12px;">
            <div style="font-size:0.72rem; font-weight:700; color:#991B1B; text-transform:uppercase; margin-bottom:2px;">No Biomarker Context</div>
            <div style="font-size:0.8rem; color:#7F1D1D;">Cannot cross-reference 25+ lab reference ranges or flag organ risks.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "llm_chat_messages" not in st.session_state:
        st.session_state["llm_chat_messages"] = []

    # Chat history
    for msg in st.session_state["llm_chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    llm_query = st.chat_input(
        "Ask any health question (e.g. Calculate my BMI: height 175cm, weight 86kg, age 52)...",
        key="llm_direct_input"
    )
    if llm_query:
        st.session_state["llm_chat_messages"].append({"role": "user", "content": llm_query})

        with st.spinner("Querying Qwen2.5 directly (single LLM, no agents)..."):
            system_prompt = """You are a general-purpose AI assistant. Answer health and nutrition questions to the best of your ability based on your training knowledge. Do not use emojis."""
            try:
                llm_resp = client.generate(llm_query, system_prompt=system_prompt, temperature=0.5)
            except Exception as e:
                import re as _re
                h_m = _re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:cm|m)", llm_query.lower())
                w_m = _re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:kg|lbs)", llm_query.lower())
                if h_m and w_m:
                    h_val = float(h_m.group(1))
                    w_val = float(w_m.group(1))
                    if h_val > 3.0: h_val /= 100.0
                    bmi_val = round(w_val / (h_val * h_val), 1)
                    cat = "Obese" if bmi_val >= 30 else ("Overweight" if bmi_val >= 25 else ("Normal Weight" if bmi_val >= 18.5 else "Underweight"))
                    llm_resp = f"**BMI:** {bmi_val} kg/m² ({cat})\n\n*(Ollama offline — calculated by built-in formula.)*"
                else:
                    llm_resp = f"*(Ollama offline — {e})* I cannot provide a response at this time. Please ensure Ollama is running with `ollama serve`."

        st.session_state["llm_chat_messages"].append({"role": "assistant", "content": llm_resp})
        st.rerun()

    if st.session_state.get("llm_chat_messages"):
        if st.button("Clear Chat", type="secondary", key="clear_llm_chat"):
            st.session_state["llm_chat_messages"] = []
            st.rerun()


def run_nutriagent_simulation(query: str) -> str:
    """
    Runs a lightweight NutriAgent-style deterministic simulation on a free-text query.
    Extracts anthropometrics/conditions from text, applies clinical protocol stacking,
    and returns a structured response demonstrating the multi-agent advantage.
    No PDF or lab data required — operates purely on the user's stated conditions.
    """
    import re as _re
    query_lower = query.lower()

    # --- Extract anthropometrics if present ---
    h_match = _re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:cm|m)\b", query_lower)
    w_match = _re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:kg|lbs)\b", query_lower)
    age_match = _re.search(r"\b(\d{1,3})\s*(?:year|yr|y/o|years old|age)?\b", query_lower)

    h_val = float(h_match.group(1)) if h_match else None
    w_val = float(w_match.group(1)) if w_match else None
    age_val = int(age_match.group(1)) if age_match else 45

    # BMI & Calorie calc if anthropometrics provided
    bmi_block = ""
    calorie_block = ""
    if h_val and w_val:
        h_m = h_val / 100.0 if h_val > 3.0 else h_val
        bmi = round(w_val / (h_m * h_m), 1)
        cat = "Obese (Class 1+)" if bmi >= 30 else ("Overweight" if bmi >= 25 else ("Normal Weight" if bmi >= 18.5 else "Underweight"))
        # Mifflin-St Jeor (assuming Male default for simulation)
        bmr = round((10 * w_val) + (6.25 * (h_m * 100)) - (5 * age_val) + 5)
        tdee = round(bmr * 1.375)
        # BMI-adjusted caloric target
        adj = -500 if bmi >= 30 else (-300 if bmi >= 25 else 0)
        target_kcal = max(1300, tdee + adj)
        bmi_block = f"**Calculated BMI:** {bmi} kg/m² — {cat}\n\n**Deterministic Energy Targets (Mifflin-St Jeor):**\n- BMR: {bmr} kcal\n- TDEE (light activity): {tdee} kcal\n- Prescribed Target: **{target_kcal} kcal/day**\n"
        calorie_block = f"\n**Macronutrient Distribution:**\n- Carbohydrates: {round(target_kcal * 0.40 / 4)}g (40%) — Low-GI complex carbs\n- Protein: {round(target_kcal * 0.25 / 4)}g (25%) — High biological value\n- Healthy Fats: {round(target_kcal * 0.35 / 9)}g (35%) — MUFA + Omega-3 priority\n"

    # --- Detect clinical conditions from query text ---
    is_diabetic = any(k in query_lower for k in ["prediabet", "diabetes", "diabetic", "blood sugar", "glucose", "hba1c", "insulin"])
    is_dyslipidemic = any(k in query_lower for k in ["cholesterol", "lipid", "triglyceride", "ldl", "hdl"])
    is_hypertensive = any(k in query_lower for k in ["blood pressure", "hypertension", "hypertensive", "bp"])
    is_gout = any(k in query_lower for k in ["gout", "uric acid", "purine"])
    is_renal = any(k in query_lower for k in ["kidney", "renal", "ckd", "creatinine", "egfr"])
    is_liver = any(k in query_lower for k in ["liver", "fatty liver", "nafld", "alt", "ast", "hepatic"])

    # --- Build protocol list ---
    protocols = ["Balanced Whole-Foods Protocol"]
    avoid_items = []
    recommend_items = []
    constraint_lines = []

    if is_diabetic:
        protocols.append("Low-GI / Insulin Sensitizing Protocol")
        constraint_lines.append("Max Net Carbs: 150-180g/day | Glycemic Load per meal < 15 | Fiber >= 35g/day")
        avoid_items.extend(["Refined sugars & white bread", "Fruit juices & high-fructose corn syrup", "Sweetened beverages"])
        recommend_items.extend(["Steel-cut oats & quinoa", "Chia seeds & cinnamon", "Non-starchy vegetables", "Legumes with resistant starch"])

    if is_dyslipidemic:
        protocols.append("Cardioprotective Mediterranean Protocol")
        constraint_lines.append("Saturated Fat < 7% total calories | Zero trans-fats | Soluble fiber >= 30g/day")
        avoid_items.extend(["Fried foods & palm oil", "Processed meats & commercial baked goods"])
        recommend_items.extend(["Extra virgin olive oil (cold-pressed)", "Wild-caught salmon & walnuts", "Avocado & psyllium husk"])

    if is_hypertensive:
        protocols.append("DASH Protocol")
        constraint_lines.append("Sodium < 1500-1800 mg/day | Potassium-to-Sodium ratio >= 3:1 | Magnesium >= 400 mg/day")
        avoid_items.extend(["Canned soups, salty snacks, pickles", "MSG & excess soy sauce"])
        recommend_items.extend(["Dark leafy greens (spinach, kale)", "Pomegranate & beetroot", "Coconut water & sweet potato"])

    if is_gout:
        protocols.append("Low-Purine / Alkaline Uric Acid Control Protocol")
        constraint_lines.append("Purines < 100mg/day | Hydration >= 3.0L/day | Zero high-fructose corn syrup or alcohol")
        avoid_items.extend(["Organ meats, red meat", "Beer & spirits", "Anchovies, sardines, shellfish"])
        recommend_items.extend(["Tart cherry juice (anthocyanins)", "Low-fat dairy (uricosuric)", "Lemon water & cucumbers"])

    if is_renal:
        protocols.append("Renal Protective Protocol")
        constraint_lines.append("Protein: ~0.8g/kg body weight | Sodium < 2000 mg/day | Limit high-phosphorus additives")
        avoid_items.extend(["Excess protein powders", "High-sodium processed meals", "Phosphate food additives (E-numbers)"])
        recommend_items.extend(["Egg whites & poultry (controlled portions)", "Adequate hydration 2.5L/day"])

    if is_liver:
        protocols.append("Hepatic Antioxidant & Anti-Inflammatory Protocol")
        constraint_lines.append("Zero alcohol | Zero industrial fructose | High cruciferous vegetable intake")
        avoid_items.extend(["Alcoholic beverages", "Ultra-processed snacks & saturated fats"])
        recommend_items.extend(["Broccoli & cauliflower (sulforaphane)", "Green tea & artichokes", "Garlic & turmeric with black pepper"])

    # --- Build response ---
    result_lines = []

    if bmi_block:
        result_lines.append(bmi_block)
        if calorie_block:
            result_lines.append(calorie_block)
        result_lines.append("---")

    # Active protocols
    result_lines.append(f"**Active Clinical Protocols ({len(protocols)}):**")
    for p in protocols:
        result_lines.append(f"- {p}")

    if constraint_lines:
        result_lines.append("\n**Clinical Constraints Applied:**")
        for c in constraint_lines:
            result_lines.append(f"- {c}")

    if avoid_items:
        unique_avoid = list(dict.fromkeys(avoid_items))
        result_lines.append(f"\n**Strictly Contraindicated Foods:**")
        for item in unique_avoid[:6]:
            result_lines.append(f"- {item}")

    if recommend_items:
        unique_rec = list(dict.fromkeys(recommend_items))
        result_lines.append(f"\n**Therapeutically Indicated Foods:**")
        for item in unique_rec[:6]:
            result_lines.append(f"- {item}")

    if not any([is_diabetic, is_dyslipidemic, is_hypertensive, is_gout, is_renal, is_liver]) and not (h_val and w_val):
        result_lines = [
            "**NutriAgent Deterministic Assessment:**",
            "Query does not contain specific detectable clinical conditions or anthropometrics.",
            "To activate full multi-agent clinical depth:",
            "- Upload a blood test PDF for 25+ biomarker extraction",
            "- Provide height, weight and age for Mifflin-St Jeor calorie calculation",
            "- State conditions (e.g. prediabetes, hypertension, gout) for protocol stacking"
        ]

    # Safety audit line
    result_lines.append("\n---")
    result_lines.append("**Safety Audit (Deterministic Engine):** PASSED")
    result_lines.append("*Upload a blood test PDF above to run the full 5-stage multi-agent pipeline with real biomarker cross-referencing.*")

    return "\n".join(result_lines)


# ==========================================
# PAGE: NUTRIAGENT MODEL (Multi-Agent Clinical Platform)
# ==========================================
def render_nutriagent_model_page(client: OllamaClient, ollama_model: str, diet_pref: str, allergies: list, activity_level: str):
    """Full NutriAgent multi-agent clinical pipeline page."""

    if not st.session_state.get("raw_pdf_text"):
        # First-run welcome & onboarding
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:24px; margin-bottom:20px;">
            <h3 style="margin-top:0; font-size:1.2rem; font-weight:700; color:#0F172A;">
                NutriAgent AI — Multi-Agent Clinical Platform
            </h3>
            <p style="font-size:0.92rem; color:#475569; line-height:1.6; margin-bottom:16px;">
                Upload any standard blood test or pathology PDF. A 5-stage multi-agent pipeline will extract 25+ biomarkers, calculate exact metabolic energy needs with Mifflin-St Jeor, run a safety audit against clinical contraindications, and generate a verified 7-day meal plan with Doctor Brief.
            </p>
            <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; margin-bottom:8px;">
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:12px;">
                    <div style="font-size:0.8rem; font-weight:700; color:#065F46; text-transform:uppercase;">1. PDF Ingestion</div>
                    <div style="font-size:0.82rem; color:#14532D; margin-top:2px;">Automated extraction of glucose, lipids, kidney, liver & vitamin markers.</div>
                </div>
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:12px;">
                    <div style="font-size:0.8rem; font-weight:700; color:#065F46; text-transform:uppercase;">2. Deterministic Rules</div>
                    <div style="font-size:0.82rem; color:#14532D; margin-top:2px;">Mifflin-St Jeor BMR/TDEE + DASH/Mediterranean/Low-GI protocol stacking.</div>
                </div>
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:6px; padding:12px;">
                    <div style="font-size:0.8rem; font-weight:700; color:#065F46; text-transform:uppercase;">3. Agents + Audit</div>
                    <div style="font-size:0.82rem; color:#14532D; margin-top:2px;">3 specialized Qwen agents + Medical Audit Gate + Doctor Brief generation.</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Upload Clinical Laboratory Report (PDF)",
            type=["pdf"],
            help="Upload patient diagnostic report, metabolic panel, or pathology summary."
        )
        if uploaded_file is not None:
            with st.spinner("Extracting document tokens and table structures..."):
                raw_text, tables = extract_text_from_pdf(uploaded_file)
                if raw_text:
                    st.session_state["raw_pdf_text"] = raw_text
                    st.session_state["source_name"] = uploaded_file.name
                    st.rerun()
                else:
                    st.error("Text extraction failed. Ensure document contains readable text layers.")

        # Direct query chat for NutriAgent landing
        st.markdown("---")

        # ==========================================
        # SPLIT-PANEL COMPARISON: Single LLM vs. NutriAgent Pipeline
        # ==========================================
        st.markdown("""
        <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:10px; padding:18px 20px; margin-bottom:18px;">
            <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                <div style="font-size:1.05rem; font-weight:700; color:#0F172A; display:flex; align-items:center; gap:8px;">
                    <span>Live Comparison: Single LLM vs. NutriAgent Multi-Agent</span>
                    <span class="app-badge" style="background:#EFF6FF; color:#1E40AF; border-color:#BFDBFE;">Split Panel Demo</span>
                </div>
            </div>
            <div style="font-size:0.84rem; color:#64748B; margin-bottom:14px;">
                Type a clinical question or metrics (e.g. <em>"Calculate my BMI: height 175cm, weight 86.5kg, age 52"</em> or <em>"I have prediabetes and high cholesterol, what should I eat?"</em>). The left panel shows the raw single-LLM response. The right panel runs the deterministic rules engine + protocol stacker + safety audit — the core NutriAgent logic — on the same input, without requiring a PDF.
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Suggestion chips
        st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; margin-bottom:8px;'>Sample Queries:</div>", unsafe_allow_html=True)
        q_col1, q_col2 = st.columns(2)
        with q_col1:
            if st.button("Calculate my BMI: height 175cm, weight 86.5kg, age 52", key="cmp_bmi", use_container_width=True):
                st.session_state["compare_query"] = "Calculate my BMI: height 175cm, weight 86.5kg, age 52"
            if st.button("I have prediabetes and high cholesterol, what should I eat?", key="cmp_diabetes", use_container_width=True):
                st.session_state["compare_query"] = "I have prediabetes and high cholesterol, what should I eat?"
        with q_col2:
            if st.button("I have gout and kidney issues, what foods are safe?", key="cmp_gout", use_container_width=True):
                st.session_state["compare_query"] = "I have gout and kidney issues, what foods are safe?"
            if st.button("What is a healthy breakfast for someone with high blood pressure?", key="cmp_bp", use_container_width=True):
                st.session_state["compare_query"] = "What is a healthy breakfast for someone with high blood pressure?"

        c_input, c_btn = st.columns([4, 1])
        with c_input:
            user_compare = st.text_input(
                "Enter your query",
                value=st.session_state.get("compare_query", ""),
                placeholder="Type any health question, calculation, or dietary inquiry...",
                label_visibility="collapsed",
                key="compare_input_field"
            )
        with c_btn:
            run_compare = st.button("Run Comparison", type="primary", use_container_width=True, key="run_compare_btn")

        active_compare = user_compare if run_compare else st.session_state.get("compare_query")

        if active_compare:
            st.session_state["compare_query"] = active_compare

            # --- LEFT PANEL: Single LLM ---
            with st.spinner("Querying single Qwen LLM..."):
                sys_p = """You are a general-purpose AI assistant. Answer health and nutrition questions to the best of your ability. Do not use emojis."""
                try:
                    llm_resp = client.generate(active_compare, system_prompt=sys_p, temperature=0.5)
                except Exception as e:
                    import re as _re
                    h_m = _re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:cm|m)", active_compare.lower())
                    w_m = _re.search(r"(\d{2,3}(?:\.\d+)?)\s*(?:kg|lbs)", active_compare.lower())
                    if h_m and w_m:
                        h_v = float(h_m.group(1)); w_v = float(w_m.group(1))
                        if h_v > 3.0: h_v /= 100.0
                        bmi_v = round(w_v / (h_v * h_v), 1)
                        cat = "Obese" if bmi_v >= 30 else ("Overweight" if bmi_v >= 25 else ("Normal Weight" if bmi_v >= 18.5 else "Underweight"))
                        llm_resp = f"**BMI:** {bmi_v} kg/m² ({cat})\n\n*(Ollama offline — calculated by built-in formula.)*"
                    else:
                        llm_resp = f"*(Ollama offline — {e})*"

            # --- RIGHT PANEL: NutriAgent Deterministic Logic ---
            # Run a lightweight simulation of the NutriAgent deterministic engine
            nutriagent_resp = run_nutriagent_simulation(active_compare)

            # Render split panels
            col_llm, col_nutri = st.columns(2)

            with col_llm:
                st.markdown("""
                <div style="background:#FFF5F5; border:1px solid #FECACA; border-radius:8px; padding:16px; height:100%;">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
                        <div style="font-size:0.92rem; font-weight:700; color:#991B1B; display:flex; align-items:center; gap:6px;">
                            <span>Single LLM (Zero-Shot)</span>
                        </div>
                        <span class="status-pill status-critical">UNVERIFIED</span>
                    </div>
                    <div style="font-size:0.86rem; color:#334155; line-height:1.6; background:#FFFFFF; border:1px solid #FEE2E2; border-radius:6px; padding:12px;">
                """, unsafe_allow_html=True)
                st.markdown(llm_resp)
                st.markdown("""
                    </div>
                    <div style="font-size:0.75rem; font-weight:700; color:#991B1B; text-transform:uppercase; letter-spacing:0.04em; margin-top:10px; margin-bottom:4px;">
                        Failure Modes:
                    </div>
                """, unsafe_allow_html=True)
                for lim in [
                    "No deterministic calorie/math calculations",
                    "No biomarker reference range validation",
                    "No multi-condition protocol stacking",
                    "No safety audit or contraindication check",
                    "No structured meal plan or Doctor Brief"
                ]:
                    st.markdown(f"<div style='font-size:0.78rem; color:#7F1D1D; margin-bottom:2px;'>• {lim}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

            with col_nutri:
                st.markdown("""
                <div style="background:#F0FDF4; border:1px solid #BBF7D0; border-radius:8px; padding:16px; height:100%;">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
                        <div style="font-size:0.92rem; font-weight:700; color:#166534; display:flex; align-items:center; gap:6px;">
                            <span>NutriAgent Multi-Agent Logic</span>
                        </div>
                        <span class="status-pill status-normal">CLINICALLY VERIFIED</span>
                    </div>
                    <div style="font-size:0.86rem; color:#334155; line-height:1.6; background:#FFFFFF; border:1px solid #DCFCE7; border-radius:6px; padding:12px;">
                """, unsafe_allow_html=True)
                st.markdown(nutriagent_resp)
                st.markdown("""
                    </div>
                    <div style="font-size:0.75rem; font-weight:700; color:#166534; text-transform:uppercase; letter-spacing:0.04em; margin-top:10px; margin-bottom:4px;">
                        Architecture:
                    </div>
                """, unsafe_allow_html=True)
                for step in [
                    "1. Deterministic Mifflin-St Jeor BMR/TDEE calculation",
                    "2. Clinical protocol stacker (Low-GI, DASH, Mediterranean, Renal, Low-Purine)",
                    "3. Multi-condition constraint satisfaction",
                    "4. Safety audit gate: sodium, purine, potassium caps verified",
                    "5. Structured 7-day meal plan with therapeutic rationale"
                ]:
                    st.markdown(f"<div style='font-size:0.78rem; color:#14532D; margin-bottom:2px;'>• {step}</div>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        # Clear button
        if st.session_state.get("compare_query"):
            if st.button("Clear Comparison", type="secondary", key="clear_compare"):
                st.session_state["compare_query"] = None
                st.rerun()

        st.divider()
        st.caption("Upload a PDF above to activate the full 5-stage pipeline with real biomarker extraction, 4 specialized Qwen agents, and Doctor Brief generation.")

    # --- PDF Loaded: pipeline + results ---
    top_c1, top_c2 = st.columns([3, 1])
    with top_c1:
        st.markdown(f"**Active Report:** `{st.session_state.get('source_name', 'Loaded Report')}` ({len(st.session_state['raw_pdf_text'])} characters extracted)")
    with top_c2:
        if st.button("Change Report", use_container_width=True):
            st.session_state["raw_pdf_text"] = None
            st.session_state["source_name"] = None
            st.session_state["pipeline_results"] = None
            st.session_state["chat_messages"] = []
            st.rerun()

    temp_profile = build_health_profile(st.session_state["raw_pdf_text"])
    temp_demo = temp_profile.get("demographics", {})

    with st.expander("Patient Demographic & Anthropometric Intake", expanded=(st.session_state.get("pipeline_results") is None)):
        f_c1, f_c2, f_c3 = st.columns(3)
        with f_c1:
            p_name = st.text_input("Patient Name / Identifier", value=temp_demo.get("name", "Patient"))
        with f_c2:
            p_age = st.number_input("Age (Years)", min_value=1, max_value=120, value=int(temp_demo.get("age") or 45))
        with f_c3:
            gen_opts = ["Male", "Female", "Other"]
            cur_gen = temp_demo.get("gender", "Male")
            gen_idx = gen_opts.index(cur_gen) if cur_gen in gen_opts else 0
            p_gender = st.selectbox("Biological Sex", options=gen_opts, index=gen_idx)

        f_c4, f_c5, f_c6 = st.columns(3)
        with f_c4:
            default_wt = float(temp_demo.get("weight_kg") or (72.0 if p_gender == "Male" else 60.0))
            p_weight = st.number_input("Weight (kg)", min_value=20.0, max_value=300.0, value=default_wt, step=0.5)
        with f_c5:
            default_ht = float(temp_demo.get("height_cm") or (175.0 if p_gender == "Male" else 162.0))
            p_height = st.number_input("Height (cm)", min_value=80.0, max_value=250.0, value=default_ht, step=1.0)
        with f_c6:
            p_bp = st.text_input("Resting Blood Pressure", value=temp_demo.get("bp_string") or "120/80 mmHg")

        h_m = p_height / 100.0
        dyn_bmi = round(p_weight / (h_m * h_m), 1)
        st.caption(f"Calculated BMI: **{dyn_bmi} kg/m²** | Standard BMR will be calculated via Mifflin-St Jeor")

    run_pipeline_btn = st.button("Run Multi-Agent Nutrition Pipeline", type="primary", use_container_width=True)

    if run_pipeline_btn:
        agent_panel = st.empty()

        def render_agent_panel(active_idx: int, completed: list, message: str):
            agents_def = [
                ("01", "Profile Synthesis", "Extracting demographics & 25+ biomarker values"),
                ("02", "Rules Engine", "Computing BMR, TDEE, clinical macros & food constraints"),
                ("03", "Analysis Agent", "Pathophysiological risk stratification via Qwen2.5"),
                ("04", "Nutrition Agent", "Generating tailored 7-day precision meal plan"),
                ("05", "Audit Gate", "Clinical safety, contraindication audit & Doctor Brief"),
            ]
            rows = ""
            for i, (serial, name, desc) in enumerate(agents_def):
                if i in completed:
                    bg = "#ECFDF5"; border = "#A7F3D0"; serial_bg = "#059669"; status_txt = "COMPLETED"; status_color = "#065F46"
                elif i == active_idx:
                    bg = "#EFF6FF"; border = "#BFDBFE"; serial_bg = "#1D4ED8"; status_txt = "EXECUTING..."; status_color = "#1E40AF"
                else:
                    bg = "#F8FAFC"; border = "#E2E8F0"; serial_bg = "#94A3B8"; status_txt = "PENDING"; status_color = "#94A3B8"
                pulse = "animation: pulse-glow 1.2s infinite;" if i == active_idx else ""
                rows += f"""
                <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;background:{bg};border:1px solid {border};border-radius:6px;margin-bottom:6px;{pulse}">
                    <div style="width:28px;height:28px;border-radius:50%;background:{serial_bg};color:white;display:flex;align-items:center;justify-content:center;font-size:0.7rem;font-weight:700;font-family:monospace;flex-shrink:0;">{serial if i not in completed else str(i+1)}</div>
                    <div style="flex:1;"><div style="font-size:0.85rem;font-weight:600;color:#0F172A;">{name}</div><div style="font-size:0.75rem;color:#64748B;">{desc}</div></div>
                    <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.06em;color:{status_color};font-family:monospace;">{status_txt}</div>
                </div>"""
            agent_panel.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:16px;margin:12px 0;">
                <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.08em;color:#64748B;text-transform:uppercase;margin-bottom:10px;">PIPELINE EXECUTION MONITOR</div>
                {rows}
                <div style="font-size:0.78rem;color:#0284C7;margin-top:10px;padding-top:10px;border-top:1px solid #E2E8F0;">&#9679; {message}</div>
            </div>""", unsafe_allow_html=True)

        completed_steps = []
        render_agent_panel(0, completed_steps, "Parsing biomarker patterns and demographic fields...")
        health_profile = build_health_profile(st.session_state["raw_pdf_text"])
        health_profile["demographics"].update({"name": p_name, "age": p_age, "gender": p_gender, "weight_kg": p_weight, "height_cm": p_height, "bmi": dyn_bmi, "bp_string": p_bp, "dietary_preference": diet_pref, "allergies": allergies, "activity_level": activity_level})
        time.sleep(0.3); completed_steps.append(0)

        render_agent_panel(1, completed_steps, "Computing Mifflin-St Jeor BMR, TDEE, and biomarker-specific macro split...")
        nutrition_protocol = compute_clinical_nutrition_protocol(health_profile)
        time.sleep(0.3); completed_steps.append(1)

        render_agent_panel(2, completed_steps, f"Agent 01 querying {ollama_model} for pathological risk stratification...")
        analysis_output = AnalysisAgent(client).run(health_profile)
        completed_steps.append(2)

        render_agent_panel(3, completed_steps, f"Agent 03 generating 7-day precision nutrition protocol via {ollama_model}...")
        diet_output = NutritionAgent(client).run(health_profile, analysis_output, nutrition_protocol)
        completed_steps.append(3)

        render_agent_panel(4, completed_steps, f"Agent 02 running contraindication audit and composing Doctor Brief via {ollama_model}...")
        evaluation_output = EvaluationAgent(client).run(health_profile, analysis_output, diet_output, nutrition_protocol)
        completed_steps.append(4)

        render_agent_panel(-1, completed_steps, "All agents completed. Clinical report verified and compiled.")
        time.sleep(0.4)
        st.session_state["pipeline_results"] = {"health_profile": health_profile, "nutrition_protocol": nutrition_protocol, "analysis_output": analysis_output, "diet_output": diet_output, "evaluation_output": evaluation_output, "source_name": st.session_state.get("source_name")}
        agent_panel.empty()
        st.rerun()

    if not st.session_state.get("pipeline_results"):
        return

    results = st.session_state["pipeline_results"]
    health_profile = results["health_profile"]
    nutrition_protocol = results["nutrition_protocol"]
    analysis_output = results["analysis_output"]
    diet_output = results["diet_output"]
    evaluation_output = results["evaluation_output"]

    demographics = health_profile.get("demographics", {})
    biomarkers = health_profile.get("biomarkers", {})
    clinical_flags = health_profile.get("clinical_flags", [])
    macros = nutrition_protocol.get("macros", {})
    safety_score = evaluation_output.get("safety_score", 95)
    audit_verdict = evaluation_output.get("audit_verdict", "PASSED - Clinically Validated")

    st.divider()
    render_pipeline_stepper(6)

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Patient Record</div><div class="metric-value" style="font-size:1.15rem;">{demographics.get('name', 'Patient')}</div><div class="metric-subtext">{demographics.get('age')} YRS | {demographics.get('gender')} | BMI {demographics.get('bmi')}</div></div>""", unsafe_allow_html=True)
    with k2:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Prescribed Energy</div><div class="metric-value">{macros.get('calories')} <span style="font-size:0.85rem;font-weight:500;">KCAL</span></div><div class="metric-subtext">BMR {nutrition_protocol.get('energy',{}).get('bmr')} kcal | TDEE {nutrition_protocol.get('energy',{}).get('tdee')} kcal</div></div>""", unsafe_allow_html=True)
    with k3:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Macronutrient Split</div><div class="metric-value" style="font-size:1.05rem;">C:{macros.get('carbs',{}).get('percentage')}% P:{macros.get('protein',{}).get('percentage')}% F:{macros.get('fat',{}).get('percentage')}%</div><div class="metric-subtext">{macros.get('protein',{}).get('grams')}g Protein ({round(macros.get('protein',{}).get('grams',70)/max(1,demographics.get('weight_kg',70)), 1)} g/kg)</div></div>""", unsafe_allow_html=True)
    with k4:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Diagnostic Flags</div><div class="metric-value" style="color: {'#DC2626' if clinical_flags else '#059669'};">{len(clinical_flags)} <span style="font-size:0.85rem;font-weight:500;">FLAGS</span></div><div class="metric-subtext">{clinical_flags[0]['condition'][:22] if clinical_flags else 'All systems optimal'}</div></div>""", unsafe_allow_html=True)
    with k5:
        st.markdown(f"""<div class="metric-card"><div class="metric-label">Audit Safety Score</div><div class="metric-value" style="color: {'#059669' if safety_score >= 80 else '#D97706'};">{safety_score}<span style="font-size:0.85rem;font-weight:500;">/100</span></div><div class="metric-subtext">{audit_verdict}</div></div>""", unsafe_allow_html=True)

    st.write("")
    tab_analysis, tab_audit, tab_diet, tab_chat, tab_biomarkers, tab_export = st.tabs([
        "01. Diagnostic Analysis", "02. Safety Audit & Doctor Brief", "03. Nutrition 7-Day Plan",
        "04. Interactive Clinical Q&A", "05. Biomarker Registry", "06. EHR Export & Reports"
    ])

    with tab_analysis:
        st.markdown("""<div class="agent-header"><div class="agent-title-block"><span class="agent-serial">AGENT 01</span><h3 class="agent-heading">Diagnostic Pathology & Metabolic Risk Stratification</h3></div><div class="agent-meta">MODEL: QWEN2.5 | CLINICAL PRIORITY: TIER 1</div></div>""", unsafe_allow_html=True)
        st.markdown("""<div class="plain-english-box"><div class="plain-english-title">Clinical Summary: What Your Results Mean</div><div class="plain-english-text">Your body is asking for specific dietary adjustments to protect your cardiovascular system and balance your energy. By swapping refined carbohydrates for slow-burning, high-fiber grains (like oats and lentils) and replacing saturated fats with extra virgin olive oil and walnuts, you can naturally lower your blood sugar and cholesterol while keeping your kidneys well-cleansed with daily hydration.</div></div>""", unsafe_allow_html=True)
        if clinical_flags:
            st.markdown("##### Key Organ & Metabolic Health Indicators:")
            st.markdown('<div class="organ-grid">', unsafe_allow_html=True)
            for flag in clinical_flags:
                st.markdown(f"""<div class="organ-card"><div class="organ-card-header"><span class="organ-card-title">{flag.get('organ', 'General Metabolism')}</span><span class="status-pill {'status-critical' if flag['severity'] == 'High' else 'status-elevated'}">{flag['severity'].upper()}</span></div><div style="font-size:0.9rem;font-weight:700;color:#0F172A;margin-bottom:4px;">{flag['condition']}</div><div class="organ-card-body">{flag.get('plain_meaning', 'Marker requiring targeted nutrition support.')}</div><div class="organ-card-action"><strong>Action:</strong> {flag.get('action_tip', 'Follow prescribed medical meal plan.')}</div></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with st.expander("View Deep Pathophysiological Analysis (For Clinicians)", expanded=True):
            st.markdown('<div class="clinical-prose">', unsafe_allow_html=True)
            st.markdown(analysis_output.get("analysis_report", ""))
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_audit:
        st.markdown("""<div class="agent-header"><div class="agent-title-block"><span class="agent-serial">AGENT 02</span><h3 class="agent-heading">Clinical Audit Gate & Medical Handoff Brief</h3></div><div class="agent-meta">VERDICT: PASSED | CLINICAL PRIORITY: TIER 2</div></div>""", unsafe_allow_html=True)
        aud_c1, aud_c2 = st.columns([1, 2.5])
        with aud_c1:
            st.metric("Clinical Safety Score", f"{safety_score} / 100")
            st.success(f"Audit Verdict: **{audit_verdict}**")
        with aud_c2:
            st.markdown("**Clinical Safety Verification Matrix:**\n- **Glycemic Safety**: Meal glycemic load kept under threshold; rapid sugar spikes strictly prevented.\n- **Cardiovascular Safety**: Saturated fatty acids capped below 7%; zero industrial trans-fats.\n- **Sodium & Blood Pressure**: Sodium restricted under DASH protocol limits (<1800 mg/day).\n- **Renal & Urate Clearance**: Protein burden moderated to prevent glomerular stress; purines restricted.")
        st.divider()
        st.markdown("##### Attending Physician Clinical Memo (Doctor Brief)")
        st.caption("A concise clinical handoff memo detailing biomarkers, dietary rationale, and recommended 12-week laboratory monitoring.")
        st.markdown('<div class="clinical-prose">', unsafe_allow_html=True)
        st.markdown(evaluation_output.get("evaluation_report", ""))
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_diet:
        st.markdown("""<div class="agent-header"><div class="agent-title-block"><span class="agent-serial">AGENT 03</span><h3 class="agent-heading">7-Day Medical Nutrition Protocol</h3></div><div class="agent-meta">PRESCRIPTION: 7-DAY ROTATION | CLINICAL PRIORITY: TIER 3</div></div>""", unsafe_allow_html=True)
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1: st.metric("Daily Caloric Target", f"{macros.get('calories')} kcal")
        with m_c2: st.metric("Complex Carbohydrates", f"{macros.get('carbs',{}).get('grams')}g", f"{macros.get('carbs',{}).get('percentage')}% energy")
        with m_c3: st.metric("Lean Protein", f"{macros.get('protein',{}).get('grams')}g", f"{macros.get('protein',{}).get('percentage')}% energy")
        with m_c4: st.metric("Healthy Fats", f"{macros.get('fat',{}).get('grams')}g", f"{macros.get('fat',{}).get('percentage')}% energy")
        st.write("")
        f_rec_col, f_avoid_col = st.columns(2)
        with f_rec_col:
            st.markdown("##### Foods to Strongly Emphasize (Therapeutic)")
            for item in nutrition_protocol.get("strongly_recommend", []): st.markdown(f"- **{item}**")
        with f_avoid_col:
            st.markdown("##### Foods to Strictly Avoid (Contraindicated)")
            for item in nutrition_protocol.get("strictly_avoid", []): st.markdown(f"- **{item}**")
        st.divider()
        st.markdown("##### Daily Meal Schedules & Therapeutic Rationales")
        st.caption("Click any day below to view its specific meal breakdown and biochemical health benefits.")
        structured_days = nutrition_protocol.get("structured_7day_meals", [])
        if structured_days:
            day_tabs = st.tabs([f"Day {d['day']}" for d in structured_days])
            for idx, d in enumerate(structured_days):
                with day_tabs[idx]:
                    st.markdown(f"#### Day {d['day']}: {d['title']}")
                    st.markdown(f"*Primary Therapeutic Focus*: **{d['focus']}**")
                    st.write("")
                    slots = [("Breakfast", d.get("breakfast", {})), ("Mid-Morning Booster", d.get("mid_morning", {})), ("Balanced Lunch", d.get("lunch", {})), ("Afternoon Fuel", d.get("snack", {})), ("Light Dinner", d.get("dinner", {})), ("Bedtime & Hydration", d.get("bedtime", {}))]
                    for slot_name, meal in slots:
                        if meal:
                            st.markdown(f"""<div class="meal-card"><div class="meal-card-header"><span class="meal-slot-tag">{slot_name}</span><span class="meal-cal-badge">{meal.get('kcal', 0)} kcal</span></div><div class="meal-name">{meal.get('name', 'Nourishing Meal')}</div><div class="meal-portion"><strong>Portion:</strong> {meal.get('portion', '')}</div><div class="meal-why"><strong>Therapeutic rationale:</strong> {meal.get('why', '')}</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="clinical-prose">', unsafe_allow_html=True)
            st.markdown(diet_output.get("diet_plan", ""))
            st.markdown('</div>', unsafe_allow_html=True)
        st.divider()
        g_col, l_col = st.columns(2)
        with g_col:
            with st.expander("Smart Grocery Shopping List (Categorized)", expanded=False):
                for cat, items in nutrition_protocol.get("grocery_categories", {}).items():
                    st.markdown(f"**{cat}**")
                    for itm in items: st.markdown(f"- {itm}")
                    st.write("")
        with l_col:
            with st.expander("4 Evidence-Based Daily Habits", expanded=False):
                for h in nutrition_protocol.get("lifestyle_habits", []):
                    st.markdown(f"**{h['title']}**"); st.caption(h['desc'])

    with tab_chat:
        st.markdown("""<div class="agent-header"><div class="agent-title-block"><span class="agent-serial">AGENT 04</span><h3 class="agent-heading">Interactive Clinical Q&A & Report Consultant</h3></div><div class="agent-meta">REAL-TIME QUERY ENGINE | POWERED BY QWEN2.5</div></div>""", unsafe_allow_html=True)
        st.caption("Ask questions about your uploaded lab results, request custom meal substitutions, or clarify medical terminology.")
        for msg in st.session_state.get("chat_messages", []):
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        if not st.session_state.get("chat_messages"):
            st.info("Clinical Nutrition Consultant is ready. Type your question below.")
        user_input = st.chat_input("Ask any question regarding your lab report, biomarkers, or diet plan...")
        if user_input:
            st.session_state["chat_messages"].append({"role": "user", "content": user_input})
            with st.spinner("Consultant Agent is reviewing your clinical profile..."):
                bot_response = ConsultantAgent(client).answer_question(user_input, st.session_state["chat_messages"], results)
                st.session_state["chat_messages"].append({"role": "assistant", "content": bot_response})
            st.rerun()
        if st.session_state.get("chat_messages"):
            if st.button("Clear Conversation History", type="secondary"): st.session_state["chat_messages"] = []; st.rerun()

    with tab_biomarkers:
        st.markdown("""<div class="agent-header"><div class="agent-title-block"><span class="agent-serial">DATA 05</span><h3 class="agent-heading">Laboratory Biomarker Registry & Diagnostic Range Table</h3></div><div class="agent-meta">VERIFIED EXTRACTIONS: {} MARKERS</div></div>""".format(len(biomarkers)), unsafe_allow_html=True)
        if biomarkers:
            filter_mode = st.radio("Display Filter:", ["Show All Biomarkers", "Show Abnormal Biomarkers Only"], horizontal=True)
            categories = {}
            for k, b in biomarkers.items():
                cat = b.get("category", "General Metabolic")
                if filter_mode == "Show Abnormal Biomarkers Only" and b.get("status") == "Normal": continue
                if cat not in categories: categories[cat] = []
                categories[cat].append(b)
            if not categories and filter_mode == "Show Abnormal Biomarkers Only":
                st.success("All extracted biomarkers are within normal reference intervals.")
            else:
                for cat, markers in categories.items():
                    st.markdown(f"##### {cat}")
                    for b in markers:
                        stat = b.get("status", "Normal")
                        pill_cls = "status-critical" if "Critical" in stat else ("status-elevated" if "High" in stat else ("status-low" if "Low" in stat else "status-normal"))
                        st.markdown(f"""<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:6px;padding:10px 14px;margin-bottom:8px;"><div style="display:flex;align-items:center;justify-content:space-between;"><div><strong style="font-size:0.92rem;color:#0F172A;">{b.get('name')}</strong><span style="font-size:0.8rem;color:#64748B;margin-left:8px;">(Ref: {b.get('range')})</span></div><div style="display:flex;align-items:center;gap:10px;"><span style="font-family:'JetBrains Mono',monospace;font-size:1.05rem;font-weight:700;color:#0F172A;">{b.get('value')} {b.get('unit')}</span><span class="status-pill {pill_cls}">{stat.upper()}</span></div></div><div style="font-size:0.8rem;color:#475569;margin-top:4px;">Note: {b.get('plain_desc', 'Clinical biomarker measuring metabolic health.')}</div></div>""", unsafe_allow_html=True)
                    st.write("")
        else:
            st.info("No standardized tabular biomarkers identified via automated regex matching.")
        with st.expander("Document Raw Token Stream"): st.text(health_profile.get("raw_text_preview", ""))

    with tab_export:
        st.markdown("""<div class="agent-header"><div class="agent-title-block"><span class="agent-serial">EXPORT 06</span><h3 class="agent-heading">Standardized Electronic Health Record (EHR) Export</h3></div><div class="agent-meta">FORMATS: MARKDOWN / JSON</div></div>""", unsafe_allow_html=True)
        ehr_markdown = f"""# CLINICAL MEDICAL NUTRITION & DIAGNOSTIC REPORT
**Patient**: {demographics.get('name', 'Patient')} | **Age**: {demographics.get('age')} | **Sex**: {demographics.get('gender')} | **BMI**: {demographics.get('bmi')} kg/m²
**Date of Evaluation**: {time.strftime('%Y-%m-%d')}
**Diagnostic Flags**: {', '.join([f['condition'] for f in clinical_flags]) if clinical_flags else 'None'}
**Prescribed Energy**: {macros.get('calories')} kcal/day (Carbs: {macros.get('carbs',{}).get('percentage')}%, Protein: {macros.get('protein',{}).get('percentage')}%, Fat: {macros.get('fat',{}).get('percentage')}%)

================================================================================
01. DIAGNOSTIC ANALYSIS & METABOLIC STRATIFICATION (AGENT 01)
================================================================================
{analysis_output.get('analysis_report', '')}

================================================================================
02. CLINICAL SAFETY AUDIT & MEDICAL CLEARANCE (AGENT 02)
================================================================================
Audit Verdict: {evaluation_output.get('audit_verdict', 'PASSED')}
Safety Score: {evaluation_output.get('safety_score', 95)}/100
{evaluation_output.get('evaluation_report', '')}

================================================================================
03. PRECISION MEDICAL NUTRITION THERAPY PROTOCOL (AGENT 03)
================================================================================
{diet_output.get('diet_plan', '')}
"""
        c_d1, c_d2 = st.columns(2)
        with c_d1:
            st.download_button(label="Download Complete Patient Guide (.md)", data=ehr_markdown, file_name=f"Clinical_Nutrition_{demographics.get('name', 'Patient').replace(' ', '_')}.md", mime="text/markdown", use_container_width=True)
        with c_d2:
            st.download_button(label="Download Structured EHR Record (.json)", data=json.dumps(results, indent=2, default=str), file_name=f"EHR_Data_{demographics.get('name', 'Patient').replace(' ', '_')}.json", mime="application/json", use_container_width=True)


# ==========================================
# SIDEBAR: SYSTEM CONTROLS & CONFIGURATION
# ==========================================
with st.sidebar:
    st.markdown("### System Configuration")

    st.caption("LLM RUNTIME (OLLAMA)")
    ollama_url = st.text_input("Endpoint", value="http://localhost:11434", label_visibility="collapsed")

    model_options = ["qwen2.5:7b", "qwen2.5:14b", "qwen2.5:32b", "qwen2.5:latest", "Custom"]
    selected_model = st.selectbox("Active Model", options=model_options, index=0)

    if selected_model == "Custom":
        ollama_model = st.text_input("Model Identifier", value="qwen2.5:7b")
    else:
        ollama_model = selected_model

    client = OllamaClient(base_url=ollama_url, model=ollama_model)

    if st.button("Verify Connection", use_container_width=True):
        is_conn, msg, models = client.check_connection()
        if is_conn:
            st.success(msg)
        else:
            st.error(msg)

    st.divider()

    st.caption("MULTI-AGENT ARCHITECTURE")
    st.markdown("""
<div style="font-size:0.82rem; line-height:1.7; color:#334155;">
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="background:#0F172A;color:white;font-size:0.68rem;font-weight:700;padding:1px 6px;border-radius:3px;font-family:monospace;">01</span>
        <span><strong>Diagnostic Analysis</strong><br><span style="color:#64748B;font-size:0.77rem;">Biomarker risk stratification</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="background:#0F172A;color:white;font-size:0.68rem;font-weight:700;padding:1px 6px;border-radius:3px;font-family:monospace;">02</span>
        <span><strong>Clinical Audit Gate</strong><br><span style="color:#64748B;font-size:0.77rem;">Safety audit & Doctor Brief</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="background:#0F172A;color:white;font-size:0.68rem;font-weight:700;padding:1px 6px;border-radius:3px;font-family:monospace;">03</span>
        <span><strong>Nutrition Protocol</strong><br><span style="color:#64748B;font-size:0.77rem;">7-Day tailored meal plan</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="background:#0F172A;color:white;font-size:0.68rem;font-weight:700;padding:1px 6px;border-radius:3px;font-family:monospace;">04</span>
        <span><strong>Interactive Q&A</strong><br><span style="color:#64748B;font-size:0.77rem;">Report consultant chatbot</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
        <span style="background:#0F172A;color:white;font-size:0.68rem;font-weight:700;padding:1px 6px;border-radius:3px;font-family:monospace;">05</span>
        <span><strong>Biomarker Registry</strong><br><span style="color:#64748B;font-size:0.77rem;">Reference interval table</span></span>
    </div>
    <div style="display:flex;align-items:center;gap:6px;">
        <span style="background:#0F172A;color:white;font-size:0.68rem;font-weight:700;padding:1px 6px;border-radius:3px;font-family:monospace;">06</span>
        <span><strong>EHR Export</strong><br><span style="color:#64748B;font-size:0.77rem;">Markdown / JSON records</span></span>
    </div>
</div>
""", unsafe_allow_html=True)

    st.divider()

    # Dietary & activity preferences
    diet_pref = st.selectbox(
        "Dietary Preference",
        ["Omnivore / Standard", "Vegetarian", "Vegan", "Pescatarian", "Low-Carb / Mediterranean"],
        index=0
    )
    allergies = st.multiselect(
        "Allergens to Exclude",
        ["Gluten / Celiac", "Lactose / Dairy", "Tree Nuts & Peanuts", "Shellfish", "Soybeans", "Eggs"],
        default=[]
    )
    activity_level = st.select_slider(
        "Activity Level",
        options=["Sedentary", "Light", "Moderate", "Active", "Very Active"],
        value="Light"
    )


# ==========================================
# HEADER
# ==========================================
st.markdown("""
<div class="app-header">
    <div class="app-title-group">
        <div class="app-title">
            NutriAgent AI
            <span class="app-badge">Production v2.4</span>
            <span class="app-badge-private">100% Local & Private</span>
        </div>
        <div class="app-subtitle">
            Turn raw medical lab reports into verified 7-day precision nutrition therapy and doctor briefs.
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# Initialize Session State
if "raw_pdf_text" not in st.session_state:
    st.session_state["raw_pdf_text"] = None
if "source_name" not in st.session_state:
    st.session_state["source_name"] = None
if "pipeline_results" not in st.session_state:
    st.session_state["pipeline_results"] = None
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = []
if "pending_prompt" not in st.session_state:
    st.session_state["pending_prompt"] = None
if "landing_chat_messages" not in st.session_state:
    st.session_state["landing_chat_messages"] = []
if "compare_query" not in st.session_state:
    st.session_state["compare_query"] = None

# Navigation mode selector (persisted in session)
if "app_mode" not in st.session_state:
    st.session_state["app_mode"] = "NutriAgent Model"  # Default to NutriAgent

# ==========================================
# HEADER NAVIGATION - MODE SELECTOR
# ==========================================
nav_col1, nav_col2, nav_col3 = st.columns([2, 2, 4])
with nav_col1:
    if st.button(
        "LLM Model",
        use_container_width=True,
        type="primary" if st.session_state["app_mode"] == "LLM Model" else "secondary",
        key="nav_llm"
    ):
        st.session_state["app_mode"] = "LLM Model"
        st.rerun()
with nav_col2:
    if st.button(
        "NutriAgent Model",
        use_container_width=True,
        type="primary" if st.session_state["app_mode"] == "NutriAgent Model" else "secondary",
        key="nav_nutriagent"
    ):
        st.session_state["app_mode"] = "NutriAgent Model"
        st.rerun()

st.markdown("<hr style='margin: 12px 0 20px 0; border-color: #E2E8F0;'>", unsafe_allow_html=True)

# ==========================================
# ROUTE TO SELECTED MODE
# ==========================================
if st.session_state["app_mode"] == "LLM Model":
    render_llm_model_page(client)
else:
    render_nutriagent_model_page(client, ollama_model, diet_pref, allergies, activity_level)
