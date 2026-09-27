"""
Polar Grid: Baseline Comparison & Evaluation Module
Evaluates microgrid dispatch performance, compares against 100% diesel baseline,
and generates publication-quality evaluation graphs.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class BaselineComparator:
    def __init__(self, config_path: str = None, outputs_dir: str = None):
        if config_path is None:
            self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "station_config.json"))
        else:
            self.config_path = os.path.abspath(config_path)
            
        if outputs_dir is None:
            self.outputs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "outputs"))
        else:
            self.outputs_dir = os.path.abspath(outputs_dir)
            
        os.makedirs(self.outputs_dir, exist_ok=True)
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.gen_cfg = self.config["diesel_generator"]

    def evaluate(self, schedule_df: pd.DataFrame) -> dict:
        """
        Computes honest comparison metrics between 100% diesel baseline and Polar Grid optimized dispatch.
        """
        df = schedule_df.copy()
        dt = 1.0 # 1 hour
        
        fuel_a = self.gen_cfg["fuel_curve_a_l_per_kwh"]
        fuel_b = self.gen_cfg["fuel_curve_b_l_per_kw_rated"]
        P_rated = self.gen_cfg["total_capacity_kw"]
        
        # 1. Baseline: 100% diesel generator supplies the entire demand
        baseline_diesel_kw = df["predicted_demand_kw"].values
        baseline_fuel_litres = (fuel_a * baseline_diesel_kw + fuel_b * P_rated) * dt
        
        total_demand_kwh = float(np.sum(df["predicted_demand_kw"] * dt))
        total_ren_used_kwh = float(np.sum(df["renewable_used_kw"] * dt))
        total_dsl_gen_kwh = float(np.sum(df["diesel_generation_kw"] * dt))
        total_bat_dis_kwh = float(np.sum(df["battery_discharge_kw"] * dt))
        total_bat_ch_kwh = float(np.sum(df["battery_charge_kw"] * dt))
        total_unmet_kwh = float(np.sum(df["unmet_demand_kw"] * dt))
        
        baseline_total_fuel = float(np.sum(baseline_fuel_litres))
        optimized_total_fuel = float(np.sum(df["diesel_fuel_litres"]))
        fuel_saved_litres = max(0.0, baseline_total_fuel - optimized_total_fuel)
        
        diesel_reduction_pct = (fuel_saved_litres / baseline_total_fuel * 100.0) if baseline_total_fuel > 0 else 0.0
        ren_penetration_pct = (total_ren_used_kwh / total_demand_kwh * 100.0) if total_demand_kwh > 0 else 0.0
        
        summary = {
            "time_horizon_hours": int(len(df)),
            "total_demand_kwh": round(total_demand_kwh, 2),
            "renewable_energy_used_kwh": round(total_ren_used_kwh, 2),
            "diesel_energy_used_kwh": round(total_dsl_gen_kwh, 2),
            "battery_discharge_kwh": round(total_bat_dis_kwh, 2),
            "battery_charge_kwh": round(total_bat_ch_kwh, 2),
            "unmet_demand_kwh": round(total_unmet_kwh, 2),
            "renewable_penetration_percent": round(ren_penetration_pct, 2),
            "baseline_diesel_fuel_litres": round(baseline_total_fuel, 2),
            "optimized_diesel_fuel_litres": round(optimized_total_fuel, 2),
            "diesel_fuel_saved_litres": round(fuel_saved_litres, 2),
            "diesel_reduction_percent": round(diesel_reduction_pct, 2)
        }
        
        # Save summary JSON
        with open(os.path.join(self.outputs_dir, "dispatch_summary_metrics.json"), "w") as f:
            json.dump(summary, f, indent=2)
            
        return summary

    def generate_visualizations(self, schedule_df: pd.DataFrame, forecast_df: pd.DataFrame = None):
        """Generates clear, high-contrast plots of forecasts and dispatch schedules."""
        plt.style.use('default')
        
        # 1. Dispatch Schedule Stack Plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={'height_ratios': [2.5, 1]})
        
        timestamps = pd.to_datetime(schedule_df['timestamp'])
        
        ax1.plot(timestamps, schedule_df['predicted_demand_kw'], color='#111111', linewidth=2.5, label='Station Demand (kW)', zorder=5)
        ax1.plot(timestamps, schedule_df['solar_generation_kw'], color='#f59e0b', linestyle='--', linewidth=1.5, label='Solar Potential (kW)')
        ax1.plot(timestamps, schedule_df['wind_generation_kw'], color='#06b6d4', linestyle='--', linewidth=1.5, label='Wind Potential (kW)')
        
        # Stacked generation contributions
        y_ren = schedule_df['renewable_used_kw']
        y_bat = schedule_df['battery_discharge_kw']
        y_dsl = schedule_df['diesel_generation_kw']
        
        ax1.fill_between(timestamps, 0, y_ren, color='#10b981', alpha=0.6, label='Renewable Direct (kW)')
        ax1.fill_between(timestamps, y_ren, y_ren + y_bat, color='#8b5cf6', alpha=0.6, label='Battery Discharge (kW)')
        ax1.fill_between(timestamps, y_ren + y_bat, y_ren + y_bat + y_dsl, color='#ef4444', alpha=0.5, label='Diesel Generation (kW)')
        
        ax1.set_ylabel('Power (kW)', fontsize=12)
        ax1.set_title('Polar Grid: 48-Hour Microgrid Dispatch & Load Satisfaction', fontsize=14, fontweight='bold')
        ax1.grid(True, linestyle=':', alpha=0.6)
        ax1.legend(loc='upper right', framealpha=0.9)
        
        # Subplot 2: Battery State of Charge (%)
        ax2.plot(timestamps, schedule_df['battery_soc_percent'], color='#8b5cf6', linewidth=2.0, label='Battery SoC (%)')
        ax2.axhline(self.config['battery_storage']['min_soc'] * 100, color='red', linestyle=':', alpha=0.7, label='Min SoC Limit (20%)')
        ax2.axhline(self.config['battery_storage']['max_soc'] * 100, color='green', linestyle=':', alpha=0.7, label='Max SoC Limit (95%)')
        ax2.set_ylabel('SoC (%)', fontsize=11)
        ax2.set_xlabel('Timeline (UTC)', fontsize=12)
        ax2.set_ylim(0, 105)
        ax2.grid(True, linestyle=':', alpha=0.6)
        ax2.legend(loc='upper right', framealpha=0.9)
        
        fig.tight_layout()
        dispatch_plot_path = os.path.join(self.outputs_dir, "energy_dispatch_schedule.png")
        fig.savefig(dispatch_plot_path, dpi=150)
        plt.close(fig)
        
        # 2. Actual vs Predicted Forecast Plot (if forecast_df supplied)
        if forecast_df is not None and 'actual_modeled_demand_kw' in forecast_df.columns:
            fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
            ts = pd.to_datetime(forecast_df['timestamp'])
            
            # Demand
            axes[0].plot(ts, forecast_df['actual_modeled_demand_kw'], color='#374151', label='Actual Demand (kW)')
            axes[0].plot(ts, forecast_df['pred_modeled_demand_kw'], color='#2563eb', linestyle='--', label='Predicted Demand (kW)')
            axes[0].set_ylabel('Demand (kW)')
            axes[0].set_title('AI Forecasting Performance: Actual vs Predicted (Chronological Out-of-Sample)', fontsize=13, fontweight='bold')
            axes[0].grid(True, linestyle=':', alpha=0.6)
            axes[0].legend(loc='upper right')
            
            # Wind Speed
            axes[1].plot(ts, forecast_df['actual_wind_speed_ms'], color='#374151', label='Actual Wind Speed (m/s)')
            axes[1].plot(ts, forecast_df['pred_wind_speed_ms'], color='#059669', linestyle='--', label='Predicted Wind Speed (m/s)')
            axes[1].set_ylabel('Wind Speed (m/s)')
            axes[1].grid(True, linestyle=':', alpha=0.6)
            axes[1].legend(loc='upper right')
            
            # Solar Radiation
            axes[2].plot(ts, forecast_df['actual_solar_radiation_wm2'], color='#374151', label='Actual Solar Irradiance (W/m²)')
            axes[2].plot(ts, forecast_df['pred_solar_radiation_wm2'], color='#d97706', linestyle='--', label='Predicted Solar Irradiance (W/m²)')
            axes[2].set_ylabel('Solar (W/m²)')
            axes[2].set_xlabel('Timeline (UTC)')
            axes[2].grid(True, linestyle=':', alpha=0.6)
            axes[2].legend(loc='upper right')
            
            fig.tight_layout()
            forecast_plot_path = os.path.join(self.outputs_dir, "forecast_actual_validation.png")
            fig.savefig(forecast_plot_path, dpi=150)
            plt.close(fig)
            
        print(f"Visualizations successfully saved to {self.outputs_dir}")

if __name__ == "__main__":
    pass
