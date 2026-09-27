"""
POLAR GRID — SIX SEPARATE TEAM PREPARATION DOCUMENTS GENERATOR
Theme: ARCTIC + OFF-WHITE
Generates 6 distinct, professional Word (.docx) preparation notes.
"""

import os
import re
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

# ==============================================================================
# COLOR CONSTANTS (ARCTIC + OFF-WHITE DESIGN SYSTEM)
# ==============================================================================
COLOR_NAVY = RGBColor(15, 45, 61)         # #0F2D3D (Headings & Primary Text)
COLOR_NAVY_MUTED = RGBColor(61, 90, 108)   # #3D5A6C (Secondary Text)
COLOR_ARCTIC = RGBColor(114, 176, 171)     # #72B0AB (Primary Accent)
COLOR_ARCTIC_DARK = RGBColor(74, 137, 132) # #4A8984 (Sub-headings)
COLOR_ICE_BLUE = RGBColor(188, 220, 220)   # #BCDCDC (Borders)
COLOR_WHITE = RGBColor(255, 255, 255)      # #FFFFFF
COLOR_MINT = RGBColor(15, 107, 86)         # #0F6B56 (Clean Energy text)
COLOR_CORAL = RGBColor(194, 74, 50)        # #C24A32 (Diesel/Alert text)

HEX_OFF_WHITE = "F8FBFD"
HEX_WHITE = "FFFFFF"
HEX_ARCTIC = "72B0AB"
HEX_ARCTIC_LIGHT = "EBF5F4"
HEX_ICE_BLUE = "BCDCDC"
HEX_MINT = "D1F2EB"
HEX_YELLOW = "FFEDD1"
HEX_BUBBLEGUM = "FDC1B4"

# ==============================================================================
# XML FORMATTING HELPERS
# ==============================================================================
def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)

def set_table_borders(table, border_hex=HEX_ICE_BLUE):
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="{border_hex}"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{border_hex}"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_hex}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

def add_header_footer(doc, title_short):
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)
        
        # Header
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run(f"POLAR GRID — {title_short.upper()} | SIH PREPARATION")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = COLOR_NAVY_MUTED
        
        # Footer
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
        frun1 = fp.add_run("Mawson Station, Antarctica (67.6027° S, 62.8738° E) • Confidential SIH Notes")
        frun1.font.name = "Calibri"
        frun1.font.size = Pt(8.5)
        frun1.font.color.rgb = COLOR_NAVY_MUTED

def add_cover_block(doc, role_title, subtitle):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    
    r_tag = p.add_run("ANTARCTIC MICROGRID DECISION SUPPORT SYSTEM • SIH 2024")
    r_tag.font.name = "Calibri"
    r_tag.font.size = Pt(9.5)
    r_tag.font.bold = True
    r_tag.font.color.rgb = COLOR_ARCTIC_DARK
    
    p_title = doc.add_paragraph()
    p_title.paragraph_format.space_before = Pt(2)
    p_title.paragraph_format.space_after = Pt(2)
    r_title = p_title.add_run(f"POLAR GRID — {role_title.upper()}")
    r_title.font.name = "Calibri"
    r_title.font.size = Pt(20)
    r_title.font.bold = True
    r_title.font.color.rgb = COLOR_NAVY
    
    p_sub = doc.add_paragraph()
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(14)
    r_sub = p_sub.add_run(subtitle)
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(11)
    r_sub.font.italic = True
    r_sub.font.color.rgb = COLOR_NAVY_MUTED
    
    # Divider bar
    p_div = doc.add_paragraph()
    p_div.paragraph_format.space_after = Pt(12)
    r_div = p_div.add_run("━" * 58)
    r_div.font.size = Pt(12)
    r_div.font.color.rgb = COLOR_ARCTIC

def add_section_header(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    
    r_dot = p.add_run("■ ")
    r_dot.font.name = "Calibri"
    r_dot.font.size = Pt(13)
    r_dot.font.color.rgb = COLOR_ARCTIC
    
    r_text = p.add_run(text.upper())
    r_text.font.name = "Calibri"
    r_text.font.size = Pt(13)
    r_text.font.bold = True
    r_text.font.color.rgb = COLOR_NAVY

def add_subheading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(11)
    r.font.bold = True
    r.font.color.rgb = COLOR_ARCTIC_DARK

def add_body_p(doc, text, bold_prefix=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Calibri"
        r_pre.font.bold = True
        r_pre.font.size = Pt(10)
        r_pre.font.color.rgb = COLOR_NAVY
    
    tokens = re.split(r'(\*\*.*?\*\*|`.*?`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            inner = token[2:-2]
            run = p.add_run(inner)
            run.font.name = "Calibri"
            run.font.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = COLOR_NAVY
        elif token.startswith("`") and token.endswith("`"):
            inner = token[1:-1]
            run = p.add_run(f" {inner} ")
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = COLOR_ARCTIC_DARK
        else:
            run = p.add_run(token)
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.color.rgb = COLOR_NAVY_MUTED

def add_bullet(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Calibri"
        r_pre.font.bold = True
        r_pre.font.size = Pt(10)
        r_pre.font.color.rgb = COLOR_NAVY
    
    tokens = re.split(r'(\*\*.*?\*\*|`.*?`)', text)
    for token in tokens:
        if not token:
            continue
        if token.startswith("**") and token.endswith("**"):
            inner = token[2:-2]
            run = p.add_run(inner)
            run.font.name = "Calibri"
            run.font.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = COLOR_NAVY
        elif token.startswith("`") and token.endswith("`"):
            inner = token[1:-1]
            run = p.add_run(f" {inner} ")
            run.font.name = "Consolas"
            run.font.size = Pt(9)
            run.font.color.rgb = COLOR_ARCTIC_DARK
        else:
            run = p.add_run(token)
            run.font.name = "Calibri"
            run.font.size = Pt(10)
            run.font.color.rgb = COLOR_NAVY_MUTED

def add_callout_box(doc, title, text_items, bg_hex=HEX_ARCTIC_LIGHT, border_hex=HEX_ARCTIC):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.8)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=120, bottom=120, left=160, right=160)
    
    # Border
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(f'''
        <w:tcBorders {nsdecls("w")}>
            <w:left w:val="single" w:sz="24" w:space="0" w:color="{border_hex}"/>
            <w:top w:val="single" w:sz="4" w:space="0" w:color="{HEX_ICE_BLUE}"/>
            <w:right w:val="single" w:sz="4" w:space="0" w:color="{HEX_ICE_BLUE}"/>
            <w:bottom w:val="single" w:sz="4" w:space="0" w:color="{HEX_ICE_BLUE}"/>
        </w:tcBorders>
    ''')
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    r_t = p.add_run(f"★  {title}")
    r_t.font.name = "Calibri"
    r_t.font.size = Pt(10.5)
    r_t.font.bold = True
    r_t.font.color.rgb = COLOR_NAVY
    
    for item in text_items:
        p_item = cell.add_paragraph()
        p_item.paragraph_format.space_after = Pt(2)
        p_item.paragraph_format.line_spacing = 1.15
        r_i = p_item.add_run(item)
        r_i.font.name = "Calibri"
        r_i.font.size = Pt(9.5)
        r_i.font.color.rgb = COLOR_NAVY_MUTED

def add_qa_pair(doc, q_num, question, answer, is_cross=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.keep_with_next = True
    
    prefix = f"Cross Q{q_num}: " if is_cross else f"Q{q_num}: "
    r_q = p.add_run(prefix + question)
    r_q.font.name = "Calibri"
    r_q.font.size = Pt(10)
    r_q.font.bold = True
    r_q.font.color.rgb = COLOR_CORAL if is_cross else COLOR_NAVY
    
    p_ans = doc.add_paragraph()
    p_ans.paragraph_format.left_indent = Inches(0.2)
    p_ans.paragraph_format.space_after = Pt(5)
    p_ans.paragraph_format.line_spacing = 1.15
    
    r_tag = p_ans.add_run("Answer: ")
    r_tag.font.name = "Calibri"
    r_tag.font.size = Pt(9.5)
    r_tag.font.bold = True
    r_tag.font.color.rgb = COLOR_ARCTIC_DARK
    
    r_ans = p_ans.add_run(answer)
    r_ans.font.name = "Calibri"
    r_ans.font.size = Pt(9.5)
    r_ans.font.color.rgb = COLOR_NAVY_MUTED

def add_common_every_member_should_know(doc):
    add_section_header(doc, "Every Team Member Should Know (Common Essentials)")
    add_body_p(doc, "Regardless of your specific role, you must be able to deliver crisp 1-line answers to these fundamental project questions if a judge asks you directly:")
    
    essentials = [
        ("What is Polar Grid?", "An AI-assisted microgrid decision-support system that predicts station electrical demand, forecasts wind/solar generation, and computes the optimal hour-by-hour battery/diesel dispatch schedule for Mawson Station, Antarctica."),
        ("What exact problem are we solving?", "Antarctic stations rely heavily on diesel fuel shipped once a year at immense logistical cost and emissions risk. Polar Grid maximizes clean renewable utilization to safely reduce unnecessary diesel burn."),
        ("What is the working MVP?", "A full-stack operational decision console deployed with a FastAPI backend, trained HistGradientBoosting demand regressor, ECMWF live weather feed, and SciPy HiGHS linear programming optimizer."),
        ("Where does live weather come from?", "Directly from the European Centre for Medium-Range Weather Forecasts (ECMWF IFS 9km) operational model via Open-Meteo API. Polar Grid does NOT forecast the weather itself; we ingest ECMWF's weather to estimate renewable generation."),
        ("What does the ML model predict?", "Hourly station electrical demand (kW) using ambient weather features and cyclical temporal patterns."),
        ("What does the optimizer do?", "SciPy HiGHS linear programming solver takes forecast demand and renewable availability to decide exact battery charge/discharge and diesel generator output to minimize diesel fuel consumption while enforcing 100% power reliability."),
        ("What happens during Polar Night?", "In polar winter (May–July), solar irradiance is 0.0 W/m². The microgrid operates solely on coastal wind generation, 300 kWh battery storage, and automated diesel backup without crashing."),
        ("How do we validate prediction accuracy?", "Strict historical backtest on 1,748 unseen test hours (Oct 21 – Dec 31, 2023, 72 days). The ML model achieved an MAE of 1.25 kW, beating baseline persistence by +22.1% with zero future-data leakage."),
        ("What is the biggest limitation?", "Historical electricity data is recorded monthly by AADC; our hourly demand profile is physically synthesized and calibrated to these monthly sums. Also, HiGHS provides hour-ahead advisory dispatch, not millisecond inverter switching."),
        ("What would we improve next?", "Deploy on-site IoT power meters for live sub-minute telemetry, incorporate multi-model weather ensembles, and add real-time degradation thermal modeling for battery packs.")
    ]
    
    for q, a in essentials:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = 1.15
        
        rq = p.add_run(f"• {q} ")
        rq.font.name = "Calibri"
        rq.font.size = Pt(9.5)
        rq.font.bold = True
        rq.font.color.rgb = COLOR_NAVY
        
        ra = p.add_run(a)
        ra.font.name = "Calibri"
        ra.font.size = Pt(9.5)
        ra.font.color.rgb = COLOR_NAVY_MUTED

def add_common_flow_box(doc):
    flow_items = [
        "Historical Station Data (AADC) + Historical Weather (ERA5)",
        "        ↓",
        "Data Processing & Feature Engineering (Lags, Cyclical Time)",
        "        ↓",
        "ML Demand Prediction (HistGradientBoostingRegressor)",
        "        ↓",
        "Live ECMWF Weather (Open-Meteo IFS 9km Numerical Weather)",
        "        ↓",
        "Wind + Solar Generation Estimation (Turbine cubic curve & PV physics)",
        "        ↓",
        "Energy Optimization (SciPy HiGHS Linear Programming Solver)",
        "        ↓",
        "Renewable + Battery + Diesel 24–72h Advisory Schedule",
        "        ↓",
        "Backend APIs (FastAPI)  →  React Operator Dashboard"
    ]
    add_callout_box(doc, "COMPLETE END-TO-END PROJECT DECISION FLOW", flow_items, bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

print("Helper functions initialized successfully.")
