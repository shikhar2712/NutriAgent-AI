"""
indian_foods.py - NIN (National Institute of Nutrition) Indian food intelligence.

Loads nin_food_data.json (produced by extract_nin_foods.py from the ICMR-NIN
"Dietary Guidelines for Indians") and uses it two ways:

  1. build_nin_reference_block()  -> a compact, CLINICALLY FILTERED food+kcal table
     injected into the Nutrition Agent prompt, so the LLM writes Indian meals with
     real NIN calorie values instead of inventing them.

  2. build_indian_7day_meals()    -> a DETERMINISTIC Indian/hybrid 7-day plan whose
     kcal come straight from the NIN tables. This is what the day-by-day UI renders,
     so the numbers on screen are sourced, not generated.

Hybrid policy: NIN Indian items are the default building blocks. Western items are
used only for slots NIN does not cover (e.g. seed/nut add-ons), and are labelled.
"""
import io
import json
import os
import re
from typing import Any, Dict, List, Optional

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nin_food_data.json")

# --- clinical exclusion vocabulary -------------------------------------------
FRIED = ("puri", "paratha", "bajji", "pakora", "vada", "samosa", "bonda", "kachori",
         "fried", "puff", "cheese balls", "chips")
# NOTE: the GI table (Annexure 10) and the cooked-preparations table (Annexure 8)
# name foods differently -- "White boiled rice" vs "Rice". These tokens are written
# to match the Annexure 8 / Annexure 1 names that is_allowed() actually sees.
HIGH_GI = ("rice", "cornflakes", "cereal flakes", "bread", "potato",
           "french fries", "glucose", "honey", "toast")
SUGARY = ("barfi", "chikki", "cake", "puttu", "sandesh", "meetha", "halwa", "jelly",
          "jam", "custard", "srikhand", "chocolate", "ice-cream", "ice cream",
          "cold drinks", "squash", "syrups", "sharabats", "sugar")
HIGH_PURINE = ("mutton", "keema", "prawn", "fish", "liver", "organ")
HIGH_SODIUM = ("pizza", "sandwich", "chat", "papad", "pickle")
NON_VEG = ("egg", "ommelette", "omelette", "mutton", "chicken", "fish", "prawn", "keema")

# NIN names an allergen differently from how a patient types it.
_ALLERGY_ALIASES = {
    "peanut": ("groundnut", "peanuts"),
    "peanuts": ("groundnut", "peanuts"),
    "groundnut": ("peanut",),
    "nuts": ("almond", "cashew", "peanut", "groundnut", "walnut", "til"),
    "tree nuts": ("almond", "cashew", "walnut"),
    "milk": ("curd", "lassi", "milk", "paneer", "cheese", "srikhand"),
    "dairy": ("curd", "lassi", "milk", "paneer", "cheese", "srikhand"),
    "lactose": ("curd", "lassi", "milk", "paneer", "cheese"),
    "gluten": ("wheat", "phulka", "paratha", "puri", "bread", "semolina", "upma", "toast"),
    "wheat": ("phulka", "paratha", "puri", "bread", "semolina", "upma", "toast"),
    "soy": ("soya", "soybean"),
    "shellfish": ("prawn",),
    "egg": ("ommelette", "omelette"),
}

_CACHE: Optional[Dict[str, Any]] = None


def load_nin_data() -> Dict[str, Any]:
    """Loads and caches the extracted NIN tables. Returns {} if the file is absent."""
    global _CACHE
    if _CACHE is None:
        try:
            with io.open(DATA_FILE, encoding="utf-8") as fh:
                _CACHE = json.load(fh)
        except (IOError, ValueError):
            _CACHE = {}
    return _CACHE


def gi_index() -> Dict[str, int]:
    """food name (lowercased) -> glycemic index."""
    return {r["food"].lower(): r["glycemic_index"] for r in load_nin_data().get("glycemic_index", [])}


def all_foods() -> List[Dict[str, Any]]:
    """Every food record that carries a kcal value, across all NIN tables."""
    d = load_nin_data()
    out = []
    for key in ("cooked_preparations", "nuts_salads_fruits",
                "low_calorie_produce", "high_calorie_produce"):
        for r in d.get(key, []):
            out.append(dict(r, table=key))
    return out


def _flag_set(health_profile: Dict[str, Any]) -> set:
    """Normalised clinical condition keys from the health profile's flags."""
    text = " ".join(f.get("condition", "") for f in health_profile.get("clinical_flags", [])).lower()
    flags = set()
    if any(k in text for k in ("diabet", "glucose", "glycem")):
        flags.add("diabetes")
    if any(k in text for k in ("lipid", "cholesterol")):
        flags.add("dyslipidemia")
    if "hypertension" in text or "blood pressure" in text:
        flags.add("hypertension")
    if "uric" in text or "gout" in text:
        flags.add("gout")
    if "renal" in text or "kidney" in text:
        flags.add("renal")
    if "hepat" in text or "liver" in text:
        flags.add("liver")
    return flags


def _as_list(value) -> List[str]:
    """Allergies arrive as a list from the multiselect, or as free text."""
    if not value:
        return []
    if isinstance(value, str):
        return [v.strip() for v in re.split(r"[,;/]", value) if v.strip()]
    return [str(v).strip() for v in value if str(v).strip()]


def is_allowed(food: str, flags: set, diet_pref: str = "",
               strictly_avoid: Optional[List[str]] = None,
               allergies: Optional[List[str]] = None) -> bool:
    """True if this NIN food survives the patient's clinical constraints."""
    f = food.lower()
    # Allergies are absolute: they outrank every other rule below.
    for alg in _as_list(allergies):
        token = re.sub(r"[^a-z ]", "", alg.lower()).strip()
        if token and token in f:
            return False
        # common aliases the NIN tables use
        for alias in _ALLERGY_ALIASES.get(token, ()):
            if alias in f:
                return False
    if (diet_pref or "").lower().startswith(("veg", "vegan")) and any(k in f for k in NON_VEG):
        return False
    for item in (strictly_avoid or []):
        token = re.sub(r"[^a-z ]", "", item.lower()).strip()
        if token and (token in f or f in token):
            return False
    if "diabetes" in flags and (any(k in f for k in SUGARY) or any(k in f for k in HIGH_GI)):
        return False
    if "dyslipidemia" in flags and any(k in f for k in FRIED):
        return False
    if "hypertension" in flags and any(k in f for k in HIGH_SODIUM):
        return False
    if "gout" in flags and any(k in f for k in HIGH_PURINE):
        return False
    if "liver" in flags and any(k in f for k in FRIED):
        return False
    return True


# NIN prints these vegetable rows as bare "With gravy" / "Dry" under the
# "Vegetable" heading; give them names that read sensibly on a meal card.
_ALIAS = {
    "With gravy": "Mixed vegetable curry (with gravy)",
    "Dry": "Dry sauteed seasonal vegetable",
}

# Unsweetened milk is not in the cooked-preparations table; NIN Annexure 14 gives
# milk at 70 kcal per 100 ml portion, so a 200 ml cup is 140 kcal.
_PLAIN_MILK = {"food": "Milk, unsweetened", "portion": "1 cup (200 ml)", "kcal": 140,
               "category": "Beverages", "table": "portion_macros"}


def _find(name: str) -> Optional[Dict[str, Any]]:
    """Exact-then-loose lookup of a NIN food record by name."""
    target = name.lower().strip()
    foods = all_foods()
    for r in foods:
        if r["food"].lower() == target:
            return r
    for r in foods:
        # loose match must be a word-boundary hit, so "Vegetable" cannot
        # silently resolve to "Vegetable puff"
        if re.search(r"\b" + re.escape(target) + r"\b", r["food"].lower()):
            return r
    return None


def _compose(parts: List[tuple], why: str, guard=None) -> Dict[str, Any]:
    """parts = [(nin food name, multiplier), ...] -> one meal-card dict.

    kcal is the NIN value times the multiplier, so every number on the meal card
    traces back to a printed table rather than to the model.
    """
    names, portions, kcal = [], [], 0
    for food_name, mult in parts:
        rec = _PLAIN_MILK if food_name == _PLAIN_MILK["food"] else _find(food_name)
        if not rec:
            continue
        # The guard is applied here too, not only when the slot is picked, so a
        # hardcoded part can never smuggle a contraindicated food onto the plan.
        if guard and not guard(rec["food"]):
            continue
        names.append(_ALIAS.get(rec["food"], rec["food"]))
        qty = rec["portion"]
        if mult != 1:
            qty = "%g x %s" % (mult, qty)
        portions.append("%s (%s)" % (qty, _ALIAS.get(rec["food"], rec["food"])))
        kcal += int(round(rec["kcal"] * mult))
    if not names:
        return {}
    return {
        "name": " + ".join(names),
        "portion": " + ".join(portions),
        "kcal": kcal,
        "why": why,
        "source": "NIN Dietary Guidelines for Indians",
    }


# Slot pools, rotated across the 7 days. Everything here exists in the NIN tables.
_BREAKFAST = [
    ([("Idli", 2)], "Steamed, fermented and oil-free; fermentation improves mineral bioavailability."),
    ([("Dosa", 1)], "Rice-lentil batter gives complementary proteins without added fat."),
    ([("Upma", 1)], "Semolina with vegetables delivers slow-release carbohydrate."),
    ([("Wheat porridge", 1)], "Whole wheat porridge is high in soluble fibre that blunts the glucose curve."),
    ([("Poha", 1)], "Flattened rice with vegetables and groundnut for sustained morning energy."),
    ([("Cereal flakes with milk", 1)], "Quick wholegrain start paired with milk protein."),
    ([("Bread", 1)], "Wholegrain slices kept light, paired with the mid-morning protein."),
]
_MID_MORNING = [
    ([("Guava", 1)], "Very high vitamin C and fibre for a low glycemic load."),
    ([("Almonds", 1)], "MUFA and magnesium support insulin sensitivity and vascular tone."),
    ([("Papaya", 1)], "Papain aids digestion; carotenoids support hepatic antioxidant defence."),
    ([("Mosambi/orange", 1)], "Citrus flavonoids improve endothelial function."),
    ([("Apple", 1)], "Pectin, a soluble fibre, binds cholesterol in the gut."),
    ([("Cashewnuts", 1)], "Plant protein and healthy fat to steady mid-morning appetite."),
    ([("Peanuts", 1)], "Affordable ALA-bearing protein with a low glycemic index."),
]
_VEG_MAIN = [
    ("Plain dhal", "Pulses supply lysine-rich protein that complements cereal."),
    ("Sambar", "Lentils with vegetables add fibre, folate and potassium."),
]
_NONVEG_MAIN = [
    ("Chicken curry", "Lean high-biological-value protein without red-meat purines."),
    ("Boiled egg", "Complete protein with choline for hepatic fat metabolism."),
]
_SNACK = [
    ([("Tomato", 1)], "Lycopene-rich and near-zero calorie."),
    ([("Cucumber", 1)], "Hydrating, potassium-bearing and naturally low in sodium."),
    ([("Carrot", 1)], "Beta-carotene supports mucosal and immune health."),
    ([("Radish", 1)], "Very low calorie with natural diuretic action."),
    ([("Beetroot", 1)], "Dietary nitrates support healthy blood pressure."),
    ([("Onion", 1)], "Quercetin, an anti-inflammatory flavonoid."),
    ([("Orange juice", 1)], "Light citrus refresher with vitamin C."),
]


def build_indian_7day_meals(health_profile: Dict[str, Any],
                            nutrition_protocol: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Deterministic Indian/hybrid 7-day plan with NIN-sourced calories.

    Returns [] when the NIN data file is missing, so callers can fall back.
    """
    if not load_nin_data():
        return []

    flags = _flag_set(health_profile)
    demo = health_profile.get("demographics", {})
    diet_pref = demo.get("dietary_preference", "") or ""
    allergies = demo.get("allergies", [])
    avoid = nutrition_protocol.get("strictly_avoid", [])
    target = int(nutrition_protocol.get("macros", {}).get("calories", 1800))
    vegetarian = diet_pref.lower().startswith(("veg", "vegan")) or not diet_pref

    def guard(food):
        return is_allowed(food, flags, diet_pref, avoid, allergies)

    def ok(parts):
        return all(guard(p[0]) for p in parts)

    def pick(pool, day):
        """First clinically allowed option, starting at the day's rotation slot."""
        for i in range(len(pool)):
            parts, why = pool[(day + i) % len(pool)]
            if ok(parts):
                return parts, why
        return None, None

    themes = [
        ("Metabolic Reset", "Fermented, oil-free carbohydrate with high-fibre pulses"),
        ("Glycemic Balance", "Low-GI cereals paired with lysine-rich dhal"),
        ("Cardioprotective Day", "Soluble fibre and MUFA-bearing nuts"),
        ("Renal & Urate Ease", "Moderated protein with high fluid volume"),
        ("Micronutrient Density", "Green leafy vegetables and citrus"),
        ("Digestive Rest", "Light, steamed preparations"),
        ("Sustained Energy", "Whole grains with balanced pulse protein"),
    ]

    days = []
    for d in range(7):
        b_parts, b_why = pick(_BREAKFAST, d)
        m_parts, m_why = pick(_MID_MORNING, d)
        s_parts, s_why = pick(_SNACK, d)

        mains = _VEG_MAIN if vegetarian else (_NONVEG_MAIN + _VEG_MAIN)
        main_name, main_why = None, None
        for i in range(len(mains)):
            cand, why = mains[(d + i) % len(mains)]
            if guard(cand):
                main_name, main_why = cand, why
                break
        if main_name is None:
            main_name, main_why = _VEG_MAIN[0]

        # Cereal base: chapati (GI 52) is preferred over white rice (GI 73) for
        # anyone with a glycemic flag; NIN's own GI table drives this choice.
        # Chapati (GI 52) is preferred over white rice (GI 73) for glycemic flags,
        # but allergies can rule both out -- fall back through the allowed staples.
        staples = ["Phulka", "Rice"] if "diabetes" in flags else ["Rice", "Phulka"]
        staples += ["Idli", "Dosa", "Kichidi"]
        cereal = next((c for c in staples if guard(c)), None)
        cereal_mult = 2.0 if cereal == "Phulka" else 1.0

        def build(mult, veg_item):
            base = [(cereal, mult)] if cereal else []
            lunch = _compose(
                base + [(main_name, 1), (veg_item, 1)],
                main_why + " Chapati is chosen over white rice on NIN's GI table (52 vs 73)."
                if cereal == "Phulka" else main_why,
                guard=guard,
            )
            dinner = _compose(
                ([(cereal, max(1.0, mult - 0.5))] if cereal else []) + [("Plain dhal", 1),
                 ("Dry" if veg_item == "With gravy" else "With gravy", 1)],
                "A lighter evening mirror of lunch eases overnight digestion.",
                guard=guard,
            )
            return lunch, dinner

        veg_item = "With gravy" if d % 2 == 0 else "Dry"
        mult = cereal_mult
        breakfast = _compose(b_parts, b_why, guard=guard) if b_parts else {}
        mid = _compose(m_parts, m_why, guard=guard) if m_parts else {}
        snack = _compose(s_parts, s_why, guard=guard) if s_parts else {}
        # Sweetened milk is dropped for anyone with a glycemic flag; NIN Annexure 14
        # supplies the unsweetened equivalent.
        milk = "Cow's milk" if guard("Cow's milk (2 tsp sugar)") else _PLAIN_MILK["food"]
        # guard always applies -- a dairy allergy must drop the bedtime milk too
        bedtime = _compose([(milk, 1 if milk == _PLAIN_MILK["food"] else 0.5)],
                           "Milk supplies calcium and tryptophan for restful sleep.",
                           guard=guard)

        # Scale the cereal portion until the day lands near the prescribed target.
        for _ in range(14):
            lunch, dinner = build(mult, veg_item)
            total = sum(x.get("kcal", 0) for x in (breakfast, mid, lunch, snack, dinner, bedtime))
            if total < target - 120 and mult < 8:
                mult += 0.5
            elif total > target + 120 and mult > 0.5:
                mult -= 0.5
            else:
                break

        title, focus = themes[d]
        days.append({
            "day": d + 1,
            "title": title,
            "focus": focus,
            "breakfast": breakfast,
            "mid_morning": mid,
            "lunch": lunch,
            "snack": snack,
            "dinner": dinner,
            "bedtime": bedtime,
            "day_total_kcal": total,
            "cuisine": "Indian (NIN-sourced)",
        })
    return days


def build_nin_reference_block(health_profile: Dict[str, Any],
                              nutrition_protocol: Dict[str, Any],
                              max_per_group: int = 12) -> str:
    """Compact, clinically filtered NIN food table for the Nutrition Agent prompt.

    Filtered rather than dumped whole: the full dataset would add ~1400 tokens to a
    prompt that already embeds the analysis report.
    """
    data = load_nin_data()
    if not data:
        return ""

    flags = _flag_set(health_profile)
    demo = health_profile.get("demographics", {})
    diet_pref = demo.get("dietary_preference", "") or ""
    allergies = demo.get("allergies", [])
    avoid = nutrition_protocol.get("strictly_avoid", [])

    groups: Dict[str, List[str]] = {}
    for r in data.get("cooked_preparations", []):
        if not is_allowed(r["food"], flags, diet_pref, avoid, allergies):
            continue
        cat = r.get("category") or "Other"
        groups.setdefault(cat, [])
        if len(groups[cat]) < max_per_group:
            groups[cat].append("%s (%s) = %d kcal" % (
                _ALIAS.get(r["food"], r["food"]), r["portion"], r["kcal"]))

    fruit_nuts = [
        "%s (%s) = %d kcal" % (r["food"], r["portion"], r["kcal"])
        for r in data.get("nuts_salads_fruits", [])
        if is_allowed(r["food"], flags, diet_pref, avoid, allergies)
    ][: max_per_group * 2]

    lines = [
        "### VERIFIED INDIAN FOOD TABLE - NIN / ICMR 'Dietary Guidelines for Indians'",
        "Use THESE foods and THESE calorie values when building meals. Do not invent kcal.",
        "Items contraindicated for this patient have already been removed from this list.",
    ]
    for cat, items in groups.items():
        lines.append("- **%s**: %s" % (cat, "; ".join(items)))
    if fruit_nuts:
        lines.append("- **Fruits / Nuts / Salads**: %s" % "; ".join(fruit_nuts))

    macros = data.get("portion_macros", [])
    if macros:
        lines.append("- **NIN portion macros (per portion)**: " + "; ".join(
            "%s %sg = %s kcal, P %sg, C %sg, F %sg" % (
                m["food_group"], m["g_per_portion"], m["kcal"],
                m["protein_g"], m["carb_g"], m["fat_g"])
            for m in macros))

    gi = data.get("glycemic_index", [])
    if gi and "diabetes" in flags:
        low = sorted([g for g in gi if g["glycemic_index"] < 56], key=lambda x: x["glycemic_index"])
        lines.append("- **Low-GI choices (NIN GI table)**: " + "; ".join(
            "%s GI %d" % (g["food"], g["glycemic_index"]) for g in low[:14]))

    lines.append("Prefer these Indian preparations; use a Western item only where NIN has no equivalent.")
    return "\n".join(lines)


def build_indian_grocery_categories(health_profile: Dict[str, Any],
                                    nutrition_protocol: Dict[str, Any]) -> Dict[str, List[str]]:
    """Grocery list drawn from the NIN tables, so it matches the Indian meal cards
    rendered on the same screen instead of listing quinoa and salmon beneath them."""
    data = load_nin_data()
    if not data:
        return {}

    flags = _flag_set(health_profile)
    demo = health_profile.get("demographics", {})
    diet_pref = demo.get("dietary_preference", "") or ""
    allergies = demo.get("allergies", [])
    avoid = nutrition_protocol.get("strictly_avoid", [])

    def keep(name):
        return is_allowed(name, flags, diet_pref, avoid, allergies)

    produce = [r for r in data.get("low_calorie_produce", []) if keep(r["food"])]
    rich = [r for r in data.get("high_calorie_produce", []) if keep(r["food"])]
    fruits_nuts = [r for r in data.get("nuts_salads_fruits", []) if keep(r["food"])]
    cooked = data.get("cooked_preparations", [])

    def names(rows, n, suffix=""):
        return ["%s%s" % (_ALIAS.get(r["food"], r["food"]), suffix % r if suffix else "")
                for r in rows[:n]]

    cats = {
        "Fresh Vegetables & Greens (NIN low-calorie list)":
            names(produce, 8, " - %(kcal)d kcal/100g"),
        "Cereals, Millets & Pulses":
            [_ALIAS.get(r["food"], r["food"]) + " (%s, %d kcal)" % (r["portion"], r["kcal"])
             for r in cooked if r.get("category") in ("Cereal", "Pulse") and keep(r["food"])][:8],
        "Fruits, Nuts & Salads":
            names(fruits_nuts, 10, " - %(portion)s, %(kcal)d kcal"),
        "Energy-dense staples (use measured portions)":
            names(rich, 6, " - %(kcal)d kcal/100g"),
    }
    return {k: v for k, v in cats.items() if v}


def build_indian_recommendations(health_profile: Dict[str, Any],
                                 nutrition_protocol: Dict[str, Any]) -> List[str]:
    """Indian 'strongly recommend' list drawn from the NIN tables.

    This list is also injected into the Nutrition Agent prompt, so leaving it as
    Western items actively pulled the model away from Indian meals.
    """
    data = load_nin_data()
    if not data:
        return []

    flags = _flag_set(health_profile)
    demo = health_profile.get("demographics", {})
    diet_pref = demo.get("dietary_preference", "") or ""
    allergies = demo.get("allergies", [])
    avoid = nutrition_protocol.get("strictly_avoid", [])

    def keep(n):
        return is_allowed(n, flags, diet_pref, avoid, allergies)

    recs: List[str] = []
    gi = {g["food"].lower(): g["glycemic_index"] for g in data.get("glycemic_index", [])}

    if "diabetes" in flags:
        low_gi = sorted(
            [(g["food"], g["glycemic_index"]) for g in data.get("glycemic_index", [])
             if g["glycemic_index"] < 56],
            key=lambda x: x[1])[:5]
        if low_gi:
            recs.append("Low-GI staples per NIN: " + ", ".join("%s (GI %d)" % (n, v) for n, v in low_gi))
        if gi.get("chappathi") and gi.get("white boiled rice"):
            recs.append("Chapati/phulka (GI %d) in place of white rice (GI %d)"
                        % (gi["chappathi"], gi["white boiled rice"]))

    pulses = [r["food"] for r in data.get("cooked_preparations", [])
              if r.get("category") == "Pulse" and keep(r["food"])]
    if pulses:
        recs.append("Daily pulses for complementary protein: " + ", ".join(pulses))

    greens = [r["food"] for r in data.get("low_calorie_produce", [])
              if keep(r["food"]) and (r.get("category") or "").upper() in ("GLV", "OTHER VEGETABLES")]
    if greens:
        recs.append("High-volume, low-calorie vegetables (NIN < 20 kcal/100 g): "
                    + ", ".join(greens[:6]))

    steamed = [r["food"] for r in data.get("cooked_preparations", [])
               if r.get("category") == "Cereal" and keep(r["food"])
               and r["food"] in ("Idli", "Dosa", "Upma", "Phulka", "Wheat porridge")]
    if steamed:
        recs.append("Steamed / griddle-cooked preparations instead of fried: " + ", ".join(steamed))

    fruits = [r["food"] for r in data.get("nuts_salads_fruits", [])
              if keep(r["food"]) and (r.get("category") or "").lower().startswith("fresh fruit")][:5]
    if fruits:
        recs.append("Whole seasonal fruit rather than juice: " + ", ".join(fruits))

    if "hypertension" in flags:
        recs.append("Season with fresh herbs, lemon and tamarind; NIN caps salt at under 5 g/day")
    if "gout" in flags or "renal" in flags:
        recs.append("Generous fluids through the day: buttermilk, lemon water, tender coconut water")
    return recs
