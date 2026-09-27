"""
Polar Grid: Data Cleaning & Preprocessing Pipeline
Extracts, cleans, and standardizes Antarctic station meteorological and energy datasets.
"""

import os
import json
import zipfile
import urllib.request
import numpy as np
import pandas as pd
from datetime import datetime

class PolarDataPipeline:
    def __init__(self, project_root: str = None):
        if project_root is None:
            # default to current working directory or two levels up
            self.root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        else:
            self.root = os.path.abspath(project_root)
            
        self.raw_data_dir = os.path.join(self.root, "data", "raw")
        self.processed_data_dir = os.path.join(self.root, "data", "processed")
        self.config_path = os.path.join(self.root, "config", "station_config.json")
        self.raw_dataset_source_dir = os.path.join(self.root, "DataSet")
        
        os.makedirs(self.raw_data_dir, exist_ok=True)
        os.makedirs(self.processed_data_dir, exist_ok=True)
        
        with open(self.config_path, "r") as f:
            self.config = json.load(f)

    def extract_and_clean_station_energy_data(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extracts real monthly historical electricity and fuel usage for Mawson Station
        from DataSet/SOE_SFU.zip without altering the raw archive.
        """
        zip_path = os.path.join(self.raw_dataset_source_dir, "SOE_SFU.zip")
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"Source archive not found: {zip_path}")
            
        with zipfile.ZipFile(zip_path, 'r') as z:
            # 1. Electricity (indicator_59.csv)
            raw_59_bytes = z.read('indicator_59.csv')
            raw_59_path = os.path.join(self.raw_data_dir, "indicator_59_raw.csv")
            with open(raw_59_path, "wb") as f:
                f.write(raw_59_bytes)
                
            # Read indicator 59 (row 0 has title, row 1 has column headers)
            df_59_raw = pd.read_csv(raw_59_path, skiprows=1)
            # Filter Mawson Station
            df_59_mawson = df_59_raw[df_59_raw['Place'] == 'Mawson'].copy()
            df_59_mawson['Date'] = pd.to_datetime(df_59_mawson['Date'], format='%b-%y')
            df_59_mawson['Value'] = pd.to_numeric(df_59_mawson['Value'], errors='coerce')
            df_59_mawson = df_59_mawson.sort_values('Date').reset_index(drop=True)
            # Interpolate any missing values cleanly
            df_59_mawson['electricity_kwh'] = df_59_mawson['Value'].interpolate(method='linear')
            df_59_clean = df_59_mawson[['Date', 'electricity_kwh']].rename(columns={'Date': 'timestamp'})
            
            # 2. Generator Fuel Usage (indicator_56.csv)
            raw_56_bytes = z.read('indicator_56.csv')
            raw_56_path = os.path.join(self.raw_data_dir, "indicator_56_raw.csv")
            with open(raw_56_path, "wb") as f:
                f.write(raw_56_bytes)
                
            df_56_raw = pd.read_csv(raw_56_path, skiprows=1)
            df_56_mawson = df_56_raw[df_56_raw['Place'] == 'Mawson'].copy()
            df_56_mawson['Date'] = pd.to_datetime(df_56_mawson['Date'], format='%b-%y')
            df_56_mawson['Value'] = pd.to_numeric(df_56_mawson['Value'], errors='coerce')
            df_56_mawson = df_56_mawson.sort_values('Date').reset_index(drop=True)
            df_56_mawson['generator_fuel_litres'] = df_56_mawson['Value'].interpolate(method='linear')
            df_56_clean = df_56_mawson[['Date', 'generator_fuel_litres']].rename(columns={'Date': 'timestamp'})

        # Save cleaned monthly benchmarks
        df_59_clean.to_csv(os.path.join(self.processed_data_dir, "mawson_monthly_electricity.csv"), index=False)
        df_56_clean.to_csv(os.path.join(self.processed_data_dir, "mawson_monthly_fuel.csv"), index=False)
        
        return df_59_clean, df_56_clean

    def fetch_or_load_era5_hourly(self, start_date: str = "2023-01-01", end_date: str = "2023-12-31") -> pd.DataFrame:
        """
        Loads cached or fetches genuine ERA5 hourly reanalysis for Mawson Station coordinates
        (-67.6027, 62.8738) from the open ECMWF archive.
        """
        cache_path = os.path.join(self.raw_data_dir, f"mawson_era5_hourly_{start_date}_{end_date}.csv")
        if os.path.exists(cache_path):
            print(f"Loading cached ERA5 hourly weather from {cache_path}")
            df_era5 = pd.read_csv(cache_path)
            df_era5['timestamp'] = pd.to_datetime(df_era5['timestamp'])
            return df_era5
            
        lat = self.config["station"]["coordinates"]["latitude"]
        lon = self.config["station"]["coordinates"]["longitude"]
        url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&"
            f"hourly=temperature_2m,wind_speed_10m,wind_direction_10m,shortwave_radiation,direct_normal_irradiance,diffuse_radiation"
        )
        print(f"Fetching genuine ERA5 hourly weather for Mawson ({lat}, {lon}) from open reanalysis archive...")
        req = urllib.request.Request(url, headers={'User-Agent': 'PolarGrid-System/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            
        h = data["hourly"]
        df_era5 = pd.DataFrame({
            "timestamp": pd.to_datetime(h["time"]),
            "temperature_celsius": h["temperature_2m"],
            # Open-Meteo returns wind_speed in km/h by default, convert to m/s
            "wind_speed_ms": [v / 3.6 for v in h["wind_speed_10m"]],
            "wind_direction_deg": h["wind_direction_10m"],
            "solar_radiation_wm2": h["shortwave_radiation"],
            "direct_radiation_wm2": h["direct_normal_irradiance"],
            "diffuse_radiation_wm2": h["diffuse_radiation"]
        })
        
        # Save raw fetched data
        df_era5.to_csv(cache_path, index=False)
        print(f"Saved {len(df_era5)} hourly weather records to {cache_path}")
        return df_era5

    def generate_calibrated_load_profile(self, df_weather: pd.DataFrame, df_monthly_elec: pd.DataFrame) -> pd.DataFrame:
        """
        Creates a transparent, physically grounded hourly load profile:
        - Base scientific & life-support load: ~120 kW
        - Heating load: Beta * max(0, Setpoint - T_ambient)
        - Diurnal occupancy curve (meals, work shifts, lighting)
        - Strictly calibrated against real historical monthly electricity records from Mawson Station.
        
        LABEL: MODELED_LOAD (Calibrated to Real Mawson Monthly Electricity Data)
        """
        df = df_weather.copy()
        
        # Average historical monthly electricity at Mawson (~135,000 kWh/month => ~185 kW continuous)
        avg_monthly_kwh = df_monthly_elec['electricity_kwh'].mean()
        target_avg_kw = avg_monthly_kwh / (30.416 * 24.0) # approx 185 kW
        
        base_kw = self.config["station"]["base_scientific_load_kw"]
        heat_coef = self.config["station"]["heating_degree_coefficient_kw_per_deg"]
        setpoint = self.config["station"]["indoor_setpoint_celsius"]
        
        # Heating degree load (colder temperatures demand more electric heating)
        t_amb = df['temperature_celsius'].values
        heating_deficit = np.maximum(0.0, setpoint - t_amb)
        raw_heating_kw = heat_coef * (heating_deficit / np.mean(heating_deficit) if np.mean(heating_deficit) > 0 else 1.0) * 45.0
        
        # Diurnal human activity multiplier (local station time UTC+5 at 62.8°E)
        hours = df['timestamp'].dt.hour.values
        # Peaks at 08:00 (breakfast/morning startup) and 18:00-20:00 (dinner/evening operations)
        diurnal_variation = 15.0 * np.sin((hours - 6) * np.pi / 12.0)
        
        # Combine initial profile
        raw_load = base_kw + raw_heating_kw + diurnal_variation
        # Ensure non-negative and physically reasonable bounds (minimum 100 kW, max 350 kW)
        raw_load = np.clip(raw_load, 100.0, 350.0)
        
        # Strictly calibrate mean to real Mawson historical average power
        calibration_ratio = target_avg_kw / np.mean(raw_load)
        calibrated_load_kw = raw_load * calibration_ratio
        
        df['modeled_demand_kw'] = np.round(calibrated_load_kw, 2)
        df['demand_data_type'] = "MODELED_LOAD (Calibrated to Real Mawson Monthly Electricity Data)"
        return df

    def run(self) -> pd.DataFrame:
        """Executes complete data pipeline and exports processed hourly dataset."""
        print("Starting Data Ingestion & Preprocessing Pipeline...")
        df_elec_monthly, df_fuel_monthly = self.extract_and_clean_station_energy_data()
        print(f"Extracted {len(df_elec_monthly)} monthly electricity records and {len(df_fuel_monthly)} fuel records for Mawson.")
        
        # Fetch 1 year of hourly weather (2023)
        df_weather = self.fetch_or_load_era5_hourly(start_date="2023-01-01", end_date="2023-12-31")
        
        # Synthesize and calibrate hourly load profile
        df_processed = self.generate_calibrated_load_profile(df_weather, df_elec_monthly)
        
        # Output clean processed dataset
        output_file = os.path.join(self.processed_data_dir, "mawson_hourly_energy_weather.csv")
        df_processed.to_csv(output_file, index=False)
        print(f"Processed dataset successfully written to {output_file} ({len(df_processed)} rows, {len(df_processed.columns)} columns).")
        return df_processed

if __name__ == "__main__":
    pipeline = PolarDataPipeline()
    df = pipeline.run()
    print("Sample output:\n", df.head(3))
