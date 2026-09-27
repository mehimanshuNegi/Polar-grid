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

def generate_doc_4(output_paths):
    doc = docx.Document()
    add_header_footer(doc, "Backend & API Engineer")
    
    add_cover_block(
        doc,
        "Backend & API Engineer",
        "FastAPI Server Architecture, REST Endpoints, Pipeline Orchestration & Fault-Tolerant Microservices"
    )
    
    # 1. WHAT I DID
    add_section_header(doc, "1. What I Did (My Exact Technical Responsibilities)")
    add_bullet(doc, "Built the asynchronous high-performance backend application using Python 3.11 and the FastAPI web framework.", "**Backend Server Framework:** ")
    add_bullet(doc, "Designed, implemented, and tested all 5 REST API endpoints powering the live dashboard, weather feeds, and validation screens.", "**REST API Design:** ")
    add_bullet(doc, "Orchestrated the pipeline integration connecting the trained ML model, Open-Meteo live weather client, and SciPy HiGHS linear solver into a synchronous request-response flow.", "**Pipeline Orchestration:** ")
    add_bullet(doc, "Configured static file mounting to serve the compiled Vite/React frontend directly from FastAPI on port 8000, eliminating CORS issues and simplifying remote tunnel deployment.", "**Single-Process Deployment:** ")
    add_bullet(doc, "Implemented automated exception handling, request timeouts, and graceful fallbacks to cached ERA5 data when external meteorological APIs are unreachable.", "**Fault Tolerance & Fallbacks:** ")
    add_bullet(doc, "Wrote and maintained automated backend unit tests in `tests/test_pipeline.py`, ensuring all 11 test cases pass in under 15 seconds.", "**Automated Testing:** ")

    # 2. HOW IT WORKS
    add_section_header(doc, "2. How It Works (Backend Architecture & Endpoints)")
    
    add_body_p(doc, "**Why is a Dedicated Backend Required?**", space_after=2)
    add_body_p(doc, "The machine learning models (scikit-learn), weather numerical calculations (numpy/pandas), and linear programming solvers (SciPy HiGHS) run in Python. A web browser cannot execute these heavy native computational C-libraries directly in JavaScript. The **FastAPI Backend** acts as the high-speed computational engine: the React frontend makes simple HTTP GET calls, the backend performs the heavy math in milliseconds, and returns clean JSON objects.", space_after=4)

    add_subheading(doc, "Verified Active API Endpoints in Polar Grid:")
    add_bullet(doc, "Returns Mawson Station coordinates (-67.6027° S, 62.8738° E), country (Australia AAD), operational status, and AADC baseline calibration notes.", "**1. GET /api/status:** ")
    add_bullet(doc, "Queries Open-Meteo for ECMWF IFS 9km hourly forecasts. Returns temperature, 10m wind speed, solar irradiance, and metadata (is_live flag, updated_at timestamp).", "**2. GET /api/weather/live?horizon=24:** ")
    add_bullet(doc, "Executes the complete operational pipeline. Ingests weather -> calls ML model for hourly demand -> solves HiGHS linear program -> returns hourly schedule (Demand, Wind, Solar, Battery, Diesel, SoC) and total diesel fuel saved.", "**3. GET /api/schedule?horizon=24&season=live:** ")
    add_bullet(doc, "Dynamically predicts station demand using the trained model on the requested historical validation date (out of 72 unseen days), returning 24 hourly records, predicted vs actual values, difference in kW, and match percentage.", "**4. GET /api/validation/day?date=YYYY-MM-DD:** ")
    add_bullet(doc, "Returns the complete statistical benchmark backtest metrics (MAE, baseline persistence error, percentage improvement) across the full 1,748 unseen test hours.", "**5. GET /api/validation:** ")

    add_subheading(doc, "Backend Data Flow Pipeline:")
    add_callout_box(doc, "REQUEST-RESPONSE PIPELINE FLOW", [
        "React Frontend (User clicks 48h horizon / Selects validation date)",
        "        ↓  (HTTP GET Request)",
        "FastAPI Router (main.py)",
        "        ↓",
        "Weather Engine (Fetches ECMWF IFS / Checks cache)",
        "        ↓",
        "ML Inference (HistGradientBoosting predicts P_demand)",
        "        ↓",
        "HiGHS Linear Solver (Optimizes battery & diesel dispatch)",
        "        ↓",
        "Pydantic Response Serialization (Converts numpy arrays to clean JSON)",
        "        ↓  (HTTP 200 OK Response)",
        "React Frontend (Renders SVG line charts, metrics cards, tables)"
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    # 3. WHAT TO SAY
    add_section_header(doc, "3. What to Say in Front of Judges (Verbatim Pitch Scripts)")
    add_callout_box(doc, "2-MINUTE BACKEND & API PITCH (ENGLISH)", [
        '"Respected Judges, the backend of Polar Grid is the computational engine connecting atmospheric physics and artificial intelligence to the user interface."',
        '"As the Backend & API Engineer, I built our asynchronous microservices using Python 3.11 and FastAPI."',
        '"Our backend exposes five dedicated REST endpoints. When an operator requests a 24, 48, or 72-hour operational schedule, our `/api/schedule` endpoint triggers a coordinated sequence in milliseconds: it fetches ECMWF numerical weather predictions, runs our scikit-learn model to predict hourly load, solves the HiGHS linear programming dispatch, and streams the structured JSON schedule back to the dashboard."',
        '"I implemented robust fault tolerance: if the external satellite weather API times out, our backend automatically falls back to cached ERA5 benchmarks without dropping requests."',
        '"Furthermore, I configured FastAPI to mount the production Vite bundle directly. This single-process deployment allows Polar Grid to run on port 8000 on any local research laptop or over secure encrypted tunnels with zero CORS friction."',
        '"Our automated test suite verifies all 11 backend and API pipeline functions in under 15 seconds."'
    ], bg_hex=HEX_OFF_WHITE, border_hex=HEX_ARCTIC)

    # 4. JUDGE QUESTIONS & ANSWERS
    add_section_header(doc, "4. Common Judge Questions & Simple Answers")
    add_qa_pair(doc, 1, "Why did you choose FastAPI over Flask or Django?", 
                "FastAPI is built on Starlette and Pydantic, offering modern asynchronous (async/await) request handling with speeds matching NodeJS and Go. It provides automatic data validation, built-in interactive OpenAPI documentation (/docs), and native type hints, which prevented data-format errors when passing large numpy arrays between ML models, optimizers, and the frontend.")
    
    add_qa_pair(doc, 2, "How does the backend communicate with the frontend?", 
                "Over standard REST HTTP requests using JSON. When the operator changes the planning horizon on the frontend, a simple `fetch('/api/schedule?horizon=48&season=live')` call is made. The backend computes the schedule and returns a lightweight JSON payload in less than 50 milliseconds.")
    
    add_qa_pair(doc, 3, "Where is your application hosted or deployed?", 
                "Polar Grid runs as a standalone Python process on port 8000. Because Antarctic research stations have isolated local area networks, our application can run completely offline on a station server or laptop. For remote judge evaluation and teammate sharing, we tunnel the local server securely using Cloudflare HTTP/2 tunnels.")
    
    add_qa_pair(doc, 4, "How do you handle external weather API failures?", 
                "We wrapped external weather API calls with 5-second timeout thresholds and try-except error handlers. If Open-Meteo is unreachable due to satellite link degradation, the backend catches the timeout exception, loads last-known cached ERA5 seasonal benchmark weather, and sets `is_live: false` in the metadata, alerting the frontend to display a 'CACHED WEATHER' badge.")

    # 5. POSSIBLE CROSS QUESTIONS
    add_section_header(doc, "5. Difficult Cross Questions & Safe Honest Answers")
    add_qa_pair(doc, 1, "Are your APIs vulnerable to CORS issues?", 
                "No. Because FastAPI directly mounts and serves the static production build (`dist/`) from the root directory (`/`), the frontend and backend share the exact same origin and port (8000). Relative API paths like `/api/schedule` are used, completely eliminating Cross-Origin Resource Sharing (CORS) preflight failures.", is_cross=True)
    
    add_qa_pair(doc, 2, "What database are you using to store telemetry?", 
                "For our working MVP, historical datasets (30-year AADC records and ERA5 hourly weather) and trained model artifacts are stored in optimized Parquet and joblib files on disk. In-memory caching provides microsecond access without database connection overhead. In a full production deployment, we would connect this API to a PostgreSQL/TimescaleDB time-series database.", is_cross=True)
    
    add_qa_pair(doc, 3, "How many requests per second can your backend handle?", 
                "Because inference with HistGradientBoosting and optimization with HiGHS take under 20 milliseconds combined, a single Uvicorn worker process easily handles 40–50 full schedule optimization requests per second. For an isolated Antarctic station with 20–50 research staff, this provides massive excess capacity.", is_cross=True)

    # 6. LIMITATIONS
    add_section_header(doc, "6. Limitations (Be Honest With Judges)")
    add_bullet(doc, "Telemetry data is currently read from structured CSV and Parquet archives rather than a live operational SCADA OPC-UA server.", "1. No Live SCADA Integration: ")
    add_bullet(doc, "The API currently uses HTTP GET polling rather than bidirectional WebSockets, which is sufficient for 1-hour rolling updates but not real-time sub-second streaming.", "2. HTTP Polling vs WebSockets: ")
    add_bullet(doc, "Authentication is currently omitted in the MVP to facilitate friction-free judge evaluation; enterprise role-based access control (RBAC) would be required for actual station commissioning.", "3. Open API Access: ")

    # 7. 30-SECOND ANSWER
    add_section_header(doc, "7. 30-Second Answer: What Did You Contribute?")
    add_callout_box(doc, "SAY THIS IF ASKED: 'WHAT DID YOU PERSONALLY DO?'", [
        '"I developed the complete backend server architecture using Python 3.11 and FastAPI. I built and tested all five REST API endpoints—including `/api/status`, `/api/weather/live`, `/api/schedule`, and `/api/validation/day`. I orchestrated the pipeline connecting our ML demand model, weather API, and HiGHS optimizer into sub-50-millisecond responses, implemented automated cached fallbacks for network dropouts, configured single-process static frontend hosting on port 8000, and maintained our automated 11-test verification suite."'
    ], bg_hex=HEX_MINT, border_hex=HEX_ARCTIC)

    # 8. EVERY MEMBER SHOULD KNOW
    add_common_every_member_should_know(doc)
    
    for path in output_paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        doc.save(path)
        print(f"Saved: {path}")

if __name__ == "__main__":
    out1 = r"c:\Users\Acer\Desktop\PolarGrid\docs\team_prep\04_Backend_API_Notes.docx"
    out2 = r"c:\Users\Acer\Desktop\PolarGrid\docs\04_Backend_API_Notes.docx"
    generate_doc_4([out1, out2])
