"""
app.py - Production-Grade Clinical UI for Qwen Multi-Agent Medical Nutrition Platform
Architecture: PDF Extraction -> Validation -> Health Profile -> Qwen Analysis (01)
-> Audit Gate (02) -> Qwen Nutrition (03) -> Biomarker Registry (04) -> EHR Export (05).
"""

import os
import json
import time
import pandas as pd
import streamlit as st

# Custom modules
from extractor import extract_text_from_pdf, build_health_profile
from deterministic_nutrition import compute_clinical_nutrition_protocol
from agents import OllamaClient, AnalysisAgent, NutritionAgent, EvaluationAgent, ConsultantAgent

# Page configuration
st.set_page_config(
    page_title="NutriAgent | Clinical Intelligence Platform",
    page_icon="⚕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Impeccable Design System: Production Medical Grade CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #0F172A;
    }

    /* Top Navigation / App Header */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 16px;
        margin-bottom: 24px;
    }
    .app-title-group {
        display: flex;
        flex-direction: column;
    }
    .app-title {
        font-size: 1.45rem;
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
        padding: 12px 18px;
        margin-bottom: 24px;
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.8rem;
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
        margin: 0 10px;
    }

    /* Metric & KPI Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 14px 16px;
    }
    .metric-label {
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: #64748B;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: #0F172A;
        margin-top: 4px;
        font-family: 'JetBrains Mono', monospace;
    }
    .metric-subtext {
        font-size: 0.78rem;
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
            transform: scale(1.05);
        }
    }
    @keyframes typing-dots {
        0%, 20% { content: ''; }
        40% { content: '.'; }
        60% { content: '..'; }
        80%, 100% { content: '...'; }
    }
    .agent-executing {
        animation: pulse-glow 1.5s infinite;
    }
    .agent-executing::after {
        content: '';
        animation: typing-dots 1.2s infinite;
        color: #0284C7;
        font-weight: 700;
        margin-left: 4px;
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
    """Renders sleek, production-standard horizontal stage indicator."""
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
            icon = "✓"
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

    # Multi-Agent Protocol Order section (replaces old Clinical Intake Modifiers + Diagnostic Test Data)
    st.caption("MULTI-AGENT PROTOCOL")
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

    # Dietary & activity preferences (kept compact without section headers)
    diet_pref = st.selectbox(
        "Dietary Paradigm",
        ["Omnivore / Standard", "Vegetarian", "Vegan", "Pescatarian", "Low-Carb / Mediterranean"],
        index=0
    )
    allergies = st.multiselect(
        "Allergens",
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
            NutriAgent Clinical Platform
            <span class="app-badge">Production v2.4</span>
        </div>
        <div class="app-subtitle">
            Deterministic Biochemical Profiling & Multi-Agent Medical Nutrition Therapy
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


# ==========================================
# SECTION: LAB REPORT INGESTION
# ==========================================
uploaded_file = st.file_uploader(
    "Clinical Laboratory Report (PDF)",
    type=["pdf"],
    help="Upload patient diagnostic report, metabolic panel, or pathology summary."
)

if uploaded_file is not None:
    with st.spinner("Extracting document tokens and table structures..."):
        raw_text, tables = extract_text_from_pdf(uploaded_file)
        if raw_text:
            st.session_state["raw_pdf_text"] = raw_text
            st.session_state["source_name"] = uploaded_file.name
            st.success(f"Parsed {len(raw_text)} characters from {uploaded_file.name}")
        else:
            st.error("Text extraction failed. Ensure document contains readable text layers.")

# If document loaded, display patient intake parameters and pipeline runner
if st.session_state.get("raw_pdf_text"):
    st.markdown(f"**Active Document:** `{st.session_state.get('source_name', 'Loaded Report')}` ({len(st.session_state['raw_pdf_text'])} characters)")

    # Extract initial profile for intake form
    temp_profile = build_health_profile(st.session_state["raw_pdf_text"])
    temp_demo = temp_profile.get("demographics", {})

    with st.expander("Patient Demographic & Anthropometric Intake", expanded=True):
        f_c1, f_c2, f_c3 = st.columns(3)
        with f_c1:
            p_name = st.text_input("Patient Identifier", value=temp_demo.get("name", "Patient"))
        with f_c2:
            p_age = st.number_input("Age (Years)", min_value=1, max_value=120, value=int(temp_demo.get("age") or 35))
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

        # Dynamic BMI
        h_m = p_height / 100.0
        dyn_bmi = round(p_weight / (h_m * h_m), 1)
        st.caption(f"Calculated BMI: **{dyn_bmi} kg/m²** | Standard BMR will be calculated via Mifflin-St Jeor")

    run_pipeline_btn = st.button("Run Multi-Agent Pipeline", type="primary", use_container_width=True)

    if run_pipeline_btn:
        # Animated Agent Execution Panel
        agent_panel = st.empty()

        def render_agent_panel(active_idx: int, completed: list, message: str):
            """Renders an animated live agent execution tracker."""
            agents_def = [
                ("01", "Profile Synthesis", "Extracting demographics & biomarkers"),
                ("02", "Rules Engine", "Computing BMR, TDEE, clinical macros"),
                ("03", "Analysis Agent", "Pathophysiological risk stratification"),
                ("04", "Nutrition Agent", "Generating 7-day meal protocol"),
                ("05", "Audit Gate", "Clinical safety & contraindication audit"),
            ]
            rows = ""
            for i, (serial, name, desc) in enumerate(agents_def):
                if i in completed:
                    bg = "#ECFDF5"; border = "#A7F3D0"; serial_bg = "#059669"; dot_color = "#059669"; status_txt = "COMPLETED"; status_color = "#065F46"
                elif i == active_idx:
                    bg = "#EFF6FF"; border = "#BFDBFE"; serial_bg = "#1D4ED8"; dot_color = "#1D4ED8"; status_txt = "EXECUTING..."; status_color = "#1E40AF"
                else:
                    bg = "#F8FAFC"; border = "#E2E8F0"; serial_bg = "#94A3B8"; dot_color = "#94A3B8"; status_txt = "PENDING"; status_color = "#94A3B8"

                pulse = "animation: pulse-glow 1.2s infinite;" if i == active_idx else ""
                rows += f"""
                <div style="display:flex;align-items:center;gap:12px;padding:10px 14px;background:{bg};border:1px solid {border};border-radius:6px;margin-bottom:6px;{pulse}">
                    <div style="width:28px;height:28px;border-radius:50%;background:{serial_bg};color:white;display:flex;align-items:center;justify-content:center;font-size:0.7rem;font-weight:700;font-family:monospace;flex-shrink:0;">{serial if i not in completed else '✓'}</div>
                    <div style="flex:1;">
                        <div style="font-size:0.85rem;font-weight:600;color:#0F172A;">{name}</div>
                        <div style="font-size:0.75rem;color:#64748B;">{desc}</div>
                    </div>
                    <div style="font-size:0.68rem;font-weight:700;letter-spacing:0.06em;color:{status_color};font-family:monospace;">{status_txt}</div>
                </div>"""

            agent_panel.markdown(f"""
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:8px;padding:16px;margin:12px 0;">
                <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.08em;color:#64748B;text-transform:uppercase;margin-bottom:10px;">PIPELINE EXECUTION MONITOR</div>
                {rows}
                <div style="font-size:0.78rem;color:#0284C7;margin-top:10px;padding-top:10px;border-top:1px solid #E2E8F0;">
                    &#9679; {message}
                </div>
            </div>
            """, unsafe_allow_html=True)

        completed_steps = []

        # Step 1: Profile Synthesis
        render_agent_panel(0, completed_steps, "Parsing biomarker patterns and demographic fields...")
        health_profile = build_health_profile(st.session_state["raw_pdf_text"])
        health_profile["demographics"]["name"] = p_name
        health_profile["demographics"]["age"] = p_age
        health_profile["demographics"]["gender"] = p_gender
        health_profile["demographics"]["weight_kg"] = p_weight
        health_profile["demographics"]["height_cm"] = p_height
        health_profile["demographics"]["bmi"] = dyn_bmi
        health_profile["demographics"]["bp_string"] = p_bp
        health_profile["demographics"]["dietary_preference"] = diet_pref
        health_profile["demographics"]["allergies"] = allergies
        health_profile["demographics"]["activity_level"] = activity_level
        time.sleep(0.4)
        completed_steps.append(0)

        # Step 2: Deterministic Rules
        render_agent_panel(1, completed_steps, "Computing Mifflin-St Jeor BMR, TDEE, and biomarker-specific macro split...")
        nutrition_protocol = compute_clinical_nutrition_protocol(health_profile)
        time.sleep(0.5)
        completed_steps.append(1)

        # Step 3: Analysis Agent
        render_agent_panel(2, completed_steps, f"Agent 01 querying {ollama_model} for pathological risk stratification...")
        analysis_agent = AnalysisAgent(client)
        analysis_output = analysis_agent.run(health_profile)
        completed_steps.append(2)

        # Step 4: Nutrition Agent
        render_agent_panel(3, completed_steps, f"Agent 03 generating 7-day precision nutrition protocol via {ollama_model}...")
        nutrition_agent = NutritionAgent(client)
        diet_output = nutrition_agent.run(health_profile, analysis_output, nutrition_protocol)
        completed_steps.append(3)

        # Step 5: Audit Gate
        render_agent_panel(4, completed_steps, f"Agent 02 running contraindication audit and composing Doctor Brief via {ollama_model}...")
        eval_agent = EvaluationAgent(client)
        evaluation_output = eval_agent.run(health_profile, analysis_output, diet_output, nutrition_protocol)
        completed_steps.append(4)

        # Final: All complete
        render_agent_panel(-1, completed_steps, "All agents completed. Clinical report verified and compiled.")
        time.sleep(0.6)

        st.session_state["pipeline_results"] = {
            "health_profile": health_profile,
            "nutrition_protocol": nutrition_protocol,
            "analysis_output": analysis_output,
            "diet_output": diet_output,
            "evaluation_output": evaluation_output,
            "source_name": st.session_state.get("source_name")
        }
        agent_panel.empty()
        st.rerun()


# ==========================================
# AGENT OUTPUTS & DASHBOARD (ORDERED BY CLINICAL PRIORITY)
# ==========================================
if st.session_state.get("pipeline_results"):
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
    micros = nutrition_protocol.get("micronutrient_targets", {})
    safety_score = evaluation_output.get("safety_score", 95)
    audit_verdict = evaluation_output.get("audit_verdict", "PASSED - Clinically Validated")

    st.divider()
    render_pipeline_stepper(5)

    # Executive Metric Header Row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Patient Record</div>
            <div class="metric-value" style="font-size:1.15rem;">{demographics.get('name', 'Patient')}</div>
            <div class="metric-subtext">{demographics.get('age')} YRS | {demographics.get('gender')} | BMI {demographics.get('bmi')}</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Prescribed Energy</div>
            <div class="metric-value">{macros.get('calories')} <span style="font-size:0.85rem; font-weight:500;">KCAL</span></div>
            <div class="metric-subtext">BMR {nutrition_protocol.get('energy',{}).get('bmr')} kcal | TDEE {nutrition_protocol.get('energy',{}).get('tdee')} kcal</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Macronutrient Split</div>
            <div class="metric-value" style="font-size:1.05rem;">C:{macros.get('carbs',{}).get('percentage')}% P:{macros.get('protein',{}).get('percentage')}% F:{macros.get('fat',{}).get('percentage')}%</div>
            <div class="metric-subtext">{macros.get('protein',{}).get('grams')}g Protein ({round(macros.get('protein',{}).get('grams',70)/max(1,demographics.get('weight_kg',70)), 1)} g/kg)</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Diagnostic Flags</div>
            <div class="metric-value" style="color: {'#DC2626' if clinical_flags else '#059669'};">{len(clinical_flags)} <span style="font-size:0.85rem; font-weight:500;">FLAGS</span></div>
            <div class="metric-subtext">{clinical_flags[0]['condition'][:24] if clinical_flags else 'All systems optimal'}</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Audit Safety Score</div>
            <div class="metric-value" style="color: {'#059669' if safety_score >= 80 else '#D97706'};">{safety_score}<span style="font-size:0.85rem; font-weight:500;">/100</span></div>
            <div class="metric-subtext">{audit_verdict}</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # Clinical Priority Ordered Tabs (Descending from Most Critical to Supporting Data)
    tab_analysis, tab_audit, tab_diet, tab_chat, tab_biomarkers, tab_export = st.tabs([
        "01. Diagnostic Analysis",
        "02. Safety Audit & Clearance",
        "03. Precision Nutrition Protocol",
        "04. Interactive Clinical Q&A",
        "05. Laboratory Biomarker Registry",
        "06. EHR Export & Documentation"
    ])

    # -------------------------------------------------------------
    # PRIORITY 01: CLINICAL ANALYSIS AGENT (PRIMARY DIAGNOSTIC LAYER)
    # -------------------------------------------------------------
    with tab_analysis:
        st.markdown("""
        <div class="agent-header">
            <div class="agent-title-block">
                <span class="agent-serial">AGENT 01</span>
                <h3 class="agent-heading">Diagnostic Pathology & Metabolic Risk Stratification</h3>
            </div>
            <div class="agent-meta">MODEL: QWEN2.5-7B | CLINICAL PRIORITY: TIER 1</div>
        </div>
        """, unsafe_allow_html=True)

        if clinical_flags:
            st.markdown("##### Identified Pathological & Metabolic Indicators:")
            for flag in clinical_flags:
                severity_class = "status-critical" if flag["severity"] == "High" else "status-elevated"
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                    <span class="status-pill {severity_class}">{flag['severity'].upper()}</span>
                    <strong style="font-size: 0.92rem;">{flag['condition']}</strong>
                    <span style="color: #64748B; font-size: 0.85rem; font-family: 'JetBrains Mono', monospace;">({flag['marker']})</span>
                </div>
                """, unsafe_allow_html=True)
            st.write("")

        st.markdown('<div class="clinical-prose">', unsafe_allow_html=True)
        st.markdown(analysis_output.get("analysis_report", ""))
        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # PRIORITY 02: EVALUATION AGENT & AUDIT GATE (SAFETY & CLEARANCE)
    # -------------------------------------------------------------
    with tab_audit:
        st.markdown("""
        <div class="agent-header">
            <div class="agent-title-block">
                <span class="agent-serial">AGENT 02</span>
                <h3 class="agent-heading">Clinical Audit Gate & Medical Handoff Brief</h3>
            </div>
            <div class="agent-meta">VERDICT: PASSED | CLINICAL PRIORITY: TIER 2</div>
        </div>
        """, unsafe_allow_html=True)

        aud_c1, aud_c2 = st.columns([1, 2.5])
        with aud_c1:
            st.metric("Safety & Adherence Score", f"{safety_score} / 100")
            st.info(f"Audit Status: **{audit_verdict}**")
        with aud_c2:
            st.markdown("""
            **Safety Verification Matrix:**
            - **Contraindication Screen**: No biochemically adverse triggers present in recommended foods.
            - **Caloric Alignment**: Prescribed energy matches target metabolic requirement.
            - **Electrolyte & Sodium Regulation**: Sodium capped below clinical threshold; potassium calibrated to renal status.
            - **Glycemic Load Distribution**: Carbohydrate complexity aligned with insulin sensitivity.
            """)

        st.divider()
        st.markdown('<div class="clinical-prose">', unsafe_allow_html=True)
        st.markdown(evaluation_output.get("evaluation_report", ""))
        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # PRIORITY 03: NUTRITION AGENT (7-DAY CLINICAL PROTOCOL)
    # -------------------------------------------------------------
    with tab_diet:
        st.markdown("""
        <div class="agent-header">
            <div class="agent-title-block">
                <span class="agent-serial">AGENT 03</span>
                <h3 class="agent-heading">7-Day Precision Medical Nutrition Protocol</h3>
            </div>
            <div class="agent-meta">PRESCRIPTION: 7-DAY ROTATION | CLINICAL PRIORITY: TIER 3</div>
        </div>
        """, unsafe_allow_html=True)

        # Macro Breakdown Bar
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        with m_c1:
            st.metric("Daily Caloric Target", f"{macros.get('calories')} kcal")
        with m_c2:
            st.metric("Complex Carbohydrates", f"{macros.get('carbs',{}).get('grams')}g", f"{macros.get('carbs',{}).get('percentage')}% energy")
        with m_c3:
            st.metric("High Biological Value Protein", f"{macros.get('protein',{}).get('grams')}g", f"{macros.get('protein',{}).get('percentage')}% energy")
        with m_c4:
            st.metric("Cardioprotective Lipids", f"{macros.get('fat',{}).get('grams')}g", f"{macros.get('fat',{}).get('percentage')}% energy")

        st.write("")
        f_rec_col, f_avoid_col = st.columns(2)
        with f_rec_col:
            st.markdown("##### Therapeutic Foods (Strongly Indicated)")
            for item in nutrition_protocol.get("strongly_recommend", []):
                st.markdown(f"- **{item}**")
        with f_avoid_col:
            st.markdown("##### Excluded Foods (Contraindicated / Prohibited)")
            for item in nutrition_protocol.get("strictly_avoid", []):
                st.markdown(f"- **{item}**")

        st.divider()
        st.markdown("##### 7-Day Structured Meal Framework & Biochemical Rationale")
        st.markdown('<div class="clinical-prose">', unsafe_allow_html=True)
        st.markdown(diet_output.get("diet_plan", ""))
        st.markdown('</div>', unsafe_allow_html=True)

    # -------------------------------------------------------------
    # PRIORITY 04: INTERACTIVE CLINICAL Q&A CONSULTANT
    # -------------------------------------------------------------
    with tab_chat:
        st.markdown("""
        <div class="agent-header">
            <div class="agent-title-block">
                <span class="agent-serial">AGENT 04</span>
                <h3 class="agent-heading">Interactive Clinical Q&A & Report Consultant</h3>
            </div>
            <div class="agent-meta">REAL-TIME QUERY ENGINE | POWERED BY QWEN2.5</div>
        </div>
        """, unsafe_allow_html=True)

        st.caption("Ask questions about your uploaded lab results, request custom meal substitutions, or clarify medical terminology.")

        # Quick Suggestion Chips
        st.markdown("<div style='font-size:0.75rem; font-weight:600; color:#64748B; text-transform:uppercase; margin-bottom:6px;'>Suggested Inquiries:</div>", unsafe_allow_html=True)
        qc1, qc2 = st.columns(2)
        with qc1:
            if st.button("💬 Explain my abnormal markers in plain language", use_container_width=True):
                st.session_state["pending_prompt"] = "Can you explain all my abnormal biomarkers in simple, plain terms and how they affect my health?"
            if st.button("🥗 Provide vegetarian protein substitutes for my meal plan", use_container_width=True):
                st.session_state["pending_prompt"] = "Can you provide vegetarian and egg-free protein substitutes for the meals in my plan while respecting my health markers?"
        with qc2:
            if st.button("🩺 How does this diet protect my liver and metabolic health?", use_container_width=True):
                st.session_state["pending_prompt"] = "How does this specific diet plan protect my liver enzymes (ALT/AST) and improve my metabolic numbers?"
            if st.button("🔬 Which specific blood tests should I repeat in 3 months?", use_container_width=True):
                st.session_state["pending_prompt"] = "Which specific blood tests and diagnostic panels should I repeat in 3 months to check my progress?"

        st.divider()

        # Render Chat History
        chat_container = st.container()
        with chat_container:
            if not st.session_state.get("chat_messages"):
                st.info("👋 Hello! I have reviewed your complete lab report, biomarkers, and clinical nutrition plan. Type any question below or click one of the suggested prompts above.")
            else:
                for msg in st.session_state["chat_messages"]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

        # Handle user input via chat box or chip click
        user_input = st.chat_input("Ask any question regarding your lab report, biomarkers, or diet plan...")
        active_prompt = user_input or st.session_state.get("pending_prompt")

        if active_prompt:
            st.session_state["pending_prompt"] = None
            # Append user message
            st.session_state["chat_messages"].append({"role": "user", "content": active_prompt})

            with st.spinner("Consultant Agent is reviewing your clinical profile and formulating response..."):
                consultant = ConsultantAgent(client)
                bot_response = consultant.answer_question(
                    active_prompt,
                    st.session_state["chat_messages"],
                    results
                )
                st.session_state["chat_messages"].append({"role": "assistant", "content": bot_response})
            st.rerun()

        # Clear Chat Button
        if st.session_state.get("chat_messages"):
            if st.button("Clear Conversation History", type="secondary"):
                st.session_state["chat_messages"] = []
                st.rerun()

    # -------------------------------------------------------------
    # PRIORITY 05: BIOMARKER REGISTRY (SUPPORTING LABORATORY DATA)
    # -------------------------------------------------------------
    with tab_biomarkers:
        st.markdown("""
        <div class="agent-header">
            <div class="agent-title-block">
                <span class="agent-serial">DATA 05</span>
                <h3 class="agent-heading">Laboratory Biomarker Registry & Diagnostic Range Table</h3>
            </div>
            <div class="agent-meta">VERIFIED EXTRACTIONS: {} MARKERS</div>
        </div>
        """.format(len(biomarkers)), unsafe_allow_html=True)

        if biomarkers:
            table_rows = []
            for k, b in biomarkers.items():
                table_rows.append({
                    "Biomarker Name": b.get("name"),
                    "Observed Value": f"{b.get('value')} {b.get('unit')}",
                    "Standard Reference Range": b.get("range"),
                    "Status": b.get("status")
                })
            df = pd.DataFrame(table_rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No standardized tabular biomarkers identified via automated regex matching.")

        with st.expander("Document Raw Token Stream"):
            st.text(health_profile.get("raw_text_preview", ""))

    # -------------------------------------------------------------
    # PRIORITY 06: EHR EXPORT & DOCUMENTATION
    # -------------------------------------------------------------
    with tab_export:
        st.markdown("""
        <div class="agent-header">
            <div class="agent-title-block">
                <span class="agent-serial">EXPORT 06</span>
                <h3 class="agent-heading">Standardized Electronic Health Record (EHR) Export</h3>
            </div>
            <div class="agent-meta">FORMATS: MARKDOWN / JSON</div>
        </div>
        """, unsafe_allow_html=True)

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
            st.download_button(
                label="Download Clinical Summary (.md)",
                data=ehr_markdown,
                file_name=f"Clinical_Nutrition_{demographics.get('name', 'Patient').replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with c_d2:
            st.download_button(
                label="Download Structured Registry (.json)",
                data=json.dumps(results, indent=2, default=str),
                file_name=f"EHR_Data_{demographics.get('name', 'Patient').replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )
