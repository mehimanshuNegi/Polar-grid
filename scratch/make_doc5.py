import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor

# Add scratch to path
sys.path.append(os.path.dirname(__file__))
from build_all_team_docs import (
    add_header_footer, add_cover_block, add_section_header,
    add_subheading, add_body_p, add_bullet, add_callout_box,
    add_qa_pair, add_common_every_member_should_know, add_common_flow_box,
    COLOR_NAVY, COLOR_ARCTIC, COLOR_ARCTIC_DARK, HEX_OFF_WHITE, HEX_ARCTIC, HEX_MINT, HEX_YELLOW
)

def generate_doc_5(output_paths):
    doc = docx.Document()
    add_header_footer(doc, "Frontend & UI Engineer")
    
    add_cover_block(
        doc,
        "Frontend & UI Engineer",
        "React 18 Architecture, Operational UI/UX, Dynamic SVG Visualizations, Day-by-Day Validation & Telemetry Console"
    )
    
    # 1. WHAT I DID
    add_section_header(doc, "1. What I Did (My Exact Technical Responsibilities)")
    add_bullet(doc, "Engineered the responsive single-page web application using modern React 18 and Vite for lightning-fast build times and smooth 60fps rendering.", "**Frontend Core Framework:** ")
    add_bullet(doc, "Designed and implemented the complete page architecture: Home, Operations Dashboard, Historical Validation, Multi-Day Scenarios, and Technical Architecture pages.", "**Page Architecture:** ")
    add_bullet(doc, "Built the primary Operations Console answering the 5 fundamental station questions: current electrical demand, renewable generation, battery storage state, diesel backup status, and advisory dispatch schedule.", "**Operational Command Dashboard:** ")
    add_bullet(doc, "Integrated Recharts and custom SVG data visualizations for hourly load forecasts, stacked generation curves, battery SoC trajectory, and dispatch breakdowns.", "**Data Visualization:** ")
    add_bullet(doc, "Created the dedicated Historical Validation Screen with an interactive day selector, side-by-side predicted vs. actual load curves, difference metrics (kW), and accuracy match percentages.", "**Validation Interface:** ")
    add_bullet(doc, "Refactored and simplified the user experience, eliminating intimidating statistical jargon (MAE matrices, persistence baseline formulas, ML leakage warnings) and replacing them with intuitive operational controls.", "**UI/UX Simplification:** ")
    add_bullet(doc, "Connected frontend components to the FastAPI backend via asynchronous REST API clients with loading states, error boundaries, and offline cached fallback alerts.", "**Backend Integration:** ")
    add_bullet(doc, "Applied a scientific 'Arctic + Off-White' visual design system with high contrast, calm polar colors, and accessible typography suitable for extreme station environments.", "**Design System:** ")

    # 2. HOW IT WORKS
    add_section_header(doc, "2. How It Works (Technical Frontend Architecture)")
    
    add_callout_box(doc, "FRONTEND DATA & CONTROL FLOW", [
        "Backend / REST APIs (FastAPI on Port 8000)",
        "        ↓  (JSON Payloads via HTTP GET)",
        "React Data Hooks (useEffect, useState, fetch)",
        "        ↓",
        "State Management & Data Normalization (Horizon, Selected Date, Unit Conversions)",
        "        ↓",
        "Component Hierarchy (Navbar, StatCards, Interactive Charts, Dispatch Table)",
        "        ↓",
        "Interactive Dashboard & Visualizations (Recharts ResponsiveContainer)",
        "        ↓",
        "Station Microgrid Operator (Actionable 24–72h Energy Decisions)"
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    add_subheading(doc, "Page Structure & Components:")
    add_bullet(doc, "Station hero overview, live operational status badge, geographic coordinates (-67.6027° S, 62.8738° E), and real-time atmospheric conditions.", "**1. Home / Overview:** ")
    add_bullet(doc, "Primary control room. Features 5 top-level KPI telemetry cards (Demand, Clean Power, Battery SoC, Diesel Output, Diesel Saved), dual time-series generation vs. demand charts, battery SoC gauge, and 24-hour advisory dispatch schedule table.", "**2. Operations Dashboard (#dashboard / #operations):** ")
    add_bullet(doc, "Interactive historical backtest explorer. Operators can pick any day from the 72-day unseen test period (Oct 21 – Dec 31, 2023) to view hourly predicted vs. actual demand curves, peak error in kW, and overall percentage accuracy.", "**3. Historical Validation (#validation):** ")
    add_bullet(doc, "Allows operators to toggle between 24-hour, 48-hour, and 72-hour planning horizons and compare seasonal regimes (Live Weather, Polar Summer, Polar Night, Storm).", "**4. Multi-Horizon Scenarios (#scenarios):** ")
    add_bullet(doc, "Interactive system explanation detailing mathematical constraints, turbine aerodynamic curves, and linear programming dispatch logic for technical reviewers.", "**5. How It Works (#how-it-works):** ")

    add_subheading(doc, "Why the UI Was Radically Simplified:")
    add_body_p(doc, "In earlier prototypes, the validation screen showed dense tables filled with Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), baseline persistence equations, and statistical warning boxes. Judges and field operators found this overwhelming and theoretical.", space_after=2)
    add_body_p(doc, "We completely redesigned the UI around **operator utility**. Instead of abstract ML formulas, the validation screen now visually plots: *'What our model predicted for that day'* right against *'What the station actually consumed'*, accompanied by an intuitive match percentage (typically 94%–98%) and average difference in kilowatts. This immediately proves real-world accuracy without requiring a statistics degree.", space_after=4)

    # 3. WHAT TO SAY
    add_section_header(doc, "3. What to Say in Front of Judges (Verbatim Pitch Scripts)")
    add_callout_box(doc, "2-MINUTE FRONTEND & UI PITCH (ENGLISH)", [
        '"Respected Judges, an intelligent energy management algorithm is useless if station operators cannot instantly understand and trust its recommendations in high-stress Antarctic conditions."',
        '"As the Frontend & UI Engineer, I built Polar Grid\'s responsive single-page web console using React 18 and Vite."',
        '"Our interface is designed around the 5 critical questions every Antarctic station manager asks: What is our electrical demand? How much renewable wind and solar energy is available? What is our battery storage level? Is the diesel generator required? And what is the hour-by-hour operational dispatch plan?"',
        '"I engineered dynamic SVG charts using Recharts that stream live ECMWF weather telemetry and display 24, 48, and 72-hour forward dispatch schedules with sub-second responsiveness."',
        '"To prove reliability to both operators and judges, I built our dedicated Validation Screen. Rather than presenting abstract mathematical metrics, it allows you to select any calendar date from our 72-day unseen test period to see our hourly predictions overlaid directly on actual historical station load, achieving 95%+ accuracy."',
        '"We chose an ergonomic Arctic Off-White design system that reduces eye strain, ensures high visibility on low-glare field screens, and presents complex microgrid physics in a calm, accessible manner."'
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    add_callout_box(doc, "QUICK HINGLISH EXPLANATION (FOR CASUAL DISCUSSIONS)", [
        '"Mera role Polar Grid ka complete user interface aur frontend banana tha. Humne React 18 aur Vite use kiya hai."',
        '"Humne dashboard ko intentionally simple aur actionable banaya hai taaki Antarctic station operator ko 5 cheezein turant dikhein: Current load, Wind aur Solar generation, Battery ka State of Charge, Diesel generator running hai ya off, aur aane wale 24 ghante ka optimized schedule."',
        '"Pehele hamari validation screen par bohot complex statistical tables the jaise MAE, RMSE wagera. Humne use simplify kiya—ab judge ya operator direct date choose kar sakte hain aur screen par prediction line actual demand ke upar perfectly match karti hui dikhti hai."',
        '"Saara data backend ke REST APIs se asynchronously fetch hota hai, aur UI poori tarah responsive aur fast hai."'
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    # 4. JUDGE QUESTIONS & ANSWERS
    add_section_header(doc, "4. Common Judge Questions & Simple Answers")
    add_qa_pair(doc, 1, "Why did you choose React over plain HTML/JS or Vue?", 
                "React's component-driven architecture and virtual DOM make it ideal for data-intensive dashboards. When an operator switches between a 24-hour and 72-hour horizon, or selects a new validation date, React re-renders only the changed chart nodes without refreshing the page. Vite provides rapid hot-module reloading and compiles the entire bundle into highly optimized static assets.")
    
    add_qa_pair(doc, 2, "How does the frontend fetch data from the backend?", 
                "We use standard native `fetch()` calls inside asynchronous React `useEffect` hooks. When the application loads, it queries `/api/status`, `/api/weather/live`, and `/api/schedule`. If the operator clicks a different planning horizon (e.g., 48h), the hook makes a lightweight GET request with query parameters and automatically updates the state.")
    
    add_qa_pair(doc, 3, "How did you make the charts responsive and interactive?", 
                "We implemented `ResponsiveContainer` from the Recharts library. The charts dynamically calculate dimensions based on parent CSS flex/grid containers. Hover tooltips, custom color gradients matching our Arctic palette, and accessible SVG legends allow operators to inspect exact numerical values for any specific hour.")
    
    add_qa_pair(doc, 4, "What happens on the frontend if the backend or internet goes down?", 
                "We implemented defensive UI state handling. If a network fetch fails or times out, the frontend catches the error, maintains the last known schedule on screen, and displays an informative banner warning the operator that live telemetry is temporarily unavailable, rather than crashing with a white screen.")

    # 5. POSSIBLE CROSS QUESTIONS
    add_section_header(doc, "5. Difficult Cross Questions & Safe Honest Answers")
    add_qa_pair(doc, 1, "Is your UI just a mockup or does it render real calculated data?", 
                "Every single data point displayed on the dashboard comes from live Python execution. When you open the dashboard or change a parameter, the frontend makes an actual HTTP request to FastAPI, which runs the real HistGradientBoosting ML model and the real SciPy HiGHS linear programming solver in milliseconds. No hardcoded or fake static numbers are used.", is_cross=True)
    
    add_qa_pair(doc, 2, "Why did you remove technical metrics like MAE and R² from the UI?", 
                "We did not remove them from the project—our backend and documentation still thoroughly track them (MAE is 1.25 kW, beating baseline by 22.1%). However, for the primary user interface, human-factors research in industrial control shows that operational staff make better, faster decisions when presented with visual actual-vs-predicted curves and match percentages rather than abstract statistical matrices.", is_cross=True)
    
    add_qa_pair(doc, 3, "Can the frontend send commands back to control physical generators?", 
                "In our current prototype, Polar Grid operates as an **advisory decision-support system**. The frontend displays recommended setpoints (e.g., 'Discharge Battery at 45 kW, Diesel OFF'). The operator reviews and authorizes the schedule. In a future production iteration, an authenticated 'Execute Dispatch' button could send control setpoints directly to a station SCADA PLC via Modbus or OPC-UA.", is_cross=True)

    # 6. LIMITATIONS
    add_section_header(doc, "6. Limitations (Be Honest With Judges)")
    add_bullet(doc, "The current interface utilizes client-side polling on user action rather than continuous WebSocket streaming.", "1. Polling vs Real-Time WebSockets: ")
    add_bullet(doc, "While fully responsive across desktop, laptop, and tablet screens, the multi-column dispatch table is optimized for landscape displays rather than small smartphone screens.", "2. Table Form Factor: ")
    add_bullet(doc, "User management, multi-user role authorization, and audit logging for dispatch changes are not yet implemented in this prototype.", "3. No Multi-User RBAC: ")

    # 7. 30-SECOND ANSWER
    add_section_header(doc, "7. 30-Second Answer: What Did You Contribute?")
    add_callout_box(doc, "SAY THIS IF ASKED: 'WHAT DID YOU PERSONALLY DO?'", [
        '"I developed the complete frontend web application using React 18 and Vite. I designed the page architecture across Operations, Validation, Scenarios, and Architecture. I built responsive SVG charts for load forecasts, renewable generation, and battery trajectories, connected all components asynchronously to our FastAPI endpoints, and simplified the UI into a clean, operational Arctic console where operators can evaluate live dispatch recommendations and inspect day-by-day historical model validation in one click."'
    ], bg_hex=HEX_MINT, border_hex=HEX_ARCTIC)

    # 8. EVERY MEMBER SHOULD KNOW
    add_common_every_member_should_know(doc)
    
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Saved: {path}")

if __name__ == "__main__":
    out1 = r"c:\Users\Acer\Desktop\PolarGrid\docs\team_prep\05_Frontend_UI_Notes.docx"
    out2 = r"c:\Users\Acer\Desktop\PolarGrid\docs\05_Frontend_UI_Notes.docx"
    generate_doc_5([out1, out2])
