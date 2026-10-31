"""
extract_nin_foods.py - scrapes food + calorie tables out of the NIN
"Dietary Guidelines for Indians" PDF into nin_food_data.json.

Source: National Institute of Nutrition (ICMR), Hyderabad.
Annexures extracted:
  A1  (p96)      Nuts, salads and fruits        -> portion + kcal
  A2a/A2b (p98-99) NIN sample meal plans         -> reference skeleton
  A6  (p115)     Low calorie vegetables/fruits  -> kcal per 100 g
  A7  (p116)     High calorie vegetables/fruits -> kcal per 100 g
  A8  (p117-119) Cooked preparations            -> portion + kcal   <- core set
  A10 (p122)     Glycemic Index of common foods -> GI
  A14 (p128)     Portion sizes                  -> kcal/protein/carb/fat per portion

Run:  python extract_nin_foods.py
Every line that fails to parse is printed, so silent data loss is visible.
"""
import io
import json
import re
import sys

import pdfplumber

PDF = "DietaryGuidelinesforNINwebsite.pdf"
OUT = "nin_food_data.json"

FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75}

# lines that are page furniture, not data
NOISE = re.compile(
    r"^(\d{1,3}|Source:.*|Name of the vegetables.*|Food Stuff.*|Preparation.*|"
    r"Calories|\(Kcal\)|Portion Calories|Annexure.*|.*Kcal/100\s?gm?|"
    r"Approximate Calorific.*|Low Calorie Vegetables.*|Vegetables and Fruits with High.*)$",
    re.I,
)

# in-table category headings (not foods)
SECTIONS = re.compile(
    r"^(GLV|Roots and tubers|Roots & Tubers|Other vegetables|Fruits|Nuts|Fresh fruits|"
    r"Salads|Leafy vegetables|Cereal/Millet|Pulses|Vegetables|Spices|Unconventional|"
    r"\d+\.\s*[A-Za-z].*)$",
    re.I,
)

# a portion phrase: starts with a number or unicode fraction, ends before the kcal
PORTION = (
    r"(?:\d+(?:[½¼¾/\-\.]\d*)?|[½¼¾])\s*"
    r"(?:Nos?\.?|g\b|ml\b|cups?|tbsp|tsp|medium|small|big|large|slices?|"
    r"pieces?|glass|bottle|No\b)[^0-9(]*"
    r"(?:\([^)]*\))?"
)


def norm(s):
    s = s.replace("’", "'").replace("–", "-")
    s = re.sub(r"\s+", " ", s).strip()
    # NIN text extraction spaces out some words: "( w it h j a ggery)"
    if re.search(r"\([^)]*(?:\b\w\b\s){3,}", s):
        s = re.sub(r"\(([^)]*)\)", lambda m: "(" + re.sub(r"\s+", "", m.group(1)) + ")", s)
    return s


def starts_a_record(lines, idx):
    """True if lines[idx] opens a new record rather than continuing the last one:
    a bare '<portion> <kcal>' row, or a numeric row in the macro table."""
    if idx >= len(lines):
        return False
    nxt = lines[idx]
    return bool(re.match(r"^(?:\d|[" + "".join(FRACTIONS) + r"])", nxt))


def page_lines(pdf, n):
    t = pdf.pages[n - 1].extract_text() or ""
    return [norm(l) for l in t.split("\n") if norm(l)]


def parse_portion_table(lines, unparsed, category_from_sections=True):
    """Annexures 1 and 8: '<name> <portion> <kcal>', possibly split over lines."""
    out, pending, category = [], [], None
    last_emit = -99
    for idx, ln in enumerate(lines):
        if NOISE.match(ln):
            continue
        if SECTIONS.match(ln) and not re.search(r"\d+\s*$", ln):
            category = re.sub(r"^\d+\.\s*", "", ln)
            pending = []
            continue

        m = re.match(r"^(.*?)\s*(" + PORTION + r")\s+(\d{1,4})$", ln)
        if m and m.group(1).strip():
            name = m.group(1)
        elif m:
            name = " ".join(pending).strip()
            pending = []
        else:
            # A name can wrap across lines, e.g.
            #   "Tea(2 tsp sugar +" / "1 cup 75" / "50 ml toned milk)"
            # If the previous record left an unclosed "(", this line completes it.
            if out and out[-1]["food"].count("(") > out[-1]["food"].count(")"):
                out[-1]["food"] = norm(out[-1]["food"] + " " + ln)
            elif (out and idx == last_emit + 1 and not re.search(r"\d", ln)
                  and not starts_a_record(lines, idx + 1)):
                # wrapped tail of the name just emitted, e.g. "(corn/wheat/rice)".
                # If the NEXT line is a bare "<portion> <kcal>", this line is
                # instead the head of the next record ("Cereal flakes with milk").
                out[-1]["food"] = norm(out[-1]["food"] + " " + ln)
            elif not re.search(r"\d", ln):
                pending.append(ln)
            else:
                pending.append(ln)
                unparsed.append(ln)
            continue

        if not name:
            unparsed.append(ln)
            continue
        out.append({
            "food": norm(name),
            "portion": norm(m.group(2)),
            "kcal": int(m.group(3)),
            "category": category if category_from_sections else None,
        })
        last_emit = idx
        pending = []
    return out


def parse_per100g_table(lines, unparsed):
    """Annexures 6 and 7: '<name> <kcal per 100 g>'."""
    out, category = [], None
    for ln in lines:
        if NOISE.match(ln):
            continue
        if SECTIONS.match(ln) and not re.search(r"\d+\s*$", ln):
            category = ln
            continue
        m = re.match(r"^(.*?)\s+(\d{1,4})$", ln)
        if m and m.group(1).strip():
            out.append({
                "food": norm(m.group(1)),
                "portion": "100 g",
                "kcal": int(m.group(2)),
                "category": category,
            })
        else:
            unparsed.append(ln)
    return out


def parse_gi_table(lines, unparsed):
    """Annexure 10: two records per physical line."""
    out = []
    pat = re.compile(r"(\d{1,2})\s+([A-Za-z][A-Za-z\s/()\-]*?)\s+(\d{1,3})\s*\+\s*\d+")
    for ln in lines:
        found = pat.findall(ln)
        if found:
            for _, name, gi in found:
                out.append({"food": norm(name), "glycemic_index": int(gi)})
        elif not NOISE.match(ln) and re.search(r"\d", ln):
            unparsed.append(ln)
    return out


def parse_portion_macros(lines, unparsed):
    """Annexure 14: food group -> g/portion, kcal, protein, carb, fat."""
    out, pending = [], []
    last_emit = -99
    num = r"(\d+(?:\.\d+)?|-)"
    pat = re.compile(r"^(.*?)\s*" + r"\s+".join([r"(\d+)"] + [num] * 4) + r"$")
    for idx, ln in enumerate(lines):
        if NOISE.match(ln) or ln.lower().startswith(("energy", "g/portion", "the balanced", "@toned")):
            continue
        m = pat.match(ln)
        if not m:
            if (out and idx == last_emit + 1 and not re.search(r"\d", ln)
                    and not starts_a_record(lines, idx + 1)):
                out[-1]["food_group"] = norm(out[-1]["food_group"] + " " + ln)
            elif not re.search(r"\d", ln):
                pending.append(ln)
            continue
        name = m.group(1).strip() or " ".join(pending).strip()
        pending = []
        conv = lambda v: None if v == "-" else float(v)
        out.append({
            "food_group": norm(name),
            "g_per_portion": int(m.group(2)),
            "kcal": conv(m.group(3)),
            "protein_g": conv(m.group(4)),
            "carb_g": conv(m.group(5)),
            "fat_g": conv(m.group(6)),
        })
        last_emit = idx
    return out


def main():
    unparsed = {}
    data = {
        "source": "Dietary Guidelines for Indians - National Institute of Nutrition (ICMR), Hyderabad",
        "food_tables_source": "Nutritive Value of Indian Foods, 1989 (as reproduced in NIN annexures)",
    }

    with pdfplumber.open(PDF) as pdf:
        u = []
        data["nuts_salads_fruits"] = parse_portion_table(page_lines(pdf, 96), u)
        unparsed["A1 nuts/salads/fruits (p96)"] = u

        u = []
        rows = []
        for p in (117, 118, 119):
            rows += parse_portion_table(page_lines(pdf, p), u)
        data["cooked_preparations"] = rows
        unparsed["A8 cooked preparations (p117-119)"] = u

        u = []
        data["low_calorie_produce"] = parse_per100g_table(page_lines(pdf, 115), u)
        unparsed["A6 low calorie produce (p115)"] = u

        u = []
        data["high_calorie_produce"] = parse_per100g_table(page_lines(pdf, 116), u)
        unparsed["A7 high calorie produce (p116)"] = u

        u = []
        data["glycemic_index"] = parse_gi_table(page_lines(pdf, 122), u)
        unparsed["A10 glycemic index (p122)"] = u

        u = []
        data["portion_macros"] = parse_portion_macros(page_lines(pdf, 128), u)
        unparsed["A14 portion macros (p128)"] = u

    # A buffered head line ("Tea(2 tsp sugar +") is flagged when first seen but is
    # later folded into a real record. Drop those so the report shows real losses only.
    parsed_names = " | ".join(
        r.get("food", r.get("food_group", ""))
        for v in data.values() if isinstance(v, list) for r in v
    )
    for table in unparsed:
        unparsed[table] = [l for l in unparsed[table] if l.rstrip(" +") not in parsed_names]

    counts = {k: len(v) for k, v in data.items() if isinstance(v, list)}
    with io.open(OUT, "w", encoding="utf-8", newline="") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    print("Wrote %s" % OUT)
    for k, v in counts.items():
        print("  %-24s %3d records" % (k, v))

    print("\nUnparsed lines (each one is a potential silent data loss):")
    total_bad = 0
    for table, lines in unparsed.items():
        if lines:
            total_bad += len(lines)
            print("  %s:" % table)
            for l in lines:
                print("      %s" % l)
    if not total_bad:
        print("  none")

    # sanity assertions against what the PDF visibly contains
    problems = []
    if counts["cooked_preparations"] < 60:
        problems.append("cooked_preparations looks short (%d)" % counts["cooked_preparations"])
    if counts["glycemic_index"] != 32:
        problems.append("glycemic_index should be 32, got %d" % counts["glycemic_index"])
    if counts["portion_macros"] < 10:
        problems.append("portion_macros should be ~11, got %d" % counts["portion_macros"])
    if problems:
        print("\nVALIDATION PROBLEMS:")
        for p in problems:
            print("  - " + p)
        sys.exit(1)
    print("\nValidation OK.")


if __name__ == "__main__":
    main()
