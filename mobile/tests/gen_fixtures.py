"""Runs the ORIGINAL Python engine over a rich case set and dumps tests/fixtures.json.

Usage: python3 tests/gen_fixtures.py   (from the mobile/ directory)
"""
import ast
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # NutriAgent-AI/
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import extractor            # noqa: E402
import deterministic_nutrition as dn   # noqa: E402
import indian_foods         # noqa: E402
import general_intake       # noqa: E402


def sample_text_from_app():
    tree = ast.parse(open(os.path.join(ROOT, "app.py"), encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SAMPLE_LAB_REPORT_TEXT":
            return ast.literal_eval(node.value)
    raise SystemExit("SAMPLE_LAB_REPORT_TEXT not found")


def lab(header, rows):
    return header + "\n" + "\n".join(rows) + "\n"


HDR_M = ("CITY DIAGNOSTICS LAB\nPatient Name: Mr. Ravi Kumar\nAge: 54 Years | Sex: Male\n"
         "Height: 172 cm | Weight: 90 kg\nBlood Pressure: 126/82 mmHg\nSpecimen: Blood, reference ranges apply\n")
HDR_F = ("CITY DIAGNOSTICS LAB\nPatient Name: Ms. Anita Rao\nAge: 47 Years | Sex: Female\n"
         "Height: 160 cm | Weight: 71 kg\nBP: 120/78 mmHg\nSpecimen: Blood, reference ranges apply\n")

LAB_TEXTS = {
    "t2dm_female": lab(HDR_F, ["HbA1c 7.2 %", "Fasting Blood Glucose (FBS) 150 mg/dL", "HDL Cholesterol 45 mg/dL",
                               "Serum Uric Acid 5.2 mg/dL", "Hemoglobin 11.4 g/dL", "Total Cholesterol 190 mg/dL"]),
    "prediabetes_hba1c": lab(HDR_M, ["HbA1c (Glycated Hemoglobin) 6.1 %", "Fasting Blood Glucose 104 mg/dL",
                                     "Triglycerides 160 mg/dL", "LDL Cholesterol 120 mg/dL", "Total Cholesterol 215 mg/dL"]),
    "fbs_only_high": lab(HDR_M, ["Fasting Blood Sugar: 131", "Postprandial Glucose: 190", "Creatinine 0.9"]),
    "fbs_only_borderline": lab(HDR_F, ["Fasting Blood Sugar: 108", "Vitamin B12 450 pg/mL"]),
    "renal": lab(HDR_M, ["Serum Creatinine 1.8 mg/dL", "Estimated GFR (CKD-EPI) 40 mL/min", "Blood Urea Nitrogen 32 mg/dL",
                         "Serum Potassium (K+) 5.4 mEq/L", "Serum Sodium (Na+) 138 mEq/L"]),
    "renal_mild": lab(HDR_M, ["Serum Creatinine 1.0", "eGFR 55"]),
    "gout": lab(HDR_M, ["Serum Uric Acid 9.1 mg/dL", "Creatinine 1.0 mg/dL", "ALT (SGPT) 30 U/L"]),
    "liver_high": lab(HDR_M, ["ALT (SGPT) 120 U/L", "AST (SGOT) 85 U/L", "Total Bilirubin 1.0 mg/dL", "Triglycerides 210 mg/dL"]),
    "liver_mild": lab(HDR_F, ["ALT 60", "AST 35"]),
    "tsh_high": lab(HDR_F, ["TSH 9.2 uIU/mL", "Vitamin D 18 ng/mL"]),
    "tsh_mid": lab(HDR_F, ["TSH 5.0", "Hemoglobin 12.8"]),
    "tsh_low": lab(HDR_M, ["TSH 0.2 uIU/mL", "Serum Calcium 9.4"]),
    "k_low": lab(HDR_M, ["Serum Potassium 3.1 mEq/L", "Serum Sodium 140"]),
    "k_mild_low": lab(HDR_M, ["Potassium 3.3"]),
    "bp_stage2": lab("Patient Name: Mr. Raj Singh\nAge: 61 Years | Sex: Male\nBlood Pressure: 150/95 mmHg\nweight 82 kg\nheight 168 cm\nSpecimen blood lab report\n",
                     ["Fasting Blood Glucose 95", "Triglycerides 140"]),
    "bp_stage1": lab("Patient Name: Mr. Sam Lee\nAge: 39 Years | Sex: Male\nBP: 132/84\nSpecimen blood lab report patient\n",
                     ["Total Cholesterol 180", "HDL Cholesterol 55"]),
    "vit_low": lab(HDR_F, ["Vitamin D (25-Hydroxy) 12.0 ng/mL", "Vitamin B12 150 pg/mL", "Serum Ferritin 12 ng/mL"]),
    "normal_all": lab(HDR_M, ["HbA1c 5.2 %", "Fasting Blood Glucose 88 mg/dL", "Total Cholesterol 170 mg/dL",
                              "Triglycerides 100 mg/dL", "HDL Cholesterol 55 mg/dL", "LDL Cholesterol 90 mg/dL",
                              "Serum Creatinine 0.9 mg/dL", "Estimated GFR 105 mL/min", "Serum Uric Acid 5.0 mg/dL",
                              "ALT (SGPT) 25 U/L", "AST (SGOT) 22 U/L", "Vitamin D 45 ng/mL", "Vitamin B12 500 pg/mL"]),
    "combo_everything": lab("Patient Name: Mr. Big Case\nAge / Sex: 63 Yrs / Male\nHeight / Weight: 168 cm / 98 kg\nBlood Pressure: 148/94 mmHg\nSpecimen blood lab report\n",
                            ["HbA1c 8.1 %", "Fasting Blood Glucose 162 mg/dL", "Total Cholesterol 260 mg/dL", "LDL Cholesterol 170 mg/dL",
                             "Triglycerides 280 mg/dL", "HDL Cholesterol 32 mg/dL", "Serum Creatinine 1.7 mg/dL",
                             "Estimated GFR 44 mL/min", "Serum Uric Acid 8.8 mg/dL", "ALT (SGPT) 105 U/L", "AST (SGOT) 70 U/L",
                             "TSH 6.1", "Serum Potassium 3.2", "Vitamin D 15", "Vitamin B12 180"]),
    "meters_height": lab("Patient Name: Dr. Eva\nAge / Sex: 34 Yrs / Female\nHeight / Weight: 1.65 m / 58 kg\nBMI: 21.3\nSpecimen blood lab\n",
                         ["Hemoglobin 10.2 g/dL", "WBC 6.5", "Platelet Count 220"]),
    "wt_ht_separate": lab("Name: Tom\nAge: 29\nGender: M\nWt: 65 kg\nHt: 1.80 m\nBMI: 20.1\nSpecimen blood lab\n",
                          ["Fasting Glucose 90", "Total Cholesterol 150"]),
    "age_alt": "Report for patient 58 Years Old female. Blood lab specimen reference.\nTotal Cholesterol 205 mg/dL\nLDL Cholesterol 130\n",
    "minimal": "hello world",
    "empty": "",
    "no_markers": "This is a long document about gardening and tomatoes and weather forecasts for the coming week in the north.\n" * 2,
}

VARIANTS = [
    {"name": "Patient", "age": 50, "gender": "Male", "weight_kg": 80.0, "height_cm": 175.0, "bmi": 26.1,
     "bp_string": "120/80 mmHg", "dietary_preference": "Omnivore / Standard", "allergies": [], "activity_level": "Light"},
    {"name": "Asha", "age": 41, "gender": "Female", "weight_kg": 62.5, "height_cm": 158.0, "bmi": 25.0,
     "bp_string": "118/76 mmHg", "dietary_preference": "Vegetarian", "allergies": ["peanut", "milk"], "activity_level": "Moderate"},
    {"name": "Kiran", "age": 68, "gender": "Other", "weight_kg": 95.5, "height_cm": 170.0, "bmi": 33.0,
     "bp_string": "140/90 mmHg", "dietary_preference": "Vegan", "allergies": ["wheat", "soy"], "activity_level": "Sedentary"},
    {"name": "Meera", "age": 30, "gender": "Female", "weight_kg": 45.0, "height_cm": 165.0, "bmi": 16.5,
     "bp_string": "110/70 mmHg", "dietary_preference": "Low-Carb / Mediterranean", "allergies": ["shellfish", "egg"], "activity_level": "Active"},
    {"name": "Dev", "age": 55, "gender": "Male", "weight_kg": 72.0, "height_cm": 172.0, "bmi": None,
     "bp_string": "130/85 mmHg", "dietary_preference": "Vegetarian", "allergies": "groundnut, tree nuts", "activity_level": "Light"},
]

QUERIES = [
    "Calculate my BMI: height 175cm, weight 86.5kg, age 52",
    "I have prediabetes and high cholesterol, what should I eat?",
    "I have gout and kidney issues, what foods are safe?",
    "What is a healthy breakfast for someone with high blood pressure?",
    "I have type 2 diabetes and fatty liver. I am a 45 year old woman, 160 cm, 70 kg, vegetarian",
    "he is 60 years old, 5.9 m tall? weighs 190 lbs and has hypertension",
    "I am 34, weight 62kg, height 1.62 m, vegan, I exercise daily, thyroid problem",
    "Diabetic non-veg man 50 years old 170 cm 95 kg with kidney disease and gout",
    "She is an athlete 28 yo 168cm 55kg wants a plan, low vitamin d",
    "What should I eat?",
    "",
    "hello",
    "vitamin b12 deficiency vegetarian",
    "high uric acid, high bp, high cholesterol and diabetes",
    "I am 70 years old with ckd, creatinine high, eating eggs and chicken",
    "borderline sugar, impaired fasting glucose, 38 yrs, 80 kg, 178 cm",
    "pre-diabetic woman 33 years old 150 cm 49 kg moderate activity",
    "nafld and high triglycerides, I am 41 years old, male, 182cm, 101kg, heavy work",
    "hypothyroid female 52 years old 155cm 80kg",
    "I weigh 154 pounds, 180 cm tall, 29 years old, mutton lover, high ldl",
    "man, sgpt high, sgot high, hepatic",
    "Can I eat rice with diabetes? 65 y/o",
    "I'm aged 44 and have high bp is high",
    "kidney stones and purine rich diet help me, 175cm 70kg 30 yo male fish eater",
    "diabetes, hypertension, dyslipidemia, renal, gout, liver, thyroid, vitamin d, b12 all together",
    "BMI check: 160 cm 40 kg 20 years",
    "2m tall 100kg 40 year",
    "Vegetarian with type 2 diabetes wanting weight loss, 55 years old, 168 cm, 88 kg",
]


class Stub:
    def __init__(self):
        self.prompt = None
        self.system = None

    def generate(self, prompt, system_prompt="", temperature=0.3):
        self.prompt, self.system = prompt, system_prompt
        return ""


def main():
    out = {"lab_cases": [], "general": [], "fuzz": []}

    texts = dict(LAB_TEXTS)
    texts["app_sample_text"] = sample_text_from_app()
    pdf_path = os.path.join(ROOT, "sample_blood_test_report.pdf")
    with open(pdf_path, "rb") as fh:
        pdf_text, _ = extractor.extract_text_from_pdf(fh)
    texts["sample_pdf_text"] = pdf_text

    for cid, text in texts.items():
        profile = extractor.build_health_profile(text)
        variants = []
        for ov in VARIANTS:
            p = json.loads(json.dumps(profile))
            p["demographics"].update(ov)
            proto = dn.compute_clinical_nutrition_protocol(p)
            variants.append({"overrides": ov, "profile": p, "protocol": proto,
                             "nin_block": indian_foods.build_nin_reference_block(p, proto)})
        # also the "no overrides" path (raw extracted demographics)
        raw_proto = dn.compute_clinical_nutrition_protocol(profile)
        out["lab_cases"].append({"id": cid, "text": text, "profile": profile,
                                 "raw_protocol": raw_proto, "variants": variants})

    for q in QUERIES:
        stub = Stub()
        res = general_intake.run_nutriagent_general(q, stub)
        nin = indian_foods.build_nin_reference_block(res["profile"], res["protocol"])
        out["general"].append({
            "query": q, "profile": res["profile"], "protocol": res["protocol"], "audit": res["audit"],
            "comparison_rows": res["comparison_rows"], "assumptions": res["assumptions"],
            "nin_block": nin, "prompt": stub.prompt, "system": stub.system,
        })

    rnd = random.Random(20260101)
    acts = ["Sedentary", "Light", "Moderate", "Active", "very_active", "light", None, "weird"]
    for _ in range(300):
        demo = {}
        if rnd.random() < 0.95:
            demo["age"] = rnd.choice([rnd.randint(1, 100), None, 0])
        g = rnd.choice(["Male", "Female", "male", "FEMALE", "Other", None, "Unknown"])
        demo["gender"] = g
        demo["weight_kg"] = rnd.choice([None, round(rnd.uniform(35, 160), 1), float(rnd.randint(40, 140)),
                                        rnd.randint(40, 140) + 0.5])
        demo["height_cm"] = rnd.choice([None, round(rnd.uniform(130, 205), 1), float(rnd.randint(140, 200))])
        demo["bmi"] = rnd.choice([None, 0, round(rnd.uniform(15, 40), 1)])
        act = rnd.choice(acts)
        res = dn.calculate_bmr_tdee(demo, act) if act is not None else dn.calculate_bmr_tdee(demo, None)
        out["fuzz"].append({"demo": demo, "activity": act, "out": res})

    path = os.path.join(HERE, "fixtures.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("wrote %s: %d lab cases x %d variants, %d general, %d fuzz" % (
        path, len(out["lab_cases"]), len(VARIANTS), len(out["general"]), len(out["fuzz"])))


if __name__ == "__main__":
    main()
