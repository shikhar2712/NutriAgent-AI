"""
deterministic_nutrition.py - Rule-Based Clinical Nutrition Engine
Computes caloric requirements, macronutrient distributions, micronutrient thresholds,
and clinical dietary constraints based on extracted patient biomarkers and demographics.
"""

from typing import Dict, Any, List


def calculate_bmr_tdee(demographics: Dict[str, Any], activity_level: str = "light") -> Dict[str, Any]:
    """
    Computes Basal Metabolic Rate (BMR) using the Mifflin-St Jeor equation and Total Daily Energy Expenditure (TDEE).
    Gracefully handles missing demographic values with standard clinical baselines.
    """
    age = float(demographics.get("age") or 45)
    gender = str(demographics.get("gender") or "Male").capitalize()

    # Safe fallback for weight and height if missing in PDF
    weight_kg = demographics.get("weight_kg")
    if weight_kg is None:
        weight_kg = 72.0 if gender == "Male" else 60.0
    else:
        weight_kg = float(weight_kg)

    height_cm = demographics.get("height_cm")
    if height_cm is None:
        height_cm = 172.0 if gender == "Male" else 160.0
    else:
        height_cm = float(height_cm)

    # Activity multiplier
    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    mult = multipliers.get(str(activity_level).lower(), 1.375)

    # Mifflin-St Jeor formula
    if gender.lower() == "female":
        bmr = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) - 161.0
    else:
        bmr = (10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age) + 5.0

    tdee = bmr * mult
    bmi = demographics.get("bmi")
    if not bmi and weight_kg and height_cm:
        bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)

    # Caloric target recommendation
    caloric_adjustment = 0
    goal = "Weight Maintenance & Metabolic Optimization"
    if bmi:
        if bmi >= 30.0:
            caloric_adjustment = -500
            goal = "Gradual Caloric Deficit (Weight Loss & Insulin Sensitivity)"
        elif bmi >= 25.0:
            caloric_adjustment = -300
            goal = "Mild Deficit (Metabolic Health & Weight Normalization)"
        elif bmi < 18.5:
            caloric_adjustment = +300
            goal = "Caloric Surplus (Nourishment & Lean Mass Gain)"

    target_calories = max(1300, round(tdee + caloric_adjustment))

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": target_calories,
        "bmi": bmi,
        "goal": goal,
        "activity_level": activity_level,
        "calculated_weight_kg": weight_kg,
        "calculated_height_cm": height_cm
    }


def compute_clinical_nutrition_protocol(health_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates biomarkers and applies clinical dietary protocols (DASH, Mediterranean, Low-GI, Renal, Low-Purine).
    Returns macro splits, micronutrient targets, clinical constraints, allowed/restricted foods.
    """
    demographics = health_profile.get("demographics", {})
    biomarkers = health_profile.get("biomarkers", {})
    clinical_flags = health_profile.get("clinical_flags", [])

    # Step 1: Baseline energy
    energy = calculate_bmr_tdee(demographics, activity_level=demographics.get("activity_level", "light"))
    target_kcal = energy["target_calories"]
    weight_kg = energy.get("calculated_weight_kg", 70.0)

    # Step 2: Clinical condition flags
    is_diabetic = any("Diabetes" in f["condition"] or "Glucose" in f["condition"] for f in clinical_flags)
    is_dyslipidemic = any("Dyslipidemia" in f["condition"] or "Hypercholesterolemia" in f["condition"] for f in clinical_flags)
    is_hypertensive = any("Hypertension" in f["condition"] for f in clinical_flags)
    is_hyperuricemic = any("Hyperuricemia" in f["condition"] or "Gout" in f["condition"] for f in clinical_flags)
    is_renal_risk = any("Renal" in f["condition"] or "CKD" in f["condition"] for f in clinical_flags)
    is_liver_risk = any("Transaminases" in f["condition"] or "Liver" in f["condition"] or "Hepatic" in f["condition"] for f in clinical_flags)
    is_hypokalemic = any("Hypokalemia" in f["condition"] or "Potassium" in f["condition"] for f in clinical_flags)
    is_hypothyroid = any("TSH" in f["condition"] or "Hypothyroidism" in f["condition"] for f in clinical_flags)
    vit_d_low = any("Vitamin D" in f["condition"] for f in clinical_flags)
    vit_b12_low = any("Vitamin B12" in f["condition"] for f in clinical_flags)

    # Step 3: Macronutrient ratios
    # Baseline defaults
    carb_pct = 50
    protein_pct = 20
    fat_pct = 30

    protocols = ["Balanced Whole-Foods Protocol"]
    constraints = []
    strictly_avoid = []
    strongly_recommend = []

    # Diabetic / Insulin resistance adjustments
    if is_diabetic:
        protocols.append("Low Glycemic Index (Low-GI) / Insulin Sensitizing Protocol")
        carb_pct = 40
        protein_pct = 25
        fat_pct = 35
        constraints.append("Max Net Carbs: 150-180g/day; Glycemic Load per meal < 15.")
        constraints.append("Dietary Fiber target: >= 35g/day with high soluble fiber (beta-glucan, psyllium, legumes).")
        strictly_avoid.extend(["Refined sugars & sweetened beverages", "White bread, white rice, refined pastries", "Fruit juices & high-fructose corn syrups"])
        strongly_recommend.extend(["Steel-cut oats, quinoa, barley", "Non-starchy cruciferous vegetables", "Chia seeds, flaxseeds, cinnamon", "Legumes with complex resistant starches"])

    # Dyslipidemia / Heart health adjustments
    if is_dyslipidemic:
        protocols.append("Cardioprotective Mediterranean / Lipid-Lowering Protocol")
        fat_pct = max(fat_pct, 30)
        constraints.append("Saturated Fatty Acids (SFA): < 7% of total daily calories (~12-15g max).")
        constraints.append("Zero trans-fats; prioritize Monounsaturated (MUFA) and Omega-3 Polyunsaturated Fats (PUFA).")
        constraints.append("Dietary soluble fiber: >= 30g/day to bind intestinal bile acids.")
        strictly_avoid.extend(["Deep fried foods, palm oil, hydrogenated fats", "Processed meats (sausages, bacon, hot dogs)", "High-fat dairy & commercial baked goods"])
        strongly_recommend.extend(["Extra virgin olive oil (cold-pressed)", "Wild-caught fatty fish (salmon, sardines, mackerel) or algal EPA/DHA", "Walnuts and raw almonds", "Avocado & psyllium husk"])

    # Hypertension adjustments (DASH Protocol)
    if is_hypertensive:
        protocols.append("DASH (Dietary Approaches to Stop Hypertension) Protocol")
        constraints.append("Sodium restriction: < 1500 - 2000 mg/day (equivalent to ~1 level tsp salt).")
        constraints.append("Potassium-to-Sodium ratio target >= 3:1 (ensure potassium rich foods if kidney function normal).")
        constraints.append("Magnesium target: >= 400 mg/day.")
        strictly_avoid.extend(["Canned soups, packaged noodles, salty snacks, pickles", "Monosodium glutamate (MSG) & soy sauce in high amounts", "Processed cured meats"])
        strongly_recommend.extend(["Dark leafy greens (spinach, kale, Swiss chard)", "Pomegranate, beetroot (rich in nitric oxide donors)", "Pumpkin seeds, unsalted almonds", "Potassium-rich foods (sweet potato, coconut water)"])

    # Renal / CKD adjustments
    if is_renal_risk:
        protocols.append("Renal Protective Protocol (Stage-Specific)")
        # Moderate protein intake to reduce glomerular hyperfiltration
        protein_g_per_kg = 0.8
        target_protein_g = round(weight_kg * protein_g_per_kg)
        constraints.append(f"Protein moderation: ~{target_protein_g}g/day (0.8g/kg body weight) to ease glomerular workload.")
        constraints.append("Sodium restriction: < 2000 mg/day.")
        constraints.append("Serum potassium & phosphorus monitoring (moderate high-potassium/phosphorus additives if prescribed).")
        strictly_avoid.extend(["Inorganic phosphate food additives (E-numbers in processed snacks)", "Excessive protein powders / high-dose creatine", "High-sodium processed meals"])
        strongly_recommend.extend(["Controlled portions of high biological value protein (egg whites, poultry, tofu)", "Adequate clean hydration (2.5L/day unless fluid restricted)"])

    # Hyperuricemia / Gout adjustments
    if is_hyperuricemic:
        protocols.append("Low-Purine / Alkaline Uric Acid Control Protocol")
        constraints.append("Strict restriction of high-purine foods (< 100mg purines/day).")
        constraints.append("Eliminate high-fructose corn syrup & alcohol (especially beer).")
        constraints.append("Hydration target: >= 3.0 Liters clean water daily for renal clearance of urate.")
        strictly_avoid.extend(["Organ meats (liver, kidneys), red meat, venison", "Beer, spirits, high-purine seafood (anchovies, sardines, shellfish)", "High fructose corn syrup sweetened beverages"])
        strongly_recommend.extend(["Tart cherry juice / cherries (anthocyanins reduce urate)", "Low-fat dairy / yogurt (uricosuric effect of orotic acid)", "Lemon water, celery seeds, cucumbers", "Ample alkaline vegetables"])

    # Liver Function / NAFLD adjustments
    if is_liver_risk:
        protocols.append("Hepatic Antioxidant & Anti-Inflammatory Protocol")
        constraints.extend(["Eliminate all alcohol consumption.", "Strict avoidance of industrial fructose."])
        strictly_avoid.extend(["Alcoholic beverages", "Saturated fats & ultra-processed snacks", "Excessive acetaminophen / OTC hepatotoxins"])
        strongly_recommend.extend(["Cruciferous vegetables (sulforaphane for phase II liver detox)", "Artichokes, milk thistle tea, green tea (EGCG)", "Garlic and turmeric (curcumin with black pepper)"])

    # Hypokalemia (Low Potassium)
    if is_hypokalemic:
        protocols.append("Electrolyte & Potassium Replenishment Protocol")
        constraints.append("Include potassium-dense whole foods daily (target 3500-4000 mg/day).")
        strongly_recommend.extend(["Tender coconut water", "Avocados, bananas, spinach", "Baked sweet potatoes", "White beans / lentils"])

    # Thyroid / Subclinical Hypothyroidism (Elevated TSH)
    if is_hypothyroid:
        protocols.append("Thyroid & Metabolic Support Protocol")
        constraints.append("Ensure adequate dietary iodine, selenium, and zinc; cook cruciferous vegetables thoroughly to neutralize goitrogens.")
        strongly_recommend.extend(["Brazil nuts (1-2 per day for selenium)", "Iodized sea salt / sea vegetables", "Pumpkin seeds (zinc)"])

    # Calculate gram breakdowns
    carb_calories = target_kcal * (carb_pct / 100.0)
    protein_calories = target_kcal * (protein_pct / 100.0)
    fat_calories = target_kcal * (fat_pct / 100.0)

    carb_grams = round(carb_calories / 4.0)
    protein_grams = round(protein_calories / 4.0)
    fat_grams = round(fat_calories / 9.0)

    # Clean duplicates
    strictly_avoid = list(dict.fromkeys(strictly_avoid))
    strongly_recommend = list(dict.fromkeys(strongly_recommend))

    return {
        "energy": energy,
        "protocols": protocols,
        "macros": {
            "calories": target_kcal,
            "carbs": {"grams": carb_grams, "percentage": carb_pct, "calories": round(carb_calories)},
            "protein": {"grams": protein_grams, "percentage": protein_pct, "calories": round(protein_calories)},
            "fat": {"grams": fat_grams, "percentage": fat_pct, "calories": round(fat_calories)}
        },
        "micronutrient_targets": {
            "sodium_max_mg": 1800 if is_hypertensive or is_renal_risk else 2300,
            "potassium_target_mg": 3800 if is_hypertensive and not is_renal_risk else 3000,
            "fiber_min_g": 35 if is_diabetic or is_dyslipidemic else 28,
            "water_intake_liters": 3.0 if is_hyperuricemic else 2.5,
            "vit_d_supplementation": "High Priority (Suggested 2000-4000 IU/day with doctor confirmation)" if vit_d_low else "Maintenance",
            "vit_b12_supplementation": "Suggested 500-1000 mcg sublingual with doctor confirmation" if vit_b12_low else "Adequate dietary intake"
        },
        "clinical_constraints": constraints,
        "strictly_avoid": strictly_avoid if strictly_avoid else ["Ultra-processed fast foods", "Refined sugary drinks", "Industrial trans-fats"],
        "strongly_recommend": strongly_recommend if strongly_recommend else ["Diverse colorful vegetables", "Lean proteins", "Healthy unsaturated fats", "High fiber whole foods"]
    }
