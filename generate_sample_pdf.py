"""
generate_sample_pdf.py - Generates a realistic clinical pathology lab report in PDF format.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def create_sample_pdf(filename="sample_blood_test_report.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1
    )
    sub_title_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4B5563"),
        alignment=1
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1E40AF"),
        spaceBefore=10,
        spaceAfter=4
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        fontName="Helvetica-Bold"
    )
    cell_high = ParagraphStyle(
        'TableCellHigh',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#DC2626"),
        fontName="Helvetica-Bold"
    )

    story = []

    # Hospital / Lab Header
    story.append(Paragraph("<b>METROPOLITAN CLINICAL DIAGNOSTICS & PATHOLOGY LABORATORY</b>", title_style))
    story.append(Paragraph("NABH & CAP Accredited Clinical Reference Laboratory | 100 Medical Plaza, Suite 400", sub_title_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1E3A8A"), spaceAfter=10))

    # Patient Demographics Table
    demo_data = [
        [Paragraph("<b>Patient Name:</b> Mr. Robert Vance", cell_style), Paragraph("<b>Patient ID:</b> PT-90421", cell_style), Paragraph("<b>Sample Date:</b> 2026-09-12", cell_style)],
        [Paragraph("<b>Age / Sex:</b> 52 Yrs / Male", cell_style), Paragraph("<b>Height / Weight:</b> 175 cm / 86.5 kg", cell_style), Paragraph("<b>BMI:</b> 28.2 kg/m²", cell_style)],
        [Paragraph("<b>Referred By:</b> Dr. Marcus Reed, MD", cell_style), Paragraph("<b>Blood Pressure:</b> 138/88 mmHg", cell_style), Paragraph("<b>Status:</b> Final Verified", cell_style)]
    ]
    t_demo = Table(demo_data, colWidths=[180, 180, 180])
    t_demo.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_demo)
    story.append(Spacer(1, 10))

    # Test Results Header Table
    headers = [
        Paragraph("<b>Test Investigation</b>", cell_bold),
        Paragraph("<b>Observed Value</b>", cell_bold),
        Paragraph("<b>Units</b>", cell_bold),
        Paragraph("<b>Reference Range</b>", cell_bold),
        Paragraph("<b>Status / Flag</b>", cell_bold)
    ]

    tests = [
        # Glycemic
        ("Fasting Blood Glucose (FBS)", "118.0", "mg/dL", "70.0 - 99.0", "HIGH", True),
        ("Postprandial Glucose (PPBS)", "165.0", "mg/dL", "70.0 - 140.0", "HIGH", True),
        ("HbA1c (Glycated Hemoglobin)", "6.4", "%", "4.0 - 5.6", "PREDIABETIC", True),
        # Lipid
        ("Total Cholesterol", "232.0", "mg/dL", "125.0 - 200.0", "HIGH", True),
        ("Triglycerides", "198.0", "mg/dL", "< 150.0", "HIGH", True),
        ("HDL Cholesterol (Good)", "38.0", "mg/dL", "> 40.0", "LOW", True),
        ("LDL Cholesterol (Direct)", "154.0", "mg/dL", "< 100.0", "HIGH", True),
        # Renal & Uric Acid
        ("Serum Creatinine", "1.15", "mg/dL", "0.60 - 1.20", "NORMAL", False),
        ("Estimated GFR (eGFR)", "78.0", "mL/min", "> 90.0", "MILD REDUCTION", True),
        ("Blood Urea Nitrogen (BUN)", "18.0", "mg/dL", "7.0 - 20.0", "NORMAL", False),
        ("Serum Uric Acid", "7.8", "mg/dL", "3.4 - 7.0", "HIGH", True),
        # Liver
        ("ALT (SGPT)", "48.0", "U/L", "7.0 - 56.0", "NORMAL", False),
        ("AST (SGOT)", "36.0", "U/L", "10.0 - 40.0", "NORMAL", False),
        ("Total Bilirubin", "0.85", "mg/dL", "0.20 - 1.20", "NORMAL", False),
        # Vitamins & Electrolytes
        ("Vitamin D (25-OH)", "19.4", "ng/mL", "30.0 - 100.0", "DEFICIENT", True),
        ("Vitamin B12", "310.0", "pg/mL", "200.0 - 900.0", "NORMAL", False),
        ("Serum Potassium (K+)", "4.4", "mEq/L", "3.5 - 5.0", "NORMAL", False),
        ("Serum Sodium (Na+)", "141.0", "mEq/L", "135.0 - 145.0", "NORMAL", False)
    ]

    table_data = [headers]
    for name, val, unit, ref, flag, is_abn in tests:
        table_data.append([
            Paragraph(name, cell_style),
            Paragraph(f"<b>{val}</b>" if is_abn else val, cell_high if is_abn else cell_style),
            Paragraph(unit, cell_style),
            Paragraph(ref, cell_style),
            Paragraph(f"<b>{flag}</b>" if is_abn else flag, cell_high if is_abn else cell_style)
        ])

    t_results = Table(table_data, colWidths=[180, 85, 75, 110, 90])
    t_results.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0284C7")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")])
    ]))

    story.append(t_results)
    story.append(Spacer(1, 12))

    # Pathologist Summary
    story.append(Paragraph("<b>CLINICAL IMPRESSION & INTERPRETATION:</b>", section_style))
    interpretation = """Patient exhibits markers consistent with Metabolic Syndrome: Impaired Fasting Glucose / Prediabetes (HbA1c 6.4%), Mixed Dyslipidemia (elevated Total Cholesterol 232, LDL 154, Triglycerides 198, sub-optimal HDL 38), Stage 1 Hypertension (138/88 mmHg), mild Hyperuricemia (7.8 mg/dL), and Hypovitaminosis D (19.4 ng/mL). Comprehensive medical nutrition therapy, glycemic control, and cardioprotective lifestyle modification strongly recommended."""
    story.append(Paragraph(interpretation, cell_style))

    doc.build(story)
    print(f"Generated {filename} successfully.")


if __name__ == "__main__":
    create_sample_pdf()
