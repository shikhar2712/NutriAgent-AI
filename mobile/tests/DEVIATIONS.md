# engine.js vs the Python originals - deliberate deviations

Everything not listed here is checked for exact parity by `tests/parity.test.js`.

1. **Activity level normalised.** `"Very Active"` (and any spaced/hyphenated form) maps to `very_active` = x1.9.
   Python's lookup used `str.lower()` only, so "Very Active" silently fell back to x1.375.
2. **Allergen labels work.** The exact sidebar labels (`ALLERGEN_OPTIONS[].label`) expand to NIN food-name aliases
   (word-boundary match, optional plural). Bare/legacy tokens ("peanut", "milk", "gluten", ...) still use Python's
   original substring + alias table. Python never matched the labels ("Gluten / Celiac" -> "gluten  celiac").
   Matching is on food *name*; the only hidden-ingredient rule added is that the nut allergy also removes Poha and Upma
   (routinely tempered with groundnuts/cashews). `tests/safety.test.js` guards this. Other hidden ingredients
   (ghee in kichdi, hing/wheat) cannot be detected, and the app says so on the plan screen.
3. **Pescatarian** excludes chicken/mutton/keema only; fish, prawn and egg stay. Python treated it as non-veg.
   Vegetarian/Vegan behave as in Python (Vegan still allows dairy and honey, as in Python).
4. **Western plan dropped.** No `western_7day_meals`, `western_grocery_categories`, `western_strongly_recommend`.
   Without NIN data `computeProtocol` returns an empty `structured_7day_meals`, the Western grocery list, and
   `cuisine: "Unavailable (NIN data not loaded)"`.
5. **`prepareGeneral(query, overrides)`** (new): `allergies` always applied; `dietary_preference` / `activity_level`
   only when the query did not state them. With no overrides the output equals Python's.
6. **New exports** (no Python equivalent): `exclusionReason`, `flagSet`, `allFoods`.

Python quirks replicated on purpose: Python's `check_constraint_compliance` and `prompt` text, "Non-Vegetarian"
diet words, `age` regexes that can pick the wrong number, the 120 kcal day-total tolerance loop, and
`str(float)` formatting ("118.0") in flag markers.
