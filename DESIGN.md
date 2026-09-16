# DESIGN.md - NutriAgent AI Design System

## Aesthetic & Vision
NutriAgent AI is a clinical-grade medical and precision nutrition dashboard. The design language combines **clinical trust and precision** with **modern, human-centric wellness aesthetics**.

---

## Color Palette

| Token | Hex | Usage |
| :--- | :--- | :--- |
| **Primary (Slate Brand)** | `#0F172A` | Core text, heavy headings, navbar branding |
| **Accent / Clinical Sky** | `#0284C7` | Active states, primary buttons, pipeline focus |
| **Success / Validated** | `#10B981` | Normal biomarkers, passed audit badges |
| **Warning / Elevated** | `#F59E0B` | Borderline / moderate clinical flags |
| **Critical / High Alert** | `#DC2626` | Severe anomalies, contraindications, strictly avoided foods |
| **Surface Light** | `#F8FAFC` | Page backgrounds, subtle card surfaces |
| **Border / Divider** | `#E2E8F0` | Structural card borders and table dividers |

---

## Typography & Hierarchy
- **Title / H1**: Bold, clean sans-serif, deep slate (`#0F172A`), tight tracking.
- **Section Headers (H2/H3)**: Clean semi-bold, high-contrast, structured typographic hierarchy.
- **Body / Biomarker Data**: High readability, monospaced or structured tabular numbers for values and reference ranges.
- **Micro-labels / Metadata**: Uppercase, small size (0.75rem), muted slate (`#64748B`), tracking +0.5px.

---

## UI Components & Layout Guidelines

1. **Pipeline Visualizer**:
   - Sequential numbered steps showing current stage pulse, past steps in green, future steps in muted gray.
2. **Stat & Biomarker Cards**:
   - Clean, border-first cards with subtle shadow (`0 1px 3px rgba(0,0,0,0.05)`).
   - High contrast status pills:
     - `badge-normal`: `#DEF7EC` bg with `#03543F` text
     - `badge-high`: `#FDE8E8` bg with `#9B1C1C` text
     - `badge-low`: `#E1EFFE` bg with `#1E429F` text
3. **Doctor Brief & Report Formatting**:
   - Medical memo style: structured clinical notes, clear bulleted directives, no conversational filler in clinical exports.
