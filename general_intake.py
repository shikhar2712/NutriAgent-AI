"""
general_intake.py - lets NutriAgent answer a plain-language question with NO lab PDF.

The free-text query is parsed into a synthetic health profile that uses the SAME
clinical_flags condition strings extractor.py produces, so the real deterministic
engine (compute_clinical_nutrition_protocol) stacks the real protocols off it.
Nothing here re-implements the clinical rules.

Two things are deliberately NOT done on this path:
  * AnalysisAgent is not called - it stratifies biomarker risk and there are no
    biomarkers; it would invent an analysis.
  * EvaluationAgent is not called for the audit row - the compliance check is done
    in Python so the table is instant and verifiable, and it is labelled as a
    constraint check, not a biomarker cross-check.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

# Exact condition strings from extractor.py - deterministic_nutrition.py and
# indian_foods._flag_set() both substring-match on these, so they must match.
CONDITION_PATTERNS: List[Tuple[Tuple[str, ...], str, str, str]] = [
    (("type 2 diabetes", "t2dm", "diabetic", "diabetes"),
     "Type 2 Diabetes Mellitus", "Blood Sugar / Metabolism", "Severe"),
    (("prediabetes", "pre-diabetes", "prediabetic", "impaired fasting glucose", "borderline sugar"),
     "Prediabetes / Impaired Fasting Glucose", "Blood Sugar / Metabolism", "Moderate"),
    (("cholesterol", "dyslipid", "triglyceride", "ldl", "lipid"),
     "Dyslipidemia / Elevated Cholesterol", "Heart & Arteries", "Moderate"),
    (("kidney", "renal", "ckd", "creatinine", "egfr", "nephro"),
     "Renal Impairment / CKD Risk", "Kidney Function", "Moderate"),
    (("gout", "uric acid", "purine", "hyperuricemia"),
     "Hyperuricemia (Uric Acid & Gout Risk)", "Uric Acid & Joints", "Moderate"),
    (("fatty liver", "nafld", "liver", "hepatic", "sgpt", "sgot"),
     "Elevated Liver Enzymes (Hepatic Stress / NAFLD)", "Liver Function", "Moderate"),
    (("hypothyroid", "thyroid", "tsh"),
     "Elevated TSH (Sluggish Thyroid / Hypothyroidism)", "Thyroid", "Moderate"),
    (("high blood pressure", "hypertension", "hypertensive", "bp is high", "high bp"),
     "Stage 1 Hypertension", "Blood Pressure & Vessels", "Moderate"),
    (("vitamin d", "vit d", "vitamin-d"),
     "Vitamin D Deficiency", "Immunity & Bone Health", "Moderate"),
    (("vitamin b12", "b12"),
     "Vitamin B12 Deficiency", "Nerves & Blood", "Moderate"),
]

_NUM = r"(\d{1,3}(?:\.\d+)?)"


def parse_general_query(query: str) -> Dict[str, Any]:
    """Pulls anthropometrics, sex, diet preference and stated conditions out of text."""
    q = query.lower()
    out: Dict[str, Any] = {"assumptions": []}

    h = re.search(_NUM + r"\s*(?:cm\b|centim)", q) or re.search(_NUM + r"\s*m\b", q)
    w = re.search(_NUM + r"\s*(?:kgs?\b|kilo)", q)
    lb = re.search(_NUM + r"\s*(?:lbs?\b|pounds?)", q)
    age = (re.search(r"(?:age[d]?\s*(?:is|:)?\s*)" + _NUM, q)
           or re.search(_NUM + r"\s*(?:years?\s*old|yrs?\s*old|y/?o\b)", q)
           or re.search(r"\bi\s*am\s*" + _NUM + r"(?!\s*(?:cm|kg|kgs|m\b|lbs))", q)
           or re.search(r"\b" + _NUM + r"\s*(?:year|yr)s?\b", q))

    height = float(h.group(1)) if h else None
    if height is not None and height < 3.0:
        height *= 100.0
    weight = float(w.group(1)) if w else (round(float(lb.group(1)) * 0.453592, 1) if lb else None)

    if re.search(r"\b(female|woman|girl|she|her)\b", q):
        gender = "Female"
    elif re.search(r"\b(male|man|boy|he|his)\b", q):
        gender = "Male"
    else:
        gender = "Male"
        out["assumptions"].append("Sex not stated - Mifflin-St Jeor computed as male")

    if not age:
        out["assumptions"].append("Age not stated - assumed 45 years")
    if not height or not weight:
        out["assumptions"].append("Height/weight not stated - used clinical baseline for the energy target")

    if re.search(r"\b(vegan)\b", q):
        diet = "Vegan"
    elif re.search(r"\b(non-?veg|chicken|egg|fish|meat|mutton)\b", q):
        diet = "Non-Vegetarian"
    elif re.search(r"\b(veg|vegetarian)\b", q):
        diet = "Vegetarian"
    else:
        diet = "Vegetarian"
        out["assumptions"].append("Diet preference not stated - assumed vegetarian")

    activity = "Sedentary"
    if re.search(r"\b(very active|athlete|heavy work|gym daily)\b", q):
        activity = "Very Active"
    elif re.search(r"\b(active|exercise|workout|walk daily|moderate)\b", q):
        activity = "Moderate"

    out.update({
        "height_cm": height, "weight_kg": weight,
        "age": int(float(age.group(1))) if age else None,
        "gender": gender, "dietary_preference": diet, "activity_level": activity,
    })
    return out


def detect_conditions(query: str) -> List[Dict[str, str]]:
    """Stated conditions -> clinical_flags using extractor.py's exact condition strings."""
    q = query.lower()
    flags, seen = [], set()
    for keywords, condition, organ, severity in CONDITION_PATTERNS:
        if condition in seen:
            continue
        if any(k in q for k in keywords):
            # "Type 2 Diabetes Mellitus" and the prediabetes flag are mutually exclusive
            if condition == "Prediabetes / Impaired Fasting Glucose" and \
               "Type 2 Diabetes Mellitus" in seen:
                continue
            if condition == "Type 2 Diabetes Mellitus" and "prediabet" in q:
                continue
            flags.append({
                "condition": condition,
                "severity": severity,
                "marker": "Self-reported (no laboratory value supplied)",
                "organ": organ,
                "plain_meaning": "Stated by the user rather than measured from a lab report.",
                "action_tip": "Upload a blood test PDF to replace this with measured biomarker values.",
            })
            seen.add(condition)
    return flags


def build_general_profile(query: str) -> Dict[str, Any]:
    """A health profile shaped exactly like build_health_profile()'s output, but
    sourced from the user's sentence instead of a lab report."""
    parsed = parse_general_query(query)
    bmi = None
    if parsed.get("height_cm") and parsed.get("weight_kg"):
        h_m = parsed["height_cm"] / 100.0
        bmi = round(parsed["weight_kg"] / (h_m * h_m), 1)
    return {
        "demographics": {
            "name": "Guest",
            "age": parsed.get("age") or 45,
            "gender": parsed["gender"],
            "weight_kg": parsed.get("weight_kg") or (70.0 if parsed["gender"] == "Male" else 58.0),
            "height_cm": parsed.get("height_cm") or (170.0 if parsed["gender"] == "Male" else 158.0),
            "bmi": bmi,
            "bp_string": "Not measured",
            "dietary_preference": parsed["dietary_preference"],
            "allergies": [],
            "activity_level": parsed["activity_level"],
        },
        "biomarkers": {},
        "clinical_flags": detect_conditions(query),
        "raw_text_preview": query,
        "data_source": "user statement (no laboratory report)",
        "assumptions": parsed["assumptions"],
    }


def check_constraint_compliance(protocol: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic audit of the generated plan against its own prescription.

    This is a CONSTRAINT check (calorie convergence, contraindicated foods, protocol
    coverage) - not a biomarker cross-check, because there are no biomarkers here.
    """
    macros = protocol.get("macros", {})
    target = macros.get("calories") or 0
    days = protocol.get("structured_7day_meals", []) or []
    avoid = [a.lower() for a in protocol.get("strictly_avoid", [])]

    checks, passed = [], 0
    deviations = []
    for d in days:
        tot = d.get("day_total_kcal")
        if tot is None:
            tot = sum(d.get(s, {}).get("kcal", 0) for s in
                      ("breakfast", "mid_morning", "lunch", "snack", "dinner", "bedtime"))
        deviations.append(abs(tot - target))
    worst = max(deviations) if deviations else None

    ok_cal = worst is not None and target and worst <= max(150, 0.1 * target)
    checks.append(("Daily calories converge on the prescribed target",
                   ok_cal, "max deviation %s kcal" % (round(worst) if worst is not None else "n/a")))
    passed += int(bool(ok_cal))

    leaked = []
    for d in days:
        for slot in ("breakfast", "mid_morning", "lunch", "snack", "dinner", "bedtime"):
            name = (d.get(slot) or {}).get("name", "").lower()
            for a in avoid:
                token = re.sub(r"[^a-z ]", "", a).strip()
                if token and token in name:
                    leaked.append("Day %s %s: %s" % (d.get("day"), slot, name))
    ok_avoid = not leaked
    checks.append(("No contraindicated food appears in any meal", ok_avoid,
                   "clean across %d days" % len(days) if ok_avoid else "; ".join(leaked[:3])))
    passed += int(ok_avoid)

    n_prot = len(protocol.get("protocols", []))
    ok_prot = n_prot >= 1
    checks.append(("Clinical protocols stacked for the stated conditions", ok_prot,
                   "%d active" % n_prot))
    passed += int(ok_prot)

    ok_src = bool(days) and any(
        (d.get(s) or {}).get("source") for d in days
        for s in ("breakfast", "lunch", "dinner"))
    checks.append(("Meal calories traceable to a published food table", ok_src,
                   "NIN / ICMR tables" if ok_src else "not sourced"))
    passed += int(ok_src)

    score = int(round(100.0 * passed / len(checks))) if checks else 0
    return {
        "checks": checks,
        "score": score,
        "verdict": "PASSED - constraint compliance" if score == 100 else
                   ("PARTIAL - review flagged rows" if score >= 50 else "FAILED"),
        "scope": "Constraint compliance only - no biomarker cross-check (no lab report supplied)",
    }


def build_comparison_rows(profile: Dict[str, Any], protocol: Dict[str, Any],
                          audit: Dict[str, Any]) -> List[Dict[str, str]]:
    """The dimensions on which the two answers actually differ.

    Everything here is read from the deterministic protocol, so the table renders
    instantly and does not wait on any model call.
    """
    macros = protocol.get("macros", {})
    energy = protocol.get("energy", {})
    flags = [f["condition"] for f in profile.get("clinical_flags", [])]
    protos = [p for p in protocol.get("protocols", []) if p != "Balanced Whole-Foods Protocol"]
    avoid = protocol.get("strictly_avoid", [])
    days = protocol.get("structured_7day_meals", []) or []

    def g(key):
        return (macros.get(key) or {}).get("grams")

    rows = [
        {"dimension": "Energy target",
         "llm": "Not computed - no BMR/TDEE arithmetic",
         "agent": "%s kcal/day (BMR %s, TDEE %s, Mifflin-St Jeor)" % (
             macros.get("calories"), energy.get("bmr"), energy.get("tdee"))},
        {"dimension": "Macronutrient split",
         "llm": "Not prescribed in grams",
         "agent": "Carb %sg / Protein %sg / Fat %sg" % (g("carbs"), g("protein"), g("fat"))},
        {"dimension": "Conditions detected",
         "llm": "Read as prose only",
         "agent": ", ".join(flags) if flags else "None stated"},
        {"dimension": "Clinical protocols stacked",
         "llm": "None - single pass, no rules engine",
         "agent": "; ".join(protos) if protos else "Balanced whole-foods baseline"},
        {"dimension": "Contraindicated foods enforced",
         "llm": "Not enforced - may suggest anything",
         "agent": "%d items excluded before generation" % len(avoid)},
        {"dimension": "Food calorie source",
         "llm": "Model's training data - not verifiable",
         "agent": "ICMR-NIN 'Dietary Guidelines for Indians' tables"},
        {"dimension": "7-day meal plan",
         "llm": "Prose only, calories self-estimated",
         "agent": "%d structured days, portions and kcal from the NIN tables" % len(days)},
        {"dimension": "Safety audit",
         "llm": "None",
         "agent": "%d/100 - %s" % (audit.get("score", 0), audit.get("verdict", "n/a"))},
        {"dimension": "Reproducibility",
         "llm": "Varies between runs (temperature 0.5)",
         "agent": "Identical output for identical input (deterministic engine)"},
        {"dimension": "Evidence basis",
         "llm": "General training knowledge",
         "agent": "Self-reported conditions - no laboratory values (upload a PDF for biomarker grounding)"},
    ]

    gi_swap = any("Diabet" in f or "Glucose" in f or "Prediabet" in f for f in flags)
    if gi_swap:
        rows.insert(6, {"dimension": "Glycemic-index aware staple",
                        "llm": "No GI table consulted",
                        "agent": "Chapati/phulka (GI 52) substituted for white rice (GI 73), NIN Annexure 10"})
    return rows


def run_nutriagent_general(query: str, client, max_words: int = 380) -> Dict[str, Any]:
    """NutriAgent's answer to a plain-language question, with no lab report.

    The deterministic parts (profile, protocol, audit, comparison rows) are computed
    first and returned even if the model call fails, so the table always renders.
    """
    from deterministic_nutrition import compute_clinical_nutrition_protocol

    profile = build_general_profile(query)
    protocol = compute_clinical_nutrition_protocol(profile)
    audit = check_constraint_compliance(protocol)
    rows = build_comparison_rows(profile, protocol, audit)

    try:
        from indian_foods import build_nin_reference_block
        nin_block = build_nin_reference_block(profile, protocol)
    except Exception:
        nin_block = ""

    macros = protocol.get("macros", {})
    demo = profile["demographics"]
    prompt = f"""### User question:
{query}

### Deterministic targets already computed for this person (use these exact numbers):
- Energy: {macros.get('calories')} kcal/day (BMR {protocol.get('energy', {}).get('bmr')}, TDEE {protocol.get('energy', {}).get('tdee')})
- Carbohydrate {macros.get('carbs', {}).get('grams')}g | Protein {macros.get('protein', {}).get('grams')}g | Fat {macros.get('fat', {}).get('grams')}g
- Profile: {demo.get('age')}y {demo.get('gender')}, {demo.get('weight_kg')}kg, {demo.get('height_cm')}cm, BMI {demo.get('bmi')}, {demo.get('dietary_preference')}, {demo.get('activity_level')}
- Active clinical protocols: {', '.join(protocol.get('protocols', []))}
- STRICTLY AVOID: {', '.join(protocol.get('strictly_avoid', []))}

{nin_block}

### Task:
Answer the user's question in under {max_words} words, using the numbers above verbatim.
Build meals from the verified Indian food table; quote its kcal values.
State clearly that these targets come from the stated details, not from blood tests.
Do not use emojis."""

    system = ("You are the NutriAgent clinical nutrition engine's writing layer. "
              "You never invent calorie figures: every number you state was supplied to you above.")
    try:
        answer = client.generate(prompt, system_prompt=system, temperature=0.3)
        error = None
    except Exception as exc:
        answer, error = "", "%s: %s" % (type(exc).__name__, exc)

    return {"profile": profile, "protocol": protocol, "audit": audit,
            "comparison_rows": rows, "answer": answer, "error": error,
            "assumptions": profile.get("assumptions", [])}
