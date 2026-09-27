import os
import sys
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# Add scratch to path
sys.path.append(os.path.dirname(__file__))
from build_all_team_docs import (
    add_header_footer, add_cover_block, add_section_header,
    add_subheading, add_body_p, add_bullet, add_callout_box,
    add_qa_pair, add_common_every_member_should_know, add_common_flow_box,
    COLOR_NAVY, COLOR_ARCTIC, COLOR_ARCTIC_DARK, HEX_OFF_WHITE, HEX_ARCTIC, HEX_MINT, HEX_YELLOW
)

def generate_doc_1(output_paths):
    doc = docx.Document()
    add_header_footer(doc, "Team Lead + ML & Data Engineer")
    
    # Title Cover Block
    add_cover_block(
        doc,
        "Team Lead + ML & Data Engineer",
        "System Architecture, Data Pipelines, ML Demand Forecasting, Historical Backtesting & Team Leadership Notes"
    )
    
    # 1. WHAT I DID
    add_section_header(doc, "1. What I Did (My Exact Technical Responsibilities)")
    add_bullet(doc, "Orchestrated overall system architecture across all 6 modules: Data, ML, Weather, Optimization, Backend, and Frontend.", "**Team Leadership:** ")
    add_bullet(doc, "Ingested Australian Antarctic Data Centre (AADC indicator_59) 30-year monthly electricity consumption (1993–2023) and ECMWF ERA5 hourly surface weather data for Mawson Station (-67.6027° S, 62.8738° E).", "**Dataset Pipeline:** ")
    add_bullet(doc, "Synthesized and physically calibrated hourly station load profiles against monthly historical actuals based on ambient temperature and seasonal base loads.", "**Data Calibration:** ")
    add_bullet(doc, "Engineered cyclical time features (sine/cosine of hour and day-of-year) and temporal demand/temperature lags (1h, 2h, 24h) to capture thermal inertia.", "**Feature Engineering:** ")
    add_bullet(doc, "Trained scikit-learn's `HistGradientBoostingRegressor` to predict hourly station electricity demand (kW).", "**ML Model Training:** ")
    add_bullet(doc, "Enforced a strict chronological 80/20 train/test split: Train (Jan 02 – Oct 20, 2023, 6,988 hours) vs. Unseen Test (Oct 21 – Dec 31, 2023, 1,748 hours, 72 days) with zero future-data leakage.", "**Validation Framework:** ")
    add_bullet(doc, "Connected predicted demand directly into the SciPy HiGHS linear programming optimizer as equality power conservation constraints.", "**Optimizer Integration:** ")

    # 2. HOW IT WORKS
    add_section_header(doc, "2. How It Works (Technical Architecture & Flow)")
    add_common_flow_box(doc)
    
    add_subheading(doc, "Detailed ML Pipeline Flow:")
    add_callout_box(doc, "ML PREDICTION & OPTIMIZATION PIPELINE", [
        "Historical Data (AADC monthly electricity + ERA5 hourly weather)",
        "        ↓",
        "Data Cleaning & Feature Engineering (Lags: 1h, 2h, 24h | Cyclical: sin/cos hour, day-of-year)",
        "        ↓",
        "HistGradientBoostingRegressor Model Training (80% Chronological split, 6,988 hours)",
        "        ↓",
        "Hourly Demand Prediction P_demand(t) (kW)",
        "        ↓",
        "Unseen Test Validation (Oct 21 – Dec 31, 1,748 hours | MAE: 1.25 kW vs Baseline 1.60 kW)",
        "        ↓",
        "Linear Equality Constraint fed to SciPy HiGHS Optimizer"
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)
    
    add_body_p(doc, "**Difference Between Prediction and Optimization:**", space_after=2)
    add_bullet(doc, "Takes ambient weather and temporal features and predicts **what the station electrical demand will be** (in kW). It does NOT decide how to supply the power.", "**ML Prediction:** ")
    add_bullet(doc, "Takes the ML predicted demand as an immutable target, examines wind, solar, battery state, and generator constraints, and decides **how to fulfill that demand at minimum diesel cost**.", "**HiGHS Optimization:** ")
    
    add_body_p(doc, "**Why Historical Unseen Testing is Backtesting (Crucial Clarity):**", space_after=2)
    add_bullet(doc, "The 20% validation split (Oct 21 – Dec 31, 2023) is historical backtesting. The model was trained ONLY on earlier months (Jan 02 – Oct 20) and evaluated on later months it had never seen. This proves the model's ability to generalize to unseen conditions.", "• ")
    add_bullet(doc, "It is **NOT** a three-month-ahead operational weather forecast. Operational forecasting is done in real-time over rolling 24h, 48h, and 72h horizons using live ECMWF weather feeds.", "• ")

    add_body_p(doc, "**Why HistGradientBoostingRegressor Was Selected:**", space_after=2)
    add_bullet(doc, "Handles non-linear relationships between ambient freezing temperatures, wind chill, and station heating demand without requiring artificial feature scaling.", "1. ")
    add_bullet(doc, "Native binning enables ultra-fast training (<1.5 seconds) and low runtime inference latency (<5 milliseconds), ideal for edge compute at isolated polar stations.", "2. ")
    add_bullet(doc, "Significantly outperformed linear models and matched LSTM neural networks on tabular time-series without the massive compute overhead, overfitting risk, or GPU requirements.", "3. ")

    # 3. WHAT TO SAY
    add_section_header(doc, "3. What to Say in Front of Judges (Verbatim Pitch Scripts)")
    add_callout_box(doc, "2-MINUTE TEAM LEAD OVERVIEW PITCH (ENGLISH)", [
        '"Respected Judges, Antarctic research stations like Mawson rely on diesel shipped once a year across treacherous pack ice at immense logistical cost and carbon footprint."',
        '"Polar Grid is an AI-assisted microgrid decision-support system. As Team Lead and ML Engineer, I orchestrated an end-to-end operational pipeline combining three core engines:"',
        '"First, our ML model predicts station electricity demand using temperature, katabatic wind conditions, and cyclical time features."',
        '"Second, our weather physics module converts live ECMWF Numerical Weather Predictions into expected wind and solar generation."',
        '"Third, our SciPy HiGHS linear programming optimizer computes an exact, hour-by-hour battery charge/discharge and generator dispatch schedule for rolling 24 to 72-hour horizons."',
        '"We validated our model on 72 unseen historical days, achieving a 1.25 kW mean absolute error—a 22.1% improvement over persistence baselines, safely saving projected annual diesel fuel by 41.45%."'
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    add_callout_box(doc, "HINDI / HINGLISH EXPLANATION (FOR CASUAL CONVERSATION)", [
        '"Polar Grid basically ek smart energy brain hai Antarctic research station ke liye."',
        '"Mawson Station pe diesel bohot mehenga aur dangerous logistics ke saath transport hota hai. Humne historical 30-year AADC electricity data aur ERA5 weather data use karke ek machine learning model train kiya hai jo exact electricity demand predict karta hai."',
        '"Yeh predicted demand aur live ECMWF weather forecast hamare HiGHS linear programming optimizer me jaata hai, jo station battery aur diesel generator ka optimal schedule banaata hai taaki diesel fuel consumption minimum ho aur bijli 100% reliable rahe."'
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    # 4. JUDGE QUESTIONS & ANSWERS
    add_section_header(doc, "4. Common Judge Questions & Simple Answers")
    add_qa_pair(doc, 1, "Where did you get electricity data for Mawson Station?", 
                "We obtained official monthly historical electrical consumption records from the Australian Antarctic Data Centre (AADC indicator_59 dataset) spanning 30 years (1993–2023). Because sub-hourly smart meters are not publicly exported, hourly load profiles were physically synthesized and calibrated to exactly match the monthly sums and thermal diurnal variations.")
    
    add_qa_pair(doc, 2, "What features does your ML model use to predict demand?", 
                "It uses ambient temperature, wind speed, cyclical temporal features (sine and cosine of hour-of-day and day-of-year), and lag features (demand from 1 hour ago, 2 hours ago, and 24 hours ago). Temperature and lags capture the station's building thermal inertia.")
    
    add_qa_pair(doc, 3, "Why didn't you use an LSTM or Transformer?", 
                "For tabular time-series with strong weather correlation, tree-based gradient boosted models (HistGradientBoosting) consistently outperform or match deep neural networks, while training in less than 2 seconds with zero GPU requirements. At an Antarctic station, lightweight models that can retrain on a standard laptop are significantly more practical and reliable.")
    
    add_qa_pair(doc, 4, "How do you prove your model doesn't overfit?", 
                "We enforced a strict chronological split. We trained on the first 80% of the year (Jan 2 to Oct 20, 2023) and tested on the remaining 20% (Oct 21 to Dec 31, 2023). We never shuffled timestamps, which eliminated any possibility of future-data leakage.")
    
    add_qa_pair(doc, 5, "What is the accuracy of your model?", 
                "Across the 1,748 unseen test hours, the Mean Absolute Error was 1.25 kW against an average demand of ~55 kW. This beats the standard persistence baseline (1.60 kW) by 22.1%. On the dashboard, judges can inspect every single one of the 72 test days individually.")

    # 5. POSSIBLE CROSS QUESTIONS
    add_section_header(doc, "5. Difficult Cross Questions & Safe Honest Answers")
    add_qa_pair(doc, 1, "If AADC data is monthly, how can you claim your hourly ML model is accurate to 1.25 kW?", 
                "That is an insightful observation. We are 100% transparent: AADC publishes official monthly electrical consumption totals. We modeled hourly demand by incorporating temperature-dependent heating curves and human occupancy schedules, calibrated so monthly integrals match AADC records. Our 1.25 kW MAE demonstrates that our ML model accurately captures the physical thermal and temporal dynamics of this calibrated profile.", is_cross=True)
    
    add_qa_pair(doc, 2, "What happens if your demand prediction is wrong by 10 kW during a blizzard?", 
                "Our HiGHS optimizer operates on rolling horizons with safety buffers. Furthermore, our system enforces a 300 kWh battery storage reserve and maintains 3 × 125 kW diesel generators on standby. If actual load exceeds prediction, the battery buffer absorbs the difference immediately, or the automated dispatch triggers diesel backup. The station never suffers a blackout.", is_cross=True)
    
    add_qa_pair(doc, 3, "Did you use weather data from the future when testing your model?", 
                "Absolutely not. In our chronological backtest, only historical observations prior to the test window were used for training. For operational forecasting, only forward-looking ECMWF numerical weather predictions are used as inputs.", is_cross=True)

    # 6. LIMITATIONS
    add_section_header(doc, "6. Limitations (Be Honest With Judges)")
    add_bullet(doc, "Historical hourly demand was physically synthesized based on monthly AADC reporting, as real-time smart meter telemetry is restricted by the Australian Antarctic Division.", "1. Synthesized Hourly Load: ")
    add_bullet(doc, "Polar Grid currently provides hour-ahead advisory dispatch schedules; it does not interface directly with physical SCADA switchgear or control sub-second generator governor frequencies.", "2. Advisory Dispatch Only: ")
    add_bullet(doc, "Thermal building shell insulation was treated as constant throughout the year, without accounting for variable snow accumulation on exterior building surfaces.", "3. Building Physics Assumptions: ")

    # 7. 30-SECOND ANSWER
    add_section_header(doc, "7. 30-Second Answer: What Did You Contribute?")
    add_callout_box(doc, "SAY THIS IF ASKED: 'WHAT DID YOU PERSONALLY DO?'", [
        '"As Team Lead and ML Engineer, I designed the overall architecture connecting data, ML, weather, and optimization into a unified pipeline. I processed 30 years of AADC station electricity records and ERA5 weather data, engineered cyclical and lag features, trained the HistGradientBoosting demand prediction model with strict chronological splitting, and connected the predicted demand into the HiGHS dispatch optimizer. I also led team integration to ensure all 6 modules function cohesively."'
    ], bg_hex=HEX_MINT, border_hex=HEX_ARCTIC)

    # 8. EVERY MEMBER SHOULD KNOW
    add_common_every_member_should_know(doc)
    
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Saved: {path}")

if __name__ == "__main__":
    out1 = r"c:\Users\Acer\Desktop\PolarGrid\docs\team_prep\01_Team_Lead_ML_Data_Notes.docx"
    out2 = r"c:\Users\Acer\Desktop\PolarGrid\docs\01_Team_Lead_ML_Data_Notes.docx"
    generate_doc_1([out1, out2])
