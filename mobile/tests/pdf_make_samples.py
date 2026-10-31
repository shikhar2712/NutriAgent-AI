"""Generates two extra lab-report PDFs with different layouts for extraction tests."""
import os, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "pdf_samples")
os.makedirs(OUT, exist_ok=True)
ss = getSampleStyleSheet()


def grid(rows, widths, header=True):
    t = Table(rows, colWidths=widths)
    st = [("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("FONTSIZE", (0, 0), (-1, -1), 9)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey))
    t.setStyle(TableStyle(st))
    return t


# 1) two-column CBC / thyroid report, female patient
def female():
    doc = SimpleDocTemplate(os.path.join(OUT, "female_cbc_thyroid.pdf"), pagesize=A4)
    s = [Paragraph("<b>SUNRISE DIAGNOSTICS - HAEMATOLOGY & ENDOCRINE REPORT</b>", ss["Heading2"]),
         Paragraph("Patient Name: Ms. Anita Rao", ss["Normal"]),
         Paragraph("Age / Sex: 34 Yrs / Female", ss["Normal"]),
         Paragraph("Height / Weight: 162 cm / 58 kg", ss["Normal"]),
         Paragraph("Blood Pressure: 128/82 mmHg", ss["Normal"]), Spacer(1, 10)]
    left = [["Test", "Result", "Range"],
            ["Hemoglobin", "10.8 g/dL", "12.0 - 15.5"],
            ["Total Leukocyte Count", "7.2", "4.5 - 11.0"],
            ["Platelet Count", "265", "150 - 450"],
            ["Serum Ferritin", "12", "20 - 250"]]
    right = [["Test", "Result", "Range"],
             ["TSH", "6.8", "0.4 - 4.0"],
             ["Vitamin D", "17.5", "30 - 100"],
             ["Vitamin B12", "180", "200 - 900"],
             ["Fasting Blood Sugar", "104", "70 - 99"]]
    two = Table([[grid(left, [95, 55, 60]), grid(right, [95, 55, 60])]], colWidths=[240, 240])
    s += [two, Spacer(1, 12), Paragraph("HbA1c 5.9 % (reference 4.0 - 5.6)", ss["Normal"]),
          Paragraph("Total Cholesterol: 214 mg/dL", ss["Normal"]),
          Paragraph("Serum Uric Acid 5.1 mg/dL", ss["Normal"])]
    doc.build(s)


# 2) table-heavy, multi-page, male patient with kidney/liver markers
def heavy():
    doc = SimpleDocTemplate(os.path.join(OUT, "table_heavy_male.pdf"), pagesize=A4)
    s = [Paragraph("<b>CITY PATHOLOGY LAB - COMPREHENSIVE METABOLIC PANEL</b>", ss["Heading2"]),
         grid([["Patient Name: Mr. Kiran Shah", "Age: 61 Years", "Sex: Male"],
               ["Height: 168 cm", "Weight: 91 kg", "BP: 146/92"]], [200, 130, 130], header=False),
         Spacer(1, 10)]
    rows = [["Test Description", "Observed Value", "Reference Range", "Units", "Flag"],
            ["Fasting Blood Glucose (FBS)", "131.0", "70.0 - 99.0", "mg/dL", "HIGH"],
            ["HbA1c (Glycated Hemoglobin)", "7.1", "4.0 - 5.6", "%", "HIGH"],
            ["Total Cholesterol", "246.0", "125.0 - 200.0", "mg/dL", "HIGH"],
            ["Triglycerides", "260.0", "< 150.0", "mg/dL", "HIGH"],
            ["HDL Cholesterol", "35.0", "> 40.0", "mg/dL", "LOW"],
            ["LDL Cholesterol (Direct)", "162.0", "< 100.0", "mg/dL", "HIGH"],
            ["Serum Creatinine", "1.6", "0.60 - 1.20", "mg/dL", "HIGH"],
            ["Estimated GFR (CKD-EPI)", "48.0", "> 90.0", "mL/min", "LOW"],
            ["Blood Urea Nitrogen (BUN)", "28.0", "7.0 - 20.0", "mg/dL", "HIGH"],
            ["Serum Uric Acid", "8.4", "3.4 - 7.0", "mg/dL", "HIGH"]]
    s.append(grid(rows, [150, 70, 80, 50, 45]))
    s.append(Spacer(1, 400))      # push the next section to page 2
    rows2 = [["Test Description", "Observed Value", "Reference Range", "Units", "Flag"],
             ["ALT (SGPT)", "88.0", "7.0 - 56.0", "U/L", "HIGH"],
             ["AST (SGOT)", "61.0", "10.0 - 40.0", "U/L", "HIGH"],
             ["Total Bilirubin", "0.9", "0.20 - 1.20", "mg/dL", "NORMAL"],
             ["Serum Potassium (K+)", "5.3", "3.5 - 5.0", "mEq/L", "HIGH"],
             ["Serum Sodium (Na+)", "139.0", "135.0 - 145.0", "mEq/L", "NORMAL"],
             ["Vitamin D (25-Hydroxy)", "24.0", "30.0 - 100.0", "ng/mL", "LOW"]]
    s.append(grid(rows2, [150, 70, 80, 50, 45]))
    doc.build(s)


female(); heavy(); print("wrote", OUT)
