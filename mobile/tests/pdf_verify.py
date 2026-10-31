"""Compares pdf.js text extraction against pdfplumber through the ORIGINAL extractor.py."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from extractor import extract_text_from_pdf, build_health_profile

samples = os.path.join(HERE, "pdf_samples")
subprocess.check_call([sys.executable, os.path.join(HERE, "pdf_make_samples.py"), samples])
pdfs = [os.path.join(ROOT, "sample_blood_test_report.pdf"),
        os.path.join(samples, "female_cbc_thyroid.pdf"),
        os.path.join(samples, "table_heavy_male.pdf")]
outj = os.path.join(samples, "pdfjs_out.json")
subprocess.check_call(["node", os.path.join(HERE, "pdf_extract_cli.js"), outj] + pdfs, cwd=HERE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
js = json.load(open(outj))


def view(p):
    return {"demographics": p["demographics"], "flags": p["clinical_flags"],
            "biomarkers": {k: {x: b[x] for x in ("name", "value", "unit", "status", "range")}
                           for k, b in p["biomarkers"].items()}}


bad = 0
for pdf in pdfs:
    with open(pdf, "rb") as fh:
        py_text, _ = extract_text_from_pdf(fh)
    a, b = build_health_profile(py_text), build_health_profile(js[pdf]["text"])
    va, vb = view(a), view(b)
    name = os.path.basename(pdf)
    if va == vb:
        print("PASS %-26s biomarkers=%d flags=%d chars py=%d js=%d" % (
            name, len(va["biomarkers"]), len(va["flags"]), len(py_text), len(js[pdf]["text"])))
    else:
        bad += 1
        print("FAIL", name)
        for sec in va:
            if va[sec] != vb[sec]:
                keys = set(va[sec]) | set(vb[sec])
                for k in sorted(keys, key=str):
                    x = va[sec].get(k) if isinstance(va[sec], dict) else None
                    y = vb[sec].get(k) if isinstance(vb[sec], dict) else None
                    if x != y:
                        print("  %s.%s\n    plumber: %s\n    pdf.js : %s" % (sec, k, x, y))
                if isinstance(va[sec], list):
                    print("  plumber:", va[sec]); print("  pdf.js :", vb[sec])
        print("--- pdf.js text ---\n" + js[pdf]["text"][:1500])
sys.exit(1 if bad else 0)
