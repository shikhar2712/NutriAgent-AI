"""
extractor.py - PDF Extraction, Validation & Health Profile Extraction
Handles PDF text extraction, lab report validation, and biomarker parsing.
"""

import io
import re
from typing import Dict, Any, List, Optional, Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


# Reference ranges for common clinical biomarkers with plain-language descriptions and organ categories
STANDARD_REFERENCE_RANGES = {
    "fasting_glucose": {
        "min": 70, "max": 99, "unit": "mg/dL", "name": "Fasting Blood Glucose",
        "category": "Blood Sugar & Diabetes",
        "plain_desc": "Blood sugar after an overnight fast. Key early indicator for diabetes and insulin resistance."
    },
    "postprandial_glucose": {
        "min": 70, "max": 140, "unit": "mg/dL", "name": "Postprandial Glucose",
        "category": "Blood Sugar & Diabetes",
        "plain_desc": "Blood sugar 2 hours after a meal. Shows how efficiently your body clears carbohydrates."
    },
    "hba1c": {
        "min": 4.0, "max": 5.6, "unit": "%", "name": "HbA1c (Glycated Hemoglobin)",
        "category": "Blood Sugar & Diabetes",
        "plain_desc": "Your 3-month average blood sugar score. Standard metric for diagnosing prediabetes and diabetes."
    },
    "total_cholesterol": {
        "min": 125, "max": 200, "unit": "mg/dL", "name": "Total Cholesterol",
        "category": "Heart & Lipids",
        "plain_desc": "Total amount of cholesterol circulating in your bloodstream."
    },
    "ldl_cholesterol": {
        "min": 0, "max": 100, "unit": "mg/dL", "name": "LDL Cholesterol (Bad)",
        "category": "Heart & Lipids",
        "plain_desc": "'Bad' cholesterol that can form plaque in blood vessels when elevated."
    },
    "hdl_cholesterol_male": {
        "min": 40, "max": 100, "unit": "mg/dL", "name": "HDL Cholesterol (Good, Male)",
        "category": "Heart & Lipids",
        "plain_desc": "'Good' protective cholesterol that sweeps excess fats out of your arteries."
    },
    "hdl_cholesterol_female": {
        "min": 50, "max": 100, "unit": "mg/dL", "name": "HDL Cholesterol (Good, Female)",
        "category": "Heart & Lipids",
        "plain_desc": "'Good' protective cholesterol that sweeps excess fats out of your arteries."
    },
    "triglycerides": {
        "min": 0, "max": 150, "unit": "mg/dL", "name": "Triglycerides",
        "category": "Heart & Lipids",
        "plain_desc": "Fat molecules from unused calories. High levels increase heart and liver risk."
    },
    "creatinine": {
        "min": 0.6, "max": 1.2, "unit": "mg/dL", "name": "Serum Creatinine",
        "category": "Kidney & Uric Acid",
        "plain_desc": "Natural waste product filtered by healthy kidneys. Rises if kidney filtration slows down."
    },
    "egfr": {
        "min": 90, "max": 150, "unit": "mL/min/1.73m²", "name": "eGFR (Kidney Filtration)",
        "category": "Kidney & Uric Acid",
        "plain_desc": "Estimated kidney filtration efficiency. Higher (above 90) means robust kidney cleansing."
    },
    "bun": {
        "min": 7, "max": 20, "unit": "mg/dL", "name": "Blood Urea Nitrogen (BUN)",
        "category": "Kidney & Uric Acid",
        "plain_desc": "Measures waste nitrogen from protein digestion; reflects kidney and hydration status."
    },
    "uric_acid_male": {
        "min": 3.4, "max": 7.0, "unit": "mg/dL", "name": "Uric Acid (Male)",
        "category": "Kidney & Uric Acid",
        "plain_desc": "Waste from purine breakdown. High levels can cause painful gout or kidney stones."
    },
    "uric_acid_female": {
        "min": 2.4, "max": 6.0, "unit": "mg/dL", "name": "Uric Acid (Female)",
        "category": "Kidney & Uric Acid",
        "plain_desc": "Waste from purine breakdown. High levels can cause painful gout or kidney stones."
    },
    "alt_sgpt": {
        "min": 7, "max": 56, "unit": "U/L", "name": "ALT (SGPT)",
        "category": "Liver Function",
        "plain_desc": "Liver-specific enzyme. Elevated values signal liver inflammation or fatty liver stress."
    },
    "ast_sgot": {
        "min": 10, "max": 40, "unit": "U/L", "name": "AST (SGOT)",
        "category": "Liver Function",
        "plain_desc": "Enzyme found in liver and muscle tissue; rises during cellular stress or injury."
    },
    "bilirubin_total": {
        "min": 0.2, "max": 1.2, "unit": "mg/dL", "name": "Total Bilirubin",
        "category": "Liver Function",
        "plain_desc": "Yellow pigment from red blood cell breakdown; reflects liver processing and bile flow."
    },
    "hemoglobin_male": {
        "min": 13.5, "max": 17.5, "unit": "g/dL", "name": "Hemoglobin (Male)",
        "category": "Blood Count (CBC)",
        "plain_desc": "Oxygen-carrying protein in red blood cells. Low values indicate anemia and fatigue."
    },
    "hemoglobin_female": {
        "min": 12.0, "max": 15.5, "unit": "g/dL", "name": "Hemoglobin (Female)",
        "category": "Blood Count (CBC)",
        "plain_desc": "Oxygen-carrying protein in red blood cells. Low values indicate anemia and fatigue."
    },
    "wbc_count": {
        "min": 4.5, "max": 11.0, "unit": "10^3/µL", "name": "White Blood Cell Count",
        "category": "Blood Count (CBC)",
        "plain_desc": "Immune defense cells. High values indicate infection or inflammation; low means lowered immunity."
    },
    "platelets": {
        "min": 150, "max": 450, "unit": "10^3/µL", "name": "Platelet Count",
        "category": "Blood Count (CBC)",
        "plain_desc": "Cell fragments essential for normal blood clotting and wound healing."
    },
    "vitamin_d": {
        "min": 30, "max": 100, "unit": "ng/mL", "name": "Vitamin D (25-OH)",
        "category": "Vitamins & Minerals",
        "plain_desc": "Crucial hormone-vitamin for calcium absorption, bone strength, immunity, and insulin sensitivity."
    },
    "vitamin_b12": {
        "min": 200, "max": 900, "unit": "pg/mL", "name": "Vitamin B12",
        "category": "Vitamins & Minerals",
        "plain_desc": "Essential for nerve health, DNA synthesis, and red blood cell formation."
    },
    "serum_ferritin": {
        "min": 20, "max": 250, "unit": "ng/mL", "name": "Serum Ferritin (Iron Stores)",
        "category": "Vitamins & Minerals",
        "plain_desc": "Your body's master iron storage bank. Low levels mean iron deficiency before anemia appears."
    },
    "tsh": {
        "min": 0.4, "max": 4.0, "unit": "µIU/mL", "name": "Thyroid Stimulating Hormone (TSH)",
        "category": "Thyroid & Hormones",
        "plain_desc": "Brain signal that regulates thyroid speed. High TSH means thyroid is sluggish (hypothyroid)."
    },
    "systolic_bp": {
        "min": 90, "max": 120, "unit": "mmHg", "name": "Systolic Blood Pressure",
        "category": "Vitals & Blood Pressure",
        "plain_desc": "Pressure in arteries when heart beats (top blood pressure number)."
    },
    "diastolic_bp": {
        "min": 60, "max": 80, "unit": "mmHg", "name": "Diastolic Blood Pressure",
        "category": "Vitals & Blood Pressure",
        "plain_desc": "Pressure in arteries when heart rests between beats (bottom blood pressure number)."
    },
    "serum_potassium": {
        "min": 3.5, "max": 5.0, "unit": "mEq/L", "name": "Serum Potassium (K+)",
        "category": "Electrolytes",
        "plain_desc": "Vital mineral for heart rhythm, muscle contractions, and fluid balance."
    },
    "serum_sodium": {
        "min": 135, "max": 145, "unit": "mEq/L", "name": "Serum Sodium (Na+)",
        "category": "Electrolytes",
        "plain_desc": "Main mineral for fluid volume and blood pressure regulation."
    },
    "serum_calcium": {
        "min": 8.5, "max": 10.2, "unit": "mg/dL", "name": "Serum Calcium",
        "category": "Electrolytes",
        "plain_desc": "Essential for bone density, nerve signaling, and muscle function."
    }
}


def extract_text_from_pdf(pdf_file) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Extracts text and tabular content from PDF file object or bytes.
    Returns (raw_text, tables).
    """
    raw_text = ""
    tables = []

    # Try pdfplumber first for high quality text & tables
    if PDFPLUMBER_AVAILABLE:
        try:
            if hasattr(pdf_file, "read"):
                pdf_bytes = pdf_file.read()
                pdf_file.seek(0)
                stream = io.BytesIO(pdf_bytes)
            elif isinstance(pdf_file, bytes):
                stream = io.BytesIO(pdf_file)
            else:
                stream = pdf_file

            with pdfplumber.open(stream) as pdf:
                for idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        raw_text += f"\n--- Page {idx + 1} ---\n" + page_text

                    page_tables = page.extract_tables()
                    if page_tables:
                        for tbl in page_tables:
                            tables.append({"page": idx + 1, "data": tbl})

            if raw_text.strip():
                return raw_text.strip(), tables
        except Exception as e:
            print(f"[Extractor] pdfplumber error: {e}, falling back to pypdf...")

    # Fallback to pypdf
    if PYPDF_AVAILABLE:
        try:
            if hasattr(pdf_file, "read"):
                pdf_file.seek(0)
                reader = pypdf.PdfReader(pdf_file)
            elif isinstance(pdf_file, bytes):
                reader = pypdf.PdfReader(io.BytesIO(pdf_file))
            else:
                reader = pypdf.PdfReader(pdf_file)

            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    raw_text += f"\n--- Page {idx + 1} ---\n" + page_text

            return raw_text.strip(), tables
        except Exception as e:
            print(f"[Extractor] pypdf error: {e}")

    # If neither worked or raw_text is empty, return empty
    return raw_text.strip(), tables


def validate_lab_report(raw_text: str) -> Dict[str, Any]:
    """
    Validates whether the extracted text contains valid clinical / medical / lab report content.
    Returns validation verdict, confidence score, and detected sections.
    """
    if not raw_text or len(raw_text.strip()) < 50:
        return {
            "valid": False,
            "confidence": 0.0,
            "reason": "The uploaded PDF is empty or text could not be extracted (may be a scanned image).",
            "detected_sections": [],
            "biomarker_hits": 0
        }

    medical_keywords = [
        "glucose", "cholesterol", "lipid", "triglycerides", "hba1c", "creatinine",
        "egfr", "hemoglobin", "hdl", "ldl", "uric acid", "sgot", "sgpt", "alt", "ast",
        "bilirubin", "wbc", "platelet", "vitamin", "tsh", "blood", "urine", "lab",
        "reference", "specimen", "patient", "fasting", "mg/dl", "u/l", "g/dl", "mmol/l"
    ]

    text_lower = raw_text.lower()
    matched_keywords = [kw for kw in medical_keywords if kw in text_lower]
    biomarker_hits = len(matched_keywords)

    detected_sections = []
    if any(k in text_lower for k in ["lipid", "cholesterol", "triglyceride", "hdl", "ldl"]):
        detected_sections.append("Lipid Panel")
    if any(k in text_lower for k in ["glucose", "hba1c", "glycated", "fasting sugar", "sugar"]):
        detected_sections.append("Glycemic / Diabetic Profile")
    if any(k in text_lower for k in ["creatinine", "egfr", "bun", "urea", "kidney", "renal"]):
        detected_sections.append("Renal Function Panel")
    if any(k in text_lower for k in ["alt", "ast", "sgot", "sgpt", "bilirubin", "liver", "hepatic"]):
        detected_sections.append("Liver Function Panel")
    if any(k in text_lower for k in ["hemoglobin", "wbc", "rbc", "platelet", "cbc", "complete blood"]):
        detected_sections.append("Complete Blood Count (CBC)")
    if any(k in text_lower for k in ["vitamin d", "vitamin b12", "ferritin", "iron"]):
        detected_sections.append("Micronutrients & Vitamins")
    if any(k in text_lower for k in ["tsh", "t3", "t4", "thyroid"]):
        detected_sections.append("Thyroid Profile")
    if any(k in text_lower for k in ["potassium", "sodium", "calcium", "electrolyte"]):
        detected_sections.append("Electrolyte Panel")

    confidence = min(1.0, (biomarker_hits / 10.0))
    is_valid = biomarker_hits >= 3 or len(detected_sections) >= 1

    return {
        "valid": is_valid,
        "confidence": round(confidence, 2),
        "reason": "Valid medical lab report detected." if is_valid else "Insufficient medical markers found.",
        "detected_sections": detected_sections,
        "biomarker_hits": biomarker_hits,
        "matched_keywords": matched_keywords[:12]
    }


def parse_patient_demographics(raw_text: str) -> Dict[str, Any]:
    """
    Extracts patient demographic details (Age, Gender, Weight, Height, Blood Pressure, Name).
    """
    demographics = {
        "name": "Patient",
        "age": 45,  # default fallback
        "gender": "Unknown",
        "weight_kg": None,
        "height_cm": None,
        "bmi": None,
        "systolic_bp": None,
        "diastolic_bp": None,
        "bp_string": None
    }

    # Name extraction
    name_match = re.search(r"(?:Patient\s*Name|Name|Pt\s*Name)\s*[:\-]?\s*([A-Za-z\s\.\,\'\_\-]+?)(?:\n|\r|\t|Age|Gender|Sex|DOB|Date|Patient\s*ID|Ref\s*No|$)", raw_text, re.IGNORECASE)
    if name_match:
        extracted_name = name_match.group(1).strip()
        # Clean up any trailing labels or punctuation
        extracted_name = re.sub(r"^(?:Mr\.|Mrs\.|Ms\.|Dr\.)\s*", "", extracted_name).strip()
        if len(extracted_name) >= 2 and len(extracted_name) < 40 and not any(k in extracted_name.lower() for k in ["report", "test", "specimen", "hospital", "patient id", "date"]):
            demographics["name"] = extracted_name

    # Age extraction (handles "Age: 52", "Age / Sex: 52 Yrs / Male", "52 Years Old")
    age_match = re.search(r"\bAge(?:\s*[\/\&]\s*(?:Sex|Gender))?\s*[:\-]?\s*(\d{1,3})\s*(?:Y|Yrs|Years)?\b", raw_text, re.IGNORECASE)
    if age_match:
        age_val = int(age_match.group(1))
        if 5 <= age_val <= 115:
            demographics["age"] = age_val
    else:
        age_match_alt = re.search(r"\b(\d{1,3})\s*(?:Y|Yrs|Years\s*Old)\b", raw_text, re.IGNORECASE)
        if age_match_alt:
            age_val = int(age_match_alt.group(1))
            if 5 <= age_val <= 115:
                demographics["age"] = age_val

    # Gender extraction
    gender_match = re.search(r"\b(?:Gender|Sex)\s*[:\-]?\s*(?:(?:Yrs|Years|\d+)\s*[\/\-]\s*)?(Male|Female|M|F|Other)\b", raw_text, re.IGNORECASE)
    if gender_match:
        g = gender_match.group(1).strip().upper()
        if g in ["M", "MALE"]:
            demographics["gender"] = "Male"
        elif g in ["F", "FEMALE"]:
            demographics["gender"] = "Female"
    else:
        if re.search(r"\b(?:Male)\b", raw_text, re.IGNORECASE) and not re.search(r"\bFemale\b", raw_text, re.IGNORECASE):
            demographics["gender"] = "Male"
        elif re.search(r"\b(?:Female)\b", raw_text, re.IGNORECASE):
            demographics["gender"] = "Female"

    # Combined Height / Weight pattern (e.g. "Height / Weight: 175 cm / 86.5 kg")
    combo_hw = re.search(r"\b(?:Height\s*[\/\&]\s*Weight)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*(?:cm|cms|m)?\s*[\/\&]\s*(\d{2,3}(?:\.\d+)?)\s*(?:kg|kgs|lbs)?\b", raw_text, re.IGNORECASE)
    if combo_hw:
        try:
            h = float(combo_hw.group(1))
            w = float(combo_hw.group(2))
            if h < 3.0: h *= 100
            demographics["height_cm"] = h
            demographics["weight_kg"] = w
        except ValueError:
            pass

    # Individual Weight extraction if not matched
    if not demographics["weight_kg"]:
        weight_match = re.search(r"(?<!Height\s[\/\&])\b(?:Weight|Wt)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*(?:kg|kgs|lbs)?\b", raw_text, re.IGNORECASE)
        if weight_match:
            try:
                w_val = float(weight_match.group(1))
                if 25.0 <= w_val <= 300.0:
                    demographics["weight_kg"] = w_val
            except ValueError:
                pass

    # Individual Height extraction if not matched
    if not demographics["height_cm"]:
        height_match = re.search(r"\b(?:Height|Ht)\s*[:\-]?\s*(\d{2,3}(?:\.\d+)?)\s*(?:cm|cms|m)?\b", raw_text, re.IGNORECASE)
        if height_match:
            try:
                h = float(height_match.group(1))
                if h < 3.0:  # In meters
                    h = h * 100
                if 80.0 <= h <= 250.0:
                    demographics["height_cm"] = h
            except ValueError:
                pass

    # BMI calculation or extraction
    bmi_match = re.search(r"\b(?:BMI|Body Mass Index)\s*[:\-]?\s*(\d{1,2}(?:\.\d+)?)\b", raw_text, re.IGNORECASE)
    if bmi_match:
        try:
            demographics["bmi"] = float(bmi_match.group(1))
        except ValueError:
            pass
    elif demographics["weight_kg"] and demographics["height_cm"]:
        h_m = demographics["height_cm"] / 100.0
        demographics["bmi"] = round(demographics["weight_kg"] / (h_m * h_m), 1)

    # Blood Pressure (e.g. 138/88 or 120 / 80 mmHg)
    bp_match = re.search(r"(?:Blood\s*Pressure|BP)\s*[:\-]?\s*(\d{2,3})\s*[\/\-]\s*(\d{2,3})", raw_text, re.IGNORECASE)
    if bp_match:
        try:
            sbp = int(bp_match.group(1))
            dbp = int(bp_match.group(2))
            if 70 <= sbp <= 240 and 40 <= dbp <= 140:
                demographics["systolic_bp"] = sbp
                demographics["diastolic_bp"] = dbp
                demographics["bp_string"] = f"{sbp}/{dbp} mmHg"
        except ValueError:
            pass

    return demographics


def extract_biomarkers(raw_text: str, gender: str = "Male") -> Dict[str, Any]:
    """
    Parses lab biomarkers from the text using regular expressions with context matching.
    Calculates status (Normal, High, Low, Critical) based on reference ranges.
    """
    biomarkers = {}

    patterns = {
        "fasting_glucose": [
            r"(?:fasting\s+(?:blood\s+)?(?:glucose|sugar)(?:\s*\([^\)]+\))?|glucose\s*[\-\,]?\s*fasting|fbs)\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)",
            r"(?:plasma\s+glucose\s*-\s*fasting|glucose\s*\(f\))\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "postprandial_glucose": [
            r"(?:post\s*prandial(?:\s+glucose)?(?:\s*\([^\)]+\))?|ppbs|glucose\s*[\-\,]?\s*pp|post\s*meal\s*glucose)\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "hba1c": [
            r"(?:glycated\s+hemoglobin|hba1c|haemoglobin\s*a1c|glycohemoglobin)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "total_cholesterol": [
            r"(?:total\s+cholesterol|cholesterol\s*[\-\,]?\s*total)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "ldl_cholesterol": [
            r"(?:ldl\s+cholesterol|ldl\s*-\s*c|ldl\s+direct|low\s+density\s+lipoprotein)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "hdl_cholesterol": [
            r"(?:hdl\s+cholesterol|hdl\s*-\s*c|high\s+density\s+lipoprotein)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "triglycerides": [
            r"(?:triglycerides|serum\s+triglycerides|tg)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "creatinine": [
            r"(?:serum\s+creatinine|creatinine\s*[\-\,]?\s*serum|creatinine)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "egfr": [
            r"(?:egfr|estimated\s+(?:gfr|glomerular\s+filtration\s+rate)|gfr\s*\(ckd-epi\))(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "bun": [
            r"(?:blood\s+urea\s+nitrogen|bun|serum\s+urea)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "uric_acid": [
            r"(?:uric\s+acid|serum\s+uric\s+acid)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "alt_sgpt": [
            r"(?:alt\s*\([^\)]+\)|sgpt\s*\([^\)]+\)|alanine\s+aminotransferase|sgpt|alt)\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "ast_sgot": [
            r"(?:ast\s*\([^\)]+\)|sgot\s*\([^\)]+\)|aspartate\s+aminotransferase|sgot|ast)\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "bilirubin_total": [
            r"(?:total\s+bilirubin|bilirubin\s*[\-\,]?\s*total)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "hemoglobin": [
            r"(?:hemoglobin|haemoglobin|hb)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "wbc_count": [
            r"(?:total\s+leukocyte\s+count|wbc|total\s+wbc|tlc)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "platelets": [
            r"(?:platelet\s+count|platelets)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "vitamin_d": [
            r"(?:vitamin\s+d3?|25\s*-\s*(?:oh|hydroxy)\s*vitamin\s+d|25-hydroxyvitamin\s+d)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "vitamin_b12": [
            r"(?:vitamin\s+b12|b12|cyanocobalamin)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "serum_ferritin": [
            r"(?:ferritin|serum\s+ferritin)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "tsh": [
            r"(?:tsh|thyroid\s+stimulating\s+hormone|ultra\s+tsh)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "serum_potassium": [
            r"(?:potassium|serum\s+potassium|k\+)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "serum_sodium": [
            r"(?:sodium|serum\s+sodium|na\+)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ],
        "serum_calcium": [
            r"(?:calcium|serum\s+calcium|ca\+\+)(?:\s*\([^\)]+\))?\s*[:\-\s]*([0-9]+(?:\.[0-9]+)?)"
        ]
    }

    # Perform pattern matching
    for key, pattern_list in patterns.items():
        val = None
        for pat in pattern_list:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                try:
                    val = float(match.group(1))
                    break
                except ValueError:
                    continue

        if val is not None:
            # Determine ref key
            ref_key = key
            if key == "hdl_cholesterol":
                ref_key = "hdl_cholesterol_female" if gender == "Female" else "hdl_cholesterol_male"
            elif key == "uric_acid":
                ref_key = "uric_acid_female" if gender == "Female" else "uric_acid_male"
            elif key == "hemoglobin":
                ref_key = "hemoglobin_female" if gender == "Female" else "hemoglobin_male"

            ref_info = STANDARD_REFERENCE_RANGES.get(ref_key, {
                "min": 0, "max": 9999, "unit": "", "name": key.replace("_", " ").title()
            })

            # Check status
            min_val = ref_info.get("min", 0)
            max_val = ref_info.get("max", 9999)
            unit = ref_info.get("unit", "")
            name = ref_info.get("name", key.replace("_", " ").title())

            status = "Normal"
            if val > max_val:
                status = "Critical High" if val > (max_val * 1.5) else "High"
            elif val < min_val:
                status = "Critical Low" if val < (min_val * 0.7) else "Low"

            biomarkers[key] = {
                "name": name,
                "value": val,
                "unit": unit,
                "range": f"{min_val} - {max_val} {unit}",
                "min": min_val,
                "max": max_val,
                "status": status,
                "category": ref_info.get("category", "General Metabolic"),
                "plain_desc": ref_info.get("plain_desc", "Clinical biomarker measuring metabolic health.")
            }

    return biomarkers


def build_health_profile(raw_text: str) -> Dict[str, Any]:
    """
    Main orchestrator for extraction & health profile creation.
    """
    validation = validate_lab_report(raw_text)
    demographics = parse_patient_demographics(raw_text)
    biomarkers = extract_biomarkers(raw_text, gender=demographics.get("gender", "Male"))

    # Synthesize flagged health conditions / clinical indicators
    clinical_flags = []

    # Blood Sugar & HbA1c
    hba1c = biomarkers.get("hba1c", {}).get("value")
    fbs = biomarkers.get("fasting_glucose", {}).get("value")
    if hba1c:
        if hba1c >= 6.5:
            clinical_flags.append({
                "condition": "Type 2 Diabetes Mellitus",
                "severity": "High",
                "marker": f"HbA1c: {hba1c}%",
                "organ": "Blood Sugar / Metabolism",
                "plain_meaning": "Average blood sugar over the last 3 months is in the diabetic range.",
                "action_tip": "Focus on low-glycemic complex carbs, high fiber (>35g/day), and zero sugary beverages."
            })
        elif hba1c >= 5.7:
            clinical_flags.append({
                "condition": "Prediabetes / Impaired Fasting Glucose",
                "severity": "Moderate",
                "marker": f"HbA1c: {hba1c}%",
                "organ": "Blood Sugar / Metabolism",
                "plain_meaning": "Blood sugar is slightly elevated above normal. Fully reversible with dietary and lifestyle adjustments.",
                "action_tip": "Replace refined carbs with steel-cut oats, quinoa, lentils, and daily light physical activity."
            })
    elif fbs:
        if fbs >= 126:
            clinical_flags.append({
                "condition": "Hyperglycemia / Diabetes Suspect",
                "severity": "High",
                "marker": f"FBS: {fbs} mg/dL",
                "organ": "Blood Sugar / Metabolism",
                "plain_meaning": "Fasting blood sugar is higher than standard clinical thresholds.",
                "action_tip": "Adopt low-glycemic, fiber-rich meals and consult physician for confirmatory HbA1c test."
            })
        elif fbs >= 100:
            clinical_flags.append({
                "condition": "Impaired Fasting Glucose",
                "severity": "Moderate",
                "marker": f"FBS: {fbs} mg/dL",
                "organ": "Blood Sugar / Metabolism",
                "plain_meaning": "Fasting glucose is in the prediabetes warning zone.",
                "action_tip": "Avoid late-night heavy snacking and minimize refined carbohydrates and sweet drinks."
            })

    # Lipids & Cardiovascular
    chol = biomarkers.get("total_cholesterol", {}).get("value")
    ldl = biomarkers.get("ldl_cholesterol", {}).get("value")
    tg = biomarkers.get("triglycerides", {}).get("value")
    hdl = biomarkers.get("hdl_cholesterol", {}).get("value")

    if (chol and chol > 200) or (ldl and ldl > 100) or (tg and tg > 150):
        flag_details = []
        if chol and chol > 200: flag_details.append(f"Chol: {chol}")
        if ldl and ldl > 100: flag_details.append(f"LDL: {ldl}")
        if tg and tg > 150: flag_details.append(f"TG: {tg}")
        clinical_flags.append({
            "condition": "Dyslipidemia / Elevated Cholesterol",
            "severity": "Moderate",
            "marker": ", ".join(flag_details),
            "organ": "Heart & Arteries",
            "plain_meaning": "Elevated circulating bad fats (LDL/Triglycerides) that can stress cardiovascular vessels over time.",
            "action_tip": "Switch from saturated/fried fats to extra virgin olive oil, walnuts, chia seeds, and wild fish."
        })

    # Renal
    creatinine = biomarkers.get("creatinine", {}).get("value")
    egfr = biomarkers.get("egfr", {}).get("value")
    if (creatinine and creatinine > 1.2) or (egfr and egfr < 60):
        clinical_flags.append({
            "condition": "Renal Impairment / CKD Risk",
            "severity": "High" if (egfr and egfr < 45) else "Moderate",
            "marker": f"Creatinine: {creatinine}, eGFR: {egfr}",
            "organ": "Kidneys & Filtration",
            "plain_meaning": "Kidney filtering rate is slightly reduced or serum waste levels are elevated.",
            "action_tip": "Moderate daily protein to ~0.8g/kg, limit high-sodium foods, and maintain clean hydration."
        })

    # Uric Acid / Gout
    uric_acid = biomarkers.get("uric_acid", {}).get("value")
    if uric_acid and uric_acid > 7.0:
        clinical_flags.append({
            "condition": "Hyperuricemia (Uric Acid & Gout Risk)",
            "severity": "Moderate",
            "marker": f"Uric Acid: {uric_acid} mg/dL",
            "organ": "Uric Acid & Joints",
            "plain_meaning": "High uric acid in blood; can crystallize in joints (gout) or form kidney stones if unmanaged.",
            "action_tip": "Drink at least 3.0L water daily, avoid beer/spirits and high-purine organ meats, enjoy tart cherries."
        })

    # Liver
    alt = biomarkers.get("alt_sgpt", {}).get("value")
    ast = biomarkers.get("ast_sgot", {}).get("value")
    if (alt and alt > 56) or (ast and ast > 40):
        severity = "High" if (alt and alt > 100) else "Moderate"
        clinical_flags.append({
            "condition": "Elevated Liver Enzymes (Hepatic Stress / NAFLD)",
            "severity": severity,
            "marker": f"ALT: {alt}, AST: {ast}",
            "organ": "Liver Function",
            "plain_meaning": "Liver cells are experiencing mild metabolic stress or inflammation (common in fatty liver).",
            "action_tip": "Eliminate alcohol and high-fructose syrups; add cruciferous greens (broccoli), green tea, and turmeric."
        })

    # Thyroid (TSH)
    tsh = biomarkers.get("tsh", {}).get("value")
    if tsh and tsh > 4.5:
        clinical_flags.append({
            "condition": "Elevated TSH (Sluggish Thyroid / Hypothyroidism)",
            "severity": "Mild" if tsh < 8.0 else "Moderate",
            "marker": f"TSH: {tsh} µIU/mL",
            "organ": "Thyroid & Metabolism",
            "plain_meaning": "Pituitary gland is working harder to stimulate a sluggish thyroid gland.",
            "action_tip": "Eat 1-2 Brazil nuts daily for selenium, ensure adequate zinc/iodine, and cook cruciferous veggies thoroughly."
        })
    elif tsh and tsh < 0.4:
        clinical_flags.append({
            "condition": "Low TSH (Overactive Thyroid Risk)",
            "severity": "Moderate",
            "marker": f"TSH: {tsh} µIU/mL",
            "organ": "Thyroid & Metabolism",
            "plain_meaning": "Thyroid hormone levels may be elevated, speeding up metabolic processes.",
            "action_tip": "Consult physician for free T3/T4 testing and monitor caffeine intake."
        })

    # Electrolytes (Potassium)
    k_val = biomarkers.get("serum_potassium", {}).get("value")
    if k_val and k_val < 3.5:
        clinical_flags.append({
            "condition": "Hypokalemia (Low Potassium)",
            "severity": "Mild" if k_val >= 3.0 else "High",
            "marker": f"K+: {k_val} mEq/L",
            "organ": "Electrolytes & Heart Rhythm",
            "plain_meaning": "Low blood potassium, which can cause muscle cramps, weakness, or irregular heartbeats.",
            "action_tip": "Incorporate potassium-rich tender coconut water, baked sweet potato, spinach, and avocado."
        })
    elif k_val and k_val > 5.0:
        clinical_flags.append({
            "condition": "Hyperkalemia (High Potassium)",
            "severity": "High",
            "marker": f"K+: {k_val} mEq/L",
            "organ": "Electrolytes & Heart Rhythm",
            "plain_meaning": "High potassium in blood; requires dietary care if kidneys are filtering slowly.",
            "action_tip": "Moderate high-potassium supplements and follow renal dietitian guidance."
        })

    # Blood Pressure
    sbp = demographics.get("systolic_bp")
    dbp = demographics.get("diastolic_bp")
    if sbp and dbp:
        if sbp >= 140 or dbp >= 90:
            clinical_flags.append({
                "condition": "Stage 2 Hypertension",
                "severity": "High",
                "marker": f"{sbp}/{dbp} mmHg",
                "organ": "Blood Pressure & Vessels",
                "plain_meaning": "Blood pressure is significantly elevated, putting excess strain on heart and arteries.",
                "action_tip": "Strict DASH protocol: limit sodium <1800mg/day, boost potassium/magnesium, and reduce stress."
            })
        elif sbp >= 130 or dbp >= 80:
            clinical_flags.append({
                "condition": "Stage 1 Hypertension",
                "severity": "Moderate",
                "marker": f"{sbp}/{dbp} mmHg",
                "organ": "Blood Pressure & Vessels",
                "plain_meaning": "Blood pressure is in the mild high range; very responsive to sodium moderation and diet.",
                "action_tip": "Reduce processed/packaged salty foods, use fresh herbs/lemon for seasoning, eat leafy greens."
            })

    # Vitamins
    vit_d = biomarkers.get("vitamin_d", {}).get("value")
    if vit_d and vit_d < 30:
        clinical_flags.append({
            "condition": "Vitamin D Deficiency",
            "severity": "Mild" if vit_d >= 20 else "Moderate",
            "marker": f"Vit D: {vit_d} ng/mL",
            "organ": "Immunity & Bone Health",
            "plain_meaning": "Low circulating Vitamin D, affecting bone density, immune strength, and insulin signaling.",
            "action_tip": "Get 15-20 min gentle morning sunlight, consume fortified foods/egg yolks, and discuss D3 supplementation."
        })

    vit_b12 = biomarkers.get("vitamin_b12", {}).get("value")
    if vit_b12 and vit_b12 < 200:
        clinical_flags.append({
            "condition": "Vitamin B12 Deficiency",
            "severity": "Moderate",
            "marker": f"B12: {vit_b12} pg/mL",
            "organ": "Nerve & Energy Vitality",
            "plain_meaning": "Low B12 stores can lead to fatigue, brain fog, and low red blood cell production.",
            "action_tip": "Consume fortified nutritional yeast, dairy/eggs/lean meats, or discuss sublingual B12 with your doctor."
        })

    return {
        "validation": validation,
        "demographics": demographics,
        "biomarkers": biomarkers,
        "clinical_flags": clinical_flags,
        "raw_text_length": len(raw_text),
        "raw_text_preview": raw_text[:800] + ("..." if len(raw_text) > 800 else "")
    }
