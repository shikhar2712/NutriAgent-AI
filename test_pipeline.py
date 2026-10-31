"""
test_pipeline.py - Comprehensive Unit & End-to-End Test Suite for NutriAgent AI
Verifies PDF extraction, biomarker parsing, deterministic calculations,
and agent execution (both live Ollama and offline fallbacks).
"""

import sys
import unittest
from extractor import (
    parse_patient_demographics,
    extract_biomarkers,
    build_health_profile,
    validate_lab_report,
    STANDARD_REFERENCE_RANGES
)
from deterministic_nutrition import (
    calculate_bmr_tdee,
    compute_clinical_nutrition_protocol
)
from agents import (
    OllamaClient,
    AnalysisAgent,
    NutritionAgent,
    EvaluationAgent,
    ConsultantAgent,
    SingleLLMBaseline
)

# Realistic sample text matching Robert Vance test case
SAMPLE_RAW_TEXT = """
METROPOLITAN CLINICAL DIAGNOSTICS & PATHOLOGY LABORATORY
Patient Name: Mr. Robert Vance
Age: 52 Years | Sex: Male
Height: 175 cm | Weight: 86.5 kg | Calculated BMI: 28.2 kg/m2
Blood Pressure: 138/88 mmHg

Fasting Blood Glucose: 118.0 mg/dL
Postprandial Glucose: 165.0 mg/dL
HbA1c: 6.4 %
Total Cholesterol: 232.0 mg/dL
Triglycerides: 198.0 mg/dL
HDL Cholesterol: 38.0 mg/dL
LDL Cholesterol: 154.0 mg/dL
Serum Creatinine: 1.15 mg/dL
eGFR: 78.0 mL/min
Blood Urea Nitrogen: 18.0 mg/dL
Serum Uric Acid: 7.8 mg/dL
ALT: 48.0 U/L
AST: 36.0 U/L
Total Bilirubin: 0.85 mg/dL
Vitamin D: 19.4 ng/mL
Vitamin B12: 310.0 pg/mL
Serum Potassium: 4.4 mEq/L
Serum Sodium: 141.0 mEq/L
"""

class TestExtractor(unittest.TestCase):
    def test_validation(self):
        val = validate_lab_report(SAMPLE_RAW_TEXT)
        self.assertTrue(val["valid"])
        self.assertGreater(val["confidence"], 0.5)
        self.assertIn("Lipid Panel", val["detected_sections"])

    def test_demographics_parsing(self):
        demo = parse_patient_demographics(SAMPLE_RAW_TEXT)
        self.assertEqual(demo["name"], "Robert Vance")
        self.assertEqual(demo["age"], 52)
        self.assertEqual(demo["gender"], "Male")
        self.assertEqual(demo["weight_kg"], 86.5)
        self.assertEqual(demo["height_cm"], 175.0)
        self.assertEqual(demo["bmi"], 28.2)
        self.assertEqual(demo["systolic_bp"], 138)
        self.assertEqual(demo["diastolic_bp"], 88)

    def test_biomarker_extraction(self):
        biomarkers = extract_biomarkers(SAMPLE_RAW_TEXT, gender="Male")
        self.assertIn("hba1c", biomarkers)
        self.assertEqual(biomarkers["hba1c"]["value"], 6.4)
        self.assertEqual(biomarkers["hba1c"]["status"], "High")

        self.assertIn("ldl_cholesterol", biomarkers)
        self.assertEqual(biomarkers["ldl_cholesterol"]["value"], 154.0)
        self.assertEqual(biomarkers["ldl_cholesterol"]["status"], "Critical High")

        self.assertIn("uric_acid", biomarkers)
        self.assertEqual(biomarkers["uric_acid"]["value"], 7.8)
        self.assertEqual(biomarkers["uric_acid"]["status"], "High")

    def test_health_profile_synthesis(self):
        profile = build_health_profile(SAMPLE_RAW_TEXT)
        flags = [f["condition"] for f in profile["clinical_flags"]]
        self.assertTrue(any("Prediabetes" in f for f in flags))
        self.assertTrue(any("Dyslipidemia" in f for f in flags))
        self.assertTrue(any("Hypertension" in f for f in flags))
        self.assertTrue(any("Hyperuricemia" in f for f in flags))


class TestDeterministicNutrition(unittest.TestCase):
    def test_bmr_tdee_calculation(self):
        demo = {"age": 52, "gender": "Male", "weight_kg": 86.5, "height_cm": 175.0, "bmi": 28.2}
        energy = calculate_bmr_tdee(demo, activity_level="light")
        # BMR = (10*86.5) + (6.25*175) - (5*52) + 5 = 865 + 1093.75 - 260 + 5 = 1703.75 -> 1704
        self.assertAlmostEqual(energy["bmr"], 1704, delta=2)
        # TDEE = 1704 * 1.375 = 2343
        self.assertAlmostEqual(energy["tdee"], 2343, delta=5)
        # Target = TDEE - 300 (overweight deficit) = 2043
        self.assertAlmostEqual(energy["target_calories"], 2043, delta=5)

    def test_protocol_stacking(self):
        profile = build_health_profile(SAMPLE_RAW_TEXT)
        protocol = compute_clinical_nutrition_protocol(profile)

        protocols = protocol["protocols"]
        self.assertTrue(any("Low Glycemic Index" in p for p in protocols))
        self.assertTrue(any("Mediterranean" in p for p in protocols))
        self.assertTrue(any("DASH" in p for p in protocols))
        self.assertTrue(any("Low-Purine" in p for p in protocols))

        # Check macro restrictions
        macros = protocol["macros"]
        self.assertEqual(macros["carbs"]["percentage"], 40)
        self.assertEqual(macros["protein"]["percentage"], 25)
        self.assertEqual(macros["fat"]["percentage"], 35)

        # Check sodium cap for hypertensive
        micros = protocol["micronutrient_targets"]
        self.assertEqual(micros["sodium_max_mg"], 1800)
        self.assertEqual(micros["water_intake_liters"], 3.0)


class TestAgentsPipeline(unittest.TestCase):
    def setUp(self):
        self.client = OllamaClient(base_url="http://localhost:11434", model="qwen2.5:7b")
        self.profile = build_health_profile(SAMPLE_RAW_TEXT)
        self.protocol = compute_clinical_nutrition_protocol(self.profile)

    def test_offline_fallback_execution(self):
        """Ensures all agents gracefully return structured clinical text even if Ollama is down."""
        # 1. Analysis Agent
        agent1 = AnalysisAgent(self.client)
        out1 = agent1.run(self.profile)
        self.assertIn("analysis_report", out1)
        self.assertGreater(len(out1["analysis_report"]), 100)

        # 2. Nutrition Agent
        agent2 = NutritionAgent(self.client)
        out2 = agent2.run(self.profile, out1, self.protocol)
        self.assertIn("diet_plan", out2)
        self.assertGreater(len(out2["diet_plan"]), 100)

        # 3. Evaluation Agent (Audit Gate)
        agent3 = EvaluationAgent(self.client)
        out3 = agent3.run(self.profile, out1, out2, self.protocol)
        self.assertIn("safety_score", out3)
        self.assertGreaterEqual(out3["safety_score"], 80)
        self.assertEqual(out3["audit_verdict"], "PASSED - Clinically Validated")

        # 4. Consultant Agent
        agent4 = ConsultantAgent(self.client)
        results = {
            "health_profile": self.profile,
            "nutrition_protocol": self.protocol,
            "analysis_output": out1,
            "diet_output": out2,
            "evaluation_output": out3
        }
        ans = agent4.answer_question("Can I eat watermelon?", [], results)
        self.assertGreater(len(ans), 50)


if __name__ == "__main__":
    unittest.main()
