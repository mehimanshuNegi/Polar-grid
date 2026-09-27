"""
Polar Grid: Renewable Generation Estimation Module
Physically grounded conversion of forecasted solar irradiance and wind velocity
into estimated electrical power output (kW).
"""

import os
import json
import numpy as np
import pandas as pd

class RenewableEstimator:
    def __init__(self, config_path: str = None):
        if config_path is None:
            self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "station_config.json"))
        else:
            self.config_path = os.path.abspath(config_path)
            
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.solar_cfg = self.config["solar_pv"]
        self.wind_cfg = self.config["wind_turbines"]

    def estimate_solar_power(self, irradiance_wm2: np.ndarray | pd.Series, temp_celsius: np.ndarray | pd.Series) -> np.ndarray:
        """
        Solar PV output model (kW):
        P_solar = P_cap * (G / G_stc) * [1 + gamma * (T_cell - 25)] * eta_inv
        Cold polar air increases photovoltaic efficiency.
        """
        G = np.maximum(0.0, np.asarray(irradiance_wm2, dtype=float))
        # Inverter activation threshold: Solar inverters require minimum threshold (~5 W/m2) to overcome standby tare
        G = np.where(G < 5.0, 0.0, G)
        T = np.asarray(temp_celsius, dtype=float)
        
        P_cap = self.solar_cfg["capacity_kw"]
        G_stc = self.solar_cfg["reference_irradiance_w_per_m2"]
        gamma = self.solar_cfg["temperature_coefficient_p_deg_c"]
        eta = self.solar_cfg["inverter_efficiency"]
        
        # Approximate cell temperature: T_cell ≈ T_ambient + 0.03 * G
        T_cell = T + 0.03 * G
        temp_factor = np.maximum(0.7, 1.0 + gamma * (T_cell - 25.0))
        
        raw_power = P_cap * (G / G_stc) * temp_factor * eta
        # Cap at inverter / nameplate rating
        return np.round(np.clip(raw_power, 0.0, P_cap), 2)

    def estimate_wind_power(self, wind_speed_ms: np.ndarray | pd.Series) -> np.ndarray:
        """
        Antarctic Wind Turbine piecewise power curve (kW):
        - Cut-in: 3.5 m/s
        - Rated: 12.0 m/s
        - Cut-out: 25.0 m/s (storm shutdown)
        """
        v = np.maximum(0.0, np.asarray(wind_speed_ms, dtype=float))
        
        P_total_cap = self.wind_cfg["total_capacity_kw"]
        v_in = self.wind_cfg["cut_in_speed_m_s"]
        v_rated = self.wind_cfg["rated_speed_m_s"]
        v_out = self.wind_cfg["cut_out_speed_m_s"]
        
        power = np.zeros_like(v)
        
        # Region 2: Between cut-in and rated (cubic power relationship)
        mask_ramp = (v >= v_in) & (v < v_rated)
        power[mask_ramp] = P_total_cap * ((v[mask_ramp]**3 - v_in**3) / (v_rated**3 - v_in**3))
        
        # Region 3: Between rated and cut-out (constant rated power)
        mask_rated = (v >= v_rated) & (v <= v_out)
        power[mask_rated] = P_total_cap
        
        # Region 4: Above cut-out (storm protection trip) -> 0 kW
        return np.round(np.clip(power, 0.0, P_total_cap), 2)

    def process_forecast_dataframe(self, df_forecast: pd.DataFrame) -> pd.DataFrame:
        """
        Appends estimated solar, wind, and total renewable generation columns
        to the forecast dataframe.
        """
        df = df_forecast.copy()
        
        # Determine whether to use actual or predicted weather columns
        irr_col = "pred_solar_radiation_wm2" if "pred_solar_radiation_wm2" in df.columns else "solar_radiation_wm2"
        temp_col = "pred_temperature_celsius" if "pred_temperature_celsius" in df.columns else "temperature_celsius"
        wind_col = "pred_wind_speed_ms" if "pred_wind_speed_ms" in df.columns else "wind_speed_ms"
        
        df["solar_generation_kw"] = self.estimate_solar_power(df[irr_col], df[temp_col])
        df["wind_generation_kw"] = self.estimate_wind_power(df[wind_col])
        df["total_renewable_available_kw"] = np.round(df["solar_generation_kw"] + df["wind_generation_kw"], 2)
        
        return df

if __name__ == "__main__":
    estimator = RenewableEstimator()
    sample_irr = np.array([0, 100, 500, 800])
    sample_temp = np.array([-15, -12, -10, -8])
    sample_wind = np.array([2.0, 7.5, 14.0, 26.0])
    
    sol = estimator.estimate_solar_power(sample_irr, sample_temp)
    wnd = estimator.estimate_wind_power(sample_wind)
    print("Test Solar Output (kW):", sol)
    print("Test Wind Output (kW):", wnd)
