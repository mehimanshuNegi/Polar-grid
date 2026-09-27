"""
Polar Grid: Feature Engineering Module
Transforms cleaned time-series weather and load data into structured ML features.
"""

import numpy as np
import pandas as pd

class FeatureBuilder:
    def __init__(self):
        pass

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts temporal calendar, cyclical, lag, and rolling features.
        Preserves chronological ordering.
        """
        data = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
        data = data.sort_values('timestamp').reset_index(drop=True)
        
        # 1. Calendar and Cyclical Time Features
        dt = data['timestamp'].dt
        data['hour'] = dt.hour
        data['day_of_year'] = dt.dayofyear
        data['month'] = dt.month
        
        # Sine/Cosine cyclical encodings for periodic continuity
        data['sin_hour'] = np.sin(2 * np.pi * data['hour'] / 24.0)
        data['cos_hour'] = np.cos(2 * np.pi * data['hour'] / 24.0)
        data['sin_doy'] = np.sin(2 * np.pi * data['day_of_year'] / 365.25)
        data['cos_doy'] = np.cos(2 * np.pi * data['day_of_year'] / 365.25)
        
        # 2. Lag Features (1h, 2h, 3h, 24h lag) for dynamic persistence
        for target in ['temperature_celsius', 'wind_speed_ms', 'solar_radiation_wm2', 'modeled_demand_kw']:
            data[f'{target}_lag1'] = data[target].shift(1)
            data[f'{target}_lag2'] = data[target].shift(2)
            data[f'{target}_lag24'] = data[target].shift(24)
            
            # Rolling statistics (6-hour and 24-hour windows)
            data[f'{target}_roll6_mean'] = data[target].shift(1).rolling(window=6, min_periods=1).mean()
            data[f'{target}_roll24_mean'] = data[target].shift(1).rolling(window=24, min_periods=1).mean()

        # Drop initial 24 hours of NaNs caused by the 24-hour lag
        clean_features_df = data.dropna().reset_index(drop=True)
        return clean_features_df

if __name__ == "__main__":
    df_raw = pd.read_csv("data/processed/mawson_hourly_energy_weather.csv")
    fb = FeatureBuilder()
    df_feat = fb.build_features(df_raw)
    print(f"Features created: {df_feat.shape[1]} columns, {df_feat.shape[0]} valid rows.")
    print("Columns:", list(df_feat.columns))
