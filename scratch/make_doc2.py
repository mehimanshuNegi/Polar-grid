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

def generate_doc_2(output_paths):
    doc = docx.Document()
    add_header_footer(doc, "Weather & Renewable Energy Engineer")
    
    add_cover_block(
        doc,
        "Weather & Renewable Energy Engineer",
        "ECMWF Weather Ingestion, Turbine Aerodynamics, PV Physics & Seasonal Microgrid Generation Modeling"
    )
    
    # 1. WHAT I DID
    add_section_header(doc, "1. What I Did (My Exact Technical Responsibilities)")
    add_bullet(doc, "Designed and implemented the weather data ingestion pipeline combining historical ERA5 reanalysis and live operational ECMWF IFS feeds.", "**Weather Pipeline:** ")
    add_bullet(doc, "Integrated the Open-Meteo REST API to query real-time ECMWF IFS 9km numerical weather forecasts for Mawson Station coordinates (-67.6027° S, 62.8738° E).", "**Live API Integration:** ")
    add_bullet(doc, "Formulated the aerodynamic physical conversion from 10-meter wind speeds to electrical power output for Mawson's 2 × 100 kW wind turbines.", "**Wind Physics Modeling:** ")
    add_bullet(doc, "Formulated the physical photovoltaic conversion from global horizontal irradiance to electrical power for the 100 kW solar array, accounting for temperature coefficients and snow albedo reflection.", "**Solar Physics Modeling:** ")
    add_bullet(doc, "Modeled extreme Antarctic seasonal regimes: 24-hour austral summer daylight vs. continuous dark polar night (zero solar irradiance).", "**Seasonal Benchmarks:** ")
    add_bullet(doc, "Implemented automated fallback handling to cached historical seasonal benchmarks if external satellite or internet connectivity drops.", "**Fallback Architecture:** ")
    add_bullet(doc, "Structured renewable generation arrays and passed them directly to the HiGHS optimizer as renewable availability constraints.", "**Optimizer Hand-off:** ")

    # 2. HOW IT WORKS
    add_section_header(doc, "2. How It Works (Weather Ingestion & Renewable Physics)")
    
    add_callout_box(doc, "CRUCIAL HONESTY STATEMENT (MEMORIZE THIS)", [
        '"ECMWF provides the numerical weather prediction. Polar Grid uses that forecast to estimate renewable generation."',
        'We do NOT predict the weather ourselves. Predicting global atmospheric physics requires supercomputers. We take the world-leading ECMWF weather forecast and convert ambient physical conditions into expected kilowatt generation.'
    ], bg_hex=HEX_YELLOW, border_hex=HEX_ARCTIC)

    add_subheading(doc, "Live Weather Variables Ingested:")
    add_bullet(doc, "Wind Speed at 10m height (m/s) — primary driver of wind turbine generation.", "1. ")
    add_bullet(doc, "Direct & Diffuse Solar Radiation (W/m²) — GHI determining solar panel harvest.", "2. ")
    add_bullet(doc, "Ambient 2-meter Air Temperature (°C) — determines air density corrections and PV cell efficiency.", "3. ")

    add_subheading(doc, "Wind Generation Mathematical Physics (2 × 100 kW Turbines):")
    add_body_p(doc, "Mawson Station operates two 100 kW wind turbines (200 kW total capacity). Generation follows a piecewise cubic aerodynamic power curve:")
    add_bullet(doc, "Wind Speed < 3.0 m/s: Power = 0.0 kW (Insufficient torque to overcome friction).", "• Cut-in: ")
    add_bullet(doc, "3.0 m/s ≤ Wind Speed < 11.5 m/s: Power increases cubically: P(v) = P_rated × ((v - v_cutin) / (v_rated - v_cutin))³.", "• Cubic Region: ")
    add_bullet(doc, "11.5 m/s ≤ Wind Speed ≤ 25.0 m/s: Power output reaches rated maximum capacity (100 kW per turbine = 200 kW total).", "• Rated Plateau: ")
    add_bullet(doc, "Wind Speed > 25.0 m/s: Power = 0.0 kW (Mechanical aerodynamic brakes engage to prevent catastrophic blade destruction during blizzards).", "• Storm Cut-out: ")
    add_bullet(doc, "Antarctic freezing air (-15°C) has higher density than standard air (+15°C), generating up to 10–12% more kinetic power per cubic meter.", "• Air Density Adjustment: ")

    add_subheading(doc, "Solar Generation Physics (100 kW Solar Array):")
    add_body_p(doc, "Solar generation follows the standard physical semiconductor photovoltaic equation:")
    add_bullet(doc, "Formula: P_solar = P_rated × (G / 1000 W/m²) × [1 + γ × (T_cell - 25°C)] × η_snow.", "• ")
    add_bullet(doc, "Where G is global irradiance (W/m²), γ is cell temperature coefficient (-0.38%/°C, meaning cold Antarctic temperatures actually improve panel voltage and efficiency!), and η_snow accounts for high snow albedo reflection (~0.80).", "• ")

    add_subheading(doc, "Seasonal Extremes:")
    add_bullet(doc, "Continuous 24-hour sunlight. Solar delivers steady daytime peaks and nighttime trickle. Wind provides complementary power, achieving up to 60–80% clean energy shares.", "**Austral Summer (Dec–Jan):** ")
    add_bullet(doc, "Solar radiation equals exactly 0.0 W/m² for months. Solar power is completely zero. The microgrid operates solely on coastal wind generation, battery storage buffering, and automated diesel backup.", "**Polar Night (May–July):** ")

    # 3. WHAT TO SAY
    add_section_header(doc, "3. What to Say in Front of Judges (Verbatim Pitch Scripts)")
    add_callout_box(doc, "2-MINUTE WEATHER & RENEWABLES PITCH (ENGLISH)", [
        '"Respected Judges, renewable energy in Antarctica is 100% dependent on extreme meteorological conditions."',
        '"As the Weather & Renewable Energy Engineer, I built the pipeline that ingests live numerical weather predictions from ECMWF IFS and converts them into physical wind and solar power generation."',
        '"We ingest 10-meter wind speed, solar irradiance, and ambient temperature via the Open-Meteo API for rolling 24 to 72-hour planning horizons."',
        '"For wind generation, I implemented the aerodynamic power curve for Mawson\'s two 100 kW turbines, including cut-in, cubic power, rated plateau, and 25 m/s blizzard cut-out protection, adjusted for cold air density."',
        '"For solar, our model incorporates temperature coefficients and snow albedo gains. Crucially, during Polar Night, when solar drops to zero, our model cleanly informs the optimizer to rely on wind, battery reserves, and diesel backup."',
        '"If the satellite feed ever disconnects, our system automatically falls back to cached historical benchmarks, ensuring zero operational blackout."'
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    # 4. JUDGE QUESTIONS & ANSWERS
    add_section_header(doc, "4. Common Judge Questions & Simple Answers")
    add_qa_pair(doc, 1, "Does Polar Grid predict the weather?", 
                "No, and that is by design. Global numerical weather forecasting requires atmospheric supercomputers. We ingest live weather forecasts directly from the European Centre for Medium-Range Weather Forecasts (ECMWF IFS 9km model) via Open-Meteo. Our job is converting that atmospheric forecast into physical wind and solar generation kilowatts.")
    
    add_qa_pair(doc, 2, "What happens to your solar panels during Polar Night?", 
                "During Polar Night (May to July), the sun never rises above the horizon, so solar radiation is exactly 0.0 W/m². Our physics engine outputs 0.0 kW solar generation. The microgrid smoothly shifts load supply to coastal wind turbines, battery storage, and diesel backup without any software crash or power disruption.")
    
    add_qa_pair(doc, 3, "What happens if wind speed exceeds 25 m/s during a katabatic storm?", 
                "Wind turbines cannot operate in extreme gale conditions because aerodynamic drag would destroy the blades and generator gearbox. Our model enforces storm cut-out protection: at 25.0 m/s (~90 km/h), turbine output drops to 0.0 kW as mechanical brakes engage, and the system prompts diesel and battery to pick up the load.")
    
    add_qa_pair(doc, 4, "How do freezing temperatures affect solar panel efficiency?", 
                "Silicon solar panels actually perform better in the cold! Silicon has a negative temperature coefficient (approx -0.38% per degree above 25°C). In freezing Antarctic temperatures (-10°C to -20°C), open-circuit voltage rises, making the panels roughly 10–15% more efficient per watt of sunlight compared to a hot desert installation.")

    # 5. POSSIBLE CROSS QUESTIONS
    add_section_header(doc, "5. Difficult Cross Questions & Safe Honest Answers")
    add_qa_pair(doc, 1, "What happens if satellite internet fails and you can't reach the Open-Meteo API?", 
                "We designed an automated fail-safe fallback. If the API request times out or returns an HTTP error, our backend catches the exception, switches to cached seasonal ERA5 benchmark weather data, and alerts the operator on the dashboard with a clear 'CACHED WEATHER' status badge. The microgrid continues optimizing safely.", is_cross=True)
    
    add_qa_pair(doc, 2, "How do you account for weather forecast uncertainty?", 
                "Weather forecasts naturally become less certain over 48 and 72 hours compared to the next 24 hours. Because Polar Grid re-runs its rolling schedule every hour as new ECMWF updates arrive, any near-term error is corrected before dispatch decisions are executed. Additionally, our optimizer preserves a minimum battery state-of-charge safety buffer (20%) to absorb short-term renewable fluctuations.", is_cross=True)
    
    add_qa_pair(doc, 3, "Do you model snow accumulation covering solar panels?", 
                "In our physical formula, we include an average snow coverage loss factor (η_snow = 0.85). In real Antarctic stations, panels are tilted vertically (70° to 90°) to catch low polar sun angles and allow snow to slide off under gravity and high wind scouring. Future work will integrate optical camera sensors to detect physical panel snow coverage.", is_cross=True)

    # 6. 30-SECOND ANSWER
    add_section_header(doc, "6. 30-Second Answer: What Did You Contribute?")
    add_callout_box(doc, "SAY THIS IF ASKED: 'WHAT DID YOU PERSONALLY DO?'", [
        '"I developed the weather ingestion and renewable physics conversion modules. I integrated the Open-Meteo ECMWF live weather API, and formulated the aerodynamic power curves for Mawson\'s two 100 kW wind turbines—including air density adjustments and 25 m/s storm cut-outs—and the photovoltaic equations for the 100 kW solar array. I modeled the seasonal differences between 24-hour Austral Summer and zero-sun Polar Night, built the cached weather fallback mechanism, and passed renewable generation data into our HiGHS optimizer."'
    ], bg_hex=HEX_MINT, border_hex=HEX_ARCTIC)

    # 7. EVERY MEMBER SHOULD KNOW
    add_common_every_member_should_know(doc)
    
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Saved: {path}")

if __name__ == "__main__":
    out1 = r"c:\Users\Acer\Desktop\PolarGrid\docs\team_prep\02_Weather_Renewable_Notes.docx"
    out2 = r"c:\Users\Acer\Desktop\PolarGrid\docs\02_Weather_Renewable_Notes.docx"
    generate_doc_2([out1, out2])
