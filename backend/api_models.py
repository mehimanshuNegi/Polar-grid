"""
Polar Grid: FastAPI Pydantic Models & Schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class StationCoordinates(BaseModel):
    latitude: float
    longitude: float

class StationMeta(BaseModel):
    name: str
    country: str
    coordinates: StationCoordinates
    description: str

class DispatchSummaryMetrics(BaseModel):
    time_horizon_hours: int
    total_demand_kwh: float
    renewable_energy_used_kwh: float
    diesel_energy_used_kwh: float
    battery_discharge_kwh: float
    battery_charge_kwh: float
    unmet_demand_kwh: float
    renewable_penetration_percent: float
    baseline_diesel_fuel_litres: float
    optimized_diesel_fuel_litres: float
    diesel_fuel_saved_litres: float
    diesel_reduction_percent: float
    season: Optional[str] = "summer"
    simulation_label: Optional[str] = None
    weather_source: Optional[str] = "ECMWF IFS"
    weather_mode: Optional[str] = "live"
    weather_updated_at: Optional[str] = None
    battery_state: Optional[str] = "NORMAL"
    initial_soc: Optional[float] = 0.50
    initial_simulated_soc_percent: Optional[float] = 50.0
    current_projected_soc_percent: Optional[float] = 50.0
    diesel_state: Optional[str] = "NORMAL"
    diesel_capacity_kw: Optional[float] = 375.0
    max_available_diesel_kw: Optional[float] = 375.0
    current_diesel_kw: Optional[float] = 0.0
    current_demand_kw: Optional[float] = 0.0
    current_wind_kw: Optional[float] = 0.0
    current_solar_kw: Optional[float] = 0.0
    current_battery_charge_kw: Optional[float] = 0.0
    current_battery_discharge_kw: Optional[float] = 0.0
    current_total_supply_kw: Optional[float] = 0.0
    current_unmet_demand_kw: Optional[float] = 0.0
    alerts: Optional[List[str]] = []
    annual_validated_reduction_percent: Optional[float] = 41.45
    annual_validated_note: Optional[str] = "Projected annual diesel reduction — 12-month simulation benchmark"
    simulation_note: Optional[str] = "Prototype assumption — not live Mawson BMS/SCADA telemetry."

class ScheduleRow(BaseModel):
    timestamp: str
    predicted_demand_kw: float
    solar_generation_kw: float
    wind_generation_kw: float
    renewable_used_kw: float
    battery_charge_kw: float
    battery_discharge_kw: float
    battery_soc_percent: float
    diesel_generation_kw: float
    diesel_fuel_litres: float
    curtailed_renewable_kw: float
    unmet_demand_kw: float

class ForecastPoint(BaseModel):
    timestamp: str
    actual_modeled_demand_kw: Optional[float] = None
    pred_modeled_demand_kw: float
    actual_wind_speed_ms: Optional[float] = None
    pred_wind_speed_ms: float
    actual_solar_radiation_wm2: Optional[float] = None
    pred_solar_radiation_wm2: float
    actual_temperature_celsius: Optional[float] = None
    pred_temperature_celsius: float

class WeatherPoint(BaseModel):
    timestamp: str
    temperature_celsius: float
    wind_speed_ms: float
    wind_direction_deg: float
    solar_radiation_wm2: float
    direct_radiation_wm2: float
    diffuse_radiation_wm2: float

class LiveWeatherResponse(BaseModel):
    source: str
    provider: str
    mode: str
    is_live: bool
    updated_at: str
    latitude: float
    longitude: float
    forecast_hours: int
    points: List[WeatherPoint]
    fallback_reason: Optional[str] = None

class DispatchRunRequest(BaseModel):
    horizon_hours: Optional[int] = 24
    season: Optional[str] = "summer" # "summer", "winter", or "live"
    initial_soc: Optional[float] = None
    battery_state: Optional[str] = "NORMAL" # "NORMAL", "LOW", "CRITICAL"
    diesel_state: Optional[str] = "NORMAL"   # "NORMAL", "LIMITED", "CRITICAL"
    solar_capacity_kw: Optional[float] = None
    wind_capacity_kw: Optional[float] = None
    battery_capacity_kwh: Optional[float] = None
    diesel_capacity_kw: Optional[float] = None
