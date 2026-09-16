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

    # Build categorized smart grocery list
    grocery_categories = {
        "Fresh Vegetables & Greens": [
            "Baby spinach, Tuscan kale, Swiss chard",
            "Broccoli crowns & cauliflower (sulforaphane rich)",
            "English cucumbers & celery stalks (natural diuretics)",
            "Bell peppers (red/yellow for Vitamin C)",
            "Zucchini, asparagus, and button mushrooms"
        ],
        "Whole Grains & Complex Starches": [
            "Steel-cut oats (high beta-glucan)",
            "Organic tri-color quinoa",
            "Sprouted brown lentils & black chickpeas (chana)",
            "Pearl barley or buckwheat",
            "Sweet potatoes / Japanese yams (potassium-rich)"
        ],
        "Lean Proteins & Plant Power": [
            "Wild Alaskan salmon or rainbow trout fillets",
            "Organic pasture-raised eggs / liquid egg whites",
            "Skinless chicken breast or turkey tenderloins",
            "Organic firm non-GMO tofu / tempeh",
            "Sprouted mung beans and edamame"
        ],
        "Heart-Healthy Fats & Seeds": [
            "Extra virgin olive oil (cold-pressed, unrefined)",
            "Raw walnuts (ALA Omega-3 powerhouse)",
            "Raw soaked almonds & pumpkin seeds (zinc)",
            "Chia seeds & ground golden flaxseed",
            "Fresh Hass avocados"
        ],
        "Therapeutic Teas & Seasonings": [
            "Ceylon cinnamon (improves insulin sensitivity)",
            "Organic turmeric powder + black pepper (piperine)",
            "Fresh ginger root and whole garlic cloves",
            "Organic chamomile, peppermint, and hibiscus teas",
            "Lemons and limes for clean alkaline hydration"
        ]
    }

    # Plain-language actionable summary
    plain_summary = []
    if is_diabetic:
        plain_summary.append("Swap white rice, white bread, and sugary treats for steel-cut oats, quinoa, and lentils to keep your blood sugar steady.")
    if is_dyslipidemic:
        plain_summary.append("Replace butter, fried snacks, and fatty meats with heart-friendly extra virgin olive oil, walnuts, and wild fish.")
    if is_hypertensive:
        plain_summary.append("Keep added salt low (under 1 teaspoon daily) and enjoy potassium-rich foods like tender coconut water, spinach, and sweet potatoes.")
    if is_hyperuricemic:
        plain_summary.append("Stay well-hydrated with at least 3 liters of water daily and steer clear of beer, sodas, and organ meats to flush uric acid.")
    if not plain_summary:
        plain_summary.append("Focus on colorful whole foods, clean protein, ample hydration, and 30 minutes of daily brisk walking.")

    # 4 Core daily lifestyle habits
    lifestyle_habits = [
        {"title": "10-Minute Post-Meal Walk", "desc": "A gentle 10-minute walk after lunch and dinner significantly blunts post-meal blood sugar and triglyceride spikes."},
        {"title": "Hydration Rhythm", "desc": "Drink a large glass of water upon waking and space fluids evenly between meals to assist kidney filtration."},
        {"title": "Fiber First Principle", "desc": "Eat your vegetables and salad before your main carbs to create a natural fiber mesh in the stomach that slows sugar absorption."},
        {"title": "Restful Sleep & Stress Care", "desc": "Aim for 7-8 hours of quality sleep to prevent cortisol spikes that drive insulin resistance and blood pressure."}
    ]

    # Pre-computed structured 7-day meal plan
    structured_7day_meals = [
        {
            "day": 1,
            "title": "Metabolic Reset & Anti-Inflammatory Kickstart",
            "focus": "High soluble fiber to lower LDL & smooth glucose curve",
            "breakfast": {"name": "Cinnamon Beta-Glucan Oatmeal", "portion": "1 cup cooked steel-cut oats + 1 tbsp chia seeds + 1/2 cup blueberries + pinch Ceylon cinnamon", "kcal": 380, "why": "Beta-glucan fiber sweeps cholesterol from the gut; cinnamon improves cell insulin uptake."},
            "mid_morning": {"name": "Fresh Green Apple & Soaked Almonds", "portion": "1 crisp green apple + 8 raw soaked almonds", "kcal": 140, "why": "Pectin fiber + healthy fats deliver steady mid-morning energy with zero sugar crashes."},
            "lunch": {"name": "Mediterranean Quinoa & Herb Grilled Protein", "portion": "1 cup cooked quinoa + 120g grilled chicken breast (or steamed tofu) + steamed broccoli + 1 tbsp EVOO", "kcal": 520, "why": "Sulforaphane in broccoli supports liver detox; EVOO provides heart-protective oleic acid."},
            "snack": {"name": "Cucumber Slices & Low-Sodium Hummus", "portion": "1 sliced English cucumber + 3 tbsp homemade tahini-garlic hummus", "kcal": 130, "why": "Hydrating, alkaline, and high in potassium with minimal sodium impact."},
            "dinner": {"name": "Wild Salmon & Garlic Sautéed Asparagus", "portion": "140g baked salmon fillet (or grilled tempeh) + 1 small roasted sweet potato + 1 cup asparagus", "kcal": 490, "why": "Rich in EPA/DHA Omega-3s that reduce serum triglycerides and arterial inflammation."},
            "bedtime": {"name": "Chamomile & Lemon Infusion", "portion": "1 warm cup brewed chamomile tea with a slice of fresh lemon", "kcal": 5, "why": "Calms the nervous system and supports overnight cellular recovery."}
        },
        {
            "day": 2,
            "title": "Glycemic Balance & Heart Protection",
            "focus": "Low glycemic load with abundant antioxidant greens",
            "breakfast": {"name": "Sprouted Grain Avocado & Poached Eggs", "portion": "1 slice 100% sprouted grain sourdough + 2 poached eggs + 1/4 sliced avocado + grilled tomato", "kcal": 390, "why": "Healthy fats + bioavailable protein stabilize morning insulin and blood sugar."},
            "mid_morning": {"name": "Tender Coconut Water & Crushed Chia", "portion": "1 glass fresh coconut water + 1 tsp soaked chia seeds", "kcal": 95, "why": "Natural potassium and electrolytes support healthy vascular tone and kidney function."},
            "lunch": {"name": "Hearty Sprouted Moong Lentil Bowl", "portion": "1.5 cups slow-cooked yellow moong lentils + 1/2 cup brown basmati rice + cucumber-tomato salad", "kcal": 510, "why": "Moong lentils offer clean plant protein and slow-digesting resistant starches."},
            "snack": {"name": "Walnut & Berry Energy Fuel", "portion": "6 raw walnut halves + 1/3 cup fresh raspberries", "kcal": 160, "why": "Alpha-linolenic acid (ALA) in walnuts protects arterial walls."},
            "dinner": {"name": "Herb-Roasted Turkey / Tofu with Bok Choy", "portion": "130g lean roasted turkey breast (or seasoned pan-seared tofu) + stir-fried bok choy in sesame-ginger reduction", "kcal": 460, "why": "Light evening protein that eases digestion and promotes restorative sleep."},
            "bedtime": {"name": "Warm Spiced Turmeric Golden Water", "portion": "Warm water with 1/4 tsp pure turmeric + pinch black pepper", "kcal": 10, "why": "Curcumin combats systemic endothelial inflammation."}
        },
        {
            "day": 3,
            "title": "Renal Ease & Urate Clearance",
            "focus": "Low-purine, kidney-protective, and high-hydration",
            "breakfast": {"name": "Berry Chia Seed Super-Pudding", "portion": "3 tbsp chia seeds soaked in unsweetened almond milk + fresh blackberries + 1 tsp pumpkin seeds", "kcal": 360, "why": "Delivers 11g of fiber and zinc without adding sodium or purines."},
            "mid_morning": {"name": "Tart Cherry Antioxidant Spritzer", "portion": "1/2 cup unsweetened pure tart cherry juice mixed with sparkling water", "kcal": 70, "why": "Anthocyanins in tart cherries assist the kidneys in excreting uric acid."},
            "lunch": {"name": "Rainbow Greek Salad & Grilled Cod", "portion": "130g wild white cod (or grilled halloumi/tofu) + mixed bell peppers, cucumber, Kalamata olives, 1 tbsp EVOO", "kcal": 490, "why": "Low-purine lean marine protein paired with polyphenol-dense crisp vegetables."},
            "snack": {"name": "Crunchy Celery & Unsalted Almond Butter", "portion": "3 celery ribs with 1.5 tbsp unsalted raw almond butter", "kcal": 150, "why": "Natural phthalides in celery help relax blood vessel walls to ease blood pressure."},
            "dinner": {"name": "Stir-Fried Tempeh / Chicken with Zucchini Noodles", "portion": "120g grilled tempeh or chicken + zesty zucchini spirals + cherry tomatoes + garlic-basil pesto", "kcal": 440, "why": "Ultra-low glycemic dinner that keeps nighttime blood sugar completely flat."},
            "bedtime": {"name": "Peppermint & Fennel Digestive Tea", "portion": "1 cup freshly steeped peppermint tea", "kcal": 0, "why": "Soothes gastrointestinal tract and prevents night bloating."}
        },
        {
            "day": 4,
            "title": "Liver Detox & Cellular Regeneration",
            "focus": "Cruciferous greens and polyphenol antioxidants",
            "breakfast": {"name": "Green Superfood Protein Smoothie", "portion": "1 cup baby spinach + 1/2 green banana + 1 scoop plant protein or Greek yogurt + 1 cup almond milk + flaxseed", "kcal": 370, "why": "Provides chlorophyll, magnesium, and slow-burning amino acids for morning energy."},
            "mid_morning": {"name": "Soaked Brazil Nut & Green Tea", "portion": "1-2 raw Brazil nuts + 1 cup organic sencha green tea", "kcal": 75, "why": "Brazil nuts supply 100% daily selenium for thyroid and glutathione synthesis; EGCG protects liver cells."},
            "lunch": {"name": "Warm Chickpea & Roasted Cauliflower Bowl", "portion": "1 cup roasted chickpeas + 1.5 cups spiced cauliflower florets + tahini drizzle + fresh parsley", "kcal": 530, "why": "Sulforaphane boosts Phase II liver enzymes; chickpeas feed beneficial gut flora."},
            "snack": {"name": "Carrot Sticks with Guacamole", "portion": "1 cup raw baby carrots + 2 tbsp fresh homemade guacamole", "kcal": 135, "why": "Beta-carotene and healthy monounsaturated fats support cellular membranes."},
            "dinner": {"name": "Pan-Seared Salmon or Lentil Stew with Spinach", "portion": "130g salmon (or 1.5 cups red lentil stew) + 2 cups wilted garlic spinach with lemon juice", "kcal": 470, "why": "High-potassium, iron-rich dinner supporting clean nighttime vascular recovery."},
            "bedtime": {"name": "Hibiscus Infusion with Lime", "portion": "1 cup unsweetened hibiscus tea", "kcal": 5, "why": "Clinical trials show hibiscus tea helps naturally maintain healthy systolic blood pressure."}
        },
        {
            "day": 5,
            "title": "Cardiovascular Renewal & Nitric Oxide Boost",
            "focus": "Natural nitrates, magnesium, and vascular flexibility",
            "breakfast": {"name": "Spiced Buckwheat / Millet Porridge", "portion": "1 cup cooked buckwheat groats + almond milk + 1 tbsp crushed walnuts + fresh sliced strawberries", "kcal": 380, "why": "Rutin in buckwheat strengthens capillary walls and improves blood circulation."},
            "mid_morning": {"name": "Fresh Beetroot & Pomegranate Shot", "portion": "1/2 cup fresh pressed beet & pomegranate juice", "kcal": 80, "why": "Dietary nitrates convert to nitric oxide, naturally relaxing and widening blood vessels."},
            "lunch": {"name": "Mediterranean Tuna or White Bean Niçoise", "portion": "120g light water-packed tuna (or 1 cup cannellini beans) + steamed green beans, boiled egg, olive oil vinaigrette", "kcal": 510, "why": "Balanced, satisfying protein and fiber that prevents afternoon energy slumps."},
            "snack": {"name": "Raw Pumpkin Seeds & Dried Figs", "portion": "2 tbsp unsalted pumpkin seeds + 1 dried Mission fig", "kcal": 140, "why": "Zinc and magnesium nourish heart muscle tissue and ease vascular tone."},
            "dinner": {"name": "Herb Crusted Chicken or Tofu with Ratatouille", "portion": "130g baked chicken breast (or crispy tofu) + eggplant, zucchini, bell pepper, and tomato stew", "kcal": 450, "why": "Lycopene and anthocyanins protect LDL particles from dangerous oxidation."},
            "bedtime": {"name": "Pure Lemon & Warm Water Cleanse", "portion": "Warm water with half squeezed lemon", "kcal": 5, "why": "Gentle liver support and promotes overnight alkaline balance."}
        },
        {
            "day": 6,
            "title": "Insulin Sensitivity & Satiety Optimization",
            "focus": "Resistant starches, high protein, and clean fats",
            "breakfast": {"name": "Mediterranean Veggie Omelet / Tofu Scramble", "portion": "2 whole eggs + 2 egg whites (or 150g firm tofu) scrambled with spinach, tomatoes, and mushrooms", "kcal": 360, "why": "Zero refined carbs to kickstart fat burning and maintain stable baseline glucose."},
            "mid_morning": {"name": "Kefir or Plant-Based Probiotic Bowl", "portion": "3/4 cup plain unsweetened kefir or coconut yogurt + 1 tsp ground flax", "kcal": 110, "why": "Live probiotic cultures optimize the microbiome to improve insulin signaling."},
            "lunch": {"name": "Black Bean & Quinoa Fiesta Salad", "portion": "1 cup cooked black beans + 1/2 cup quinoa + corn kernels, cilantro, lime juice, 1/4 diced avocado", "kcal": 520, "why": "Soluble fiber and resistant starch provide 6+ hours of smooth, sustained energy."},
            "snack": {"name": "Roasted Edamame Crunch", "portion": "1/3 cup dry-roasted lightly salted edamame", "kcal": 130, "why": "14g of clean plant protein in a convenient, crunchy format."},
            "dinner": {"name": "Grilled Trout / Tempeh with Roasted Brussels Sprouts", "portion": "130g grilled trout (or marinated tempeh) + 1.5 cups caramelized roasted brussels sprouts", "kcal": 470, "why": "Indoles in brussels sprouts enhance hormone metabolism and cardiovascular health."},
            "bedtime": {"name": "Warm Lemon Balm & Chamomile Tea", "portion": "1 cup herbal tea", "kcal": 0, "why": "Promotes deep slow-wave sleep, during which insulin receptors reset."}
        },
        {
            "day": 7,
            "title": "Full System Integration & Weekly Review",
            "focus": "Balanced variety, culinary enjoyment, and weekly sustainability",
            "breakfast": {"name": "Sunday Berry Waffles or Steel-Cut Oat Bowl", "portion": "1 cup warm steel-cut oats (or 1 high-protein almond flour waffle) + fresh blueberries + 1 tbsp hemp hearts", "kcal": 390, "why": "Hemp seeds supply complete amino acids plus optimal 3:1 Omega-6 to Omega-3 ratio."},
            "mid_morning": {"name": "Citrus Grapefruit & Raw Almonds", "portion": "1/2 fresh pink grapefruit + 8 raw almonds", "kcal": 120, "why": "Naringenin in grapefruit has been shown to support healthy glucose regulation."},
            "lunch": {"name": "Sunday Roast Chicken or Lentil Loaf with Vegetables", "portion": "130g roast chicken breast (or lentil vegetable slice) + roasted carrots, parsnips, and green salad", "kcal": 530, "why": "Wholesome, comforting weekend meal packed with micronutrients and dietary fiber."},
            "snack": {"name": "Spiced Roasted Chickpeas", "portion": "1/3 cup crispy chickpeas roasted with smoked paprika and cumin", "kcal": 140, "why": "High-fiber snack that satisfies cravings for crunchy snacks without sodium overload."},
            "dinner": {"name": "Seafood / Tofu Fisherman's Stew", "portion": "1.5 cups light tomato-fennel broth with wild cod, shrimp, or tofu cubes + whole grain toast slice", "kcal": 460, "why": "Easy on evening digestion; provides iodine, selenium, and clean lean protein."},
            "bedtime": {"name": "Golden Turmeric Nightcap", "portion": "Warm almond milk with turmeric, cinnamon, and a drop of pure vanilla", "kcal": 40, "why": "Anti-inflammatory nightcap that preps the body for an energized start to the new week."}
        }
    ]

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
        "strongly_recommend": strongly_recommend if strongly_recommend else ["Diverse colorful vegetables", "Lean proteins", "Healthy unsaturated fats", "High fiber whole foods"],
        "plain_summary": plain_summary,
        "lifestyle_habits": lifestyle_habits,
        "grocery_categories": grocery_categories,
        "structured_7day_meals": structured_7day_meals
    }
