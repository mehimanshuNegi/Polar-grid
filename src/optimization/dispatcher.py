"""
Polar Grid: Microgrid Optimization & Dispatch Engine
Computes optimal 24-72 hour energy dispatch schedules minimizing diesel fuel consumption
while guaranteeing demand satisfaction, battery SoC limits, and energy conservation.
"""

import os
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog

class MicrogridOptimizer:
    def __init__(self, config_path: str = None):
        if config_path is None:
            self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config", "station_config.json"))
        else:
            self.config_path = os.path.abspath(config_path)
            
        with open(self.config_path, "r") as f:
            self.config = json.load(f)
            
        self.bat_cfg = self.config["battery_storage"]
        self.gen_cfg = self.config["diesel_generator"]
        self.penalties = self.config["dispatch_weights"]

    def optimize_schedule(self, df_input: pd.DataFrame, initial_soc: float = None) -> pd.DataFrame:
        """
        Calculates optimal multi-period energy dispatch schedule.
        Honors:
          1. Exact power balance: Solar + Wind + BatDischarge + Diesel + Unmet = Demand + BatCharge + Curtailment
          2. Battery state of charge (SoC) continuity:
             E_bat(t) = E_bat(t-1) + (eta_ch * P_charge(t) - P_discharge(t) / eta_dis) * dt
          3. Battery capacity bounds: SoC_min <= SoC(t) <= SoC_max
          4. Generator rating bounds: 0 <= P_diesel(t) <= P_diesel_max
        """
        df = df_input.copy().reset_index(drop=True)
        T = len(df)
        dt = 1.0 # 1 hour time-step
        
        # Extract series
        demand_col = "pred_modeled_demand_kw" if "pred_modeled_demand_kw" in df.columns else "modeled_demand_kw"
        demand = df[demand_col].values
        solar_avail = df["solar_generation_kw"].values
        wind_avail = df["wind_generation_kw"].values
        
        E_cap = self.bat_cfg["capacity_kwh"]
        P_ch_max = self.bat_cfg["max_charge_power_kw"]
        P_dis_max = self.bat_cfg["max_discharge_power_kw"]
        eta_ch = self.bat_cfg["charge_efficiency"]
        eta_dis = self.bat_cfg["discharge_efficiency"]
        soc_min = self.bat_cfg["min_soc"]
        soc_max = self.bat_cfg["max_soc"]
        soc_init = self.bat_cfg["initial_soc"] if initial_soc is None else initial_soc
        
        P_diesel_max = self.gen_cfg["total_capacity_kw"]
        fuel_a = self.gen_cfg["fuel_curve_a_l_per_kwh"]
        fuel_b = self.gen_cfg["fuel_curve_b_l_per_kw_rated"]
        
        # Decision variables per time step t:
        # [P_solar_used(t), P_wind_used(t), P_ch(t), P_dis(t), P_diesel(t), P_unmet(t), P_curtail(t), E_bat(t)]
        # Total variables: 8 * T
        n_vars_per_t = 8
        n_vars = n_vars_per_t * T
        
        # Indices helper
        def idx(t, var_offset):
            return t * n_vars_per_t + var_offset
            
        I_SOL = 0
        I_WND = 1
        I_PCH = 2
        I_PDIS = 3
        I_DSL = 4
        I_UNM = 5
        I_CUR = 6
        I_EBAT = 7
        
        # Objective vector c: minimize diesel fuel + penalty on unmet demand + tiny penalty on battery cycling
        # Includes slight peak-load displacement tie-breaker so battery storage naturally displaces peak diesel
        c = np.zeros(n_vars)
        max_d = max(1.0, float(np.max(demand)))
        for t in range(T):
            net_d = max(0.0, float(demand[t] - (solar_avail[t] + wind_avail[t])))
            c[idx(t, I_DSL)] = fuel_a * self.penalties["diesel_fuel_penalty"] * (1.0 + 0.02 * (net_d / max_d))
            c[idx(t, I_UNM)] = self.penalties["unmet_demand_penalty"]
            c[idx(t, I_PCH)] = self.penalties["battery_cycling_penalty"]
            c[idx(t, I_PDIS)] = self.penalties["battery_cycling_penalty"]
            c[idx(t, I_CUR)] = self.penalties["curtailment_penalty"]
            
        # Equality constraints: A_eq * x = b_eq
        # 1. Station bus power balance at each t:
        #    P_solar_used(t) + P_wind_used(t) + P_dis(t) + P_diesel(t) + P_unmet(t) - P_ch(t) = Demand(t)
        #    Total gen (sol + wnd + dis + dsl + unm) = Total load (Demand + P_ch)
        # 2. Battery dynamic energy balance:
        #    For t=0: E_bat(0) - eta_ch * dt * P_ch(0) + (1 / eta_dis) * dt * P_dis(0) = soc_init * E_cap
        #    For t>0: E_bat(t) - E_bat(t-1) - eta_ch * dt * P_ch(t) + (1 / eta_dis) * dt * P_dis(t) = 0
        # 3. Renewable balance:
        #    P_solar_used(t) + P_wind_used(t) + P_curtail(t) = Solar_avail(t) + Wind_avail(t)
        
        n_eq = 3 * T
        A_eq = np.zeros((n_eq, n_vars))
        b_eq = np.zeros(n_eq)
        
        eq_row = 0
        for t in range(T):
            # 1. Station bus power balance
            A_eq[eq_row, idx(t, I_SOL)] = 1.0
            A_eq[eq_row, idx(t, I_WND)] = 1.0
            A_eq[eq_row, idx(t, I_PDIS)] = 1.0
            A_eq[eq_row, idx(t, I_DSL)] = 1.0
            A_eq[eq_row, idx(t, I_UNM)] = 1.0
            A_eq[eq_row, idx(t, I_PCH)] = -1.0
            b_eq[eq_row] = demand[t]
            eq_row += 1
            
            # 2. Battery dynamic energy balance
            A_eq[eq_row, idx(t, I_EBAT)] = 1.0
            A_eq[eq_row, idx(t, I_PCH)] = -eta_ch * dt
            A_eq[eq_row, idx(t, I_PDIS)] = (1.0 / eta_dis) * dt
            if t == 0:
                b_eq[eq_row] = soc_init * E_cap
            else:
                A_eq[eq_row, idx(t-1, I_EBAT)] = -1.0
                b_eq[eq_row] = 0.0
            eq_row += 1
            
            # 3. Renewable balance (used + curtailed = available)
            A_eq[eq_row, idx(t, I_SOL)] = 1.0
            A_eq[eq_row, idx(t, I_WND)] = 1.0
            A_eq[eq_row, idx(t, I_CUR)] = 1.0
            b_eq[eq_row] = solar_avail[t] + wind_avail[t]
            eq_row += 1

        # Bounds on variables:
        # Battery charging is strictly limited to genuine renewable surplus (Solar + Wind - Demand).
        # Diesel can NEVER charge the battery.
        bounds = []
        for t in range(T):
            surplus_ren = max(0.0, float(solar_avail[t] + wind_avail[t] - demand[t]))
            p_ch_upper = min(P_ch_max, surplus_ren)
            
            bounds.append((0.0, solar_avail[t]))             # I_SOL
            bounds.append((0.0, wind_avail[t]))              # I_WND
            bounds.append((0.0, p_ch_upper))                 # I_PCH (surplus renewables only)
            bounds.append((0.0, P_dis_max))                  # I_PDIS
            bounds.append((0.0, P_diesel_max))               # I_DSL
            bounds.append((0.0, None))                       # I_UNM
            bounds.append((0.0, None))                       # I_CUR
            bounds.append((soc_min * E_cap, soc_max * E_cap))# I_EBAT

        # Solve Linear Program using HiGHS
        res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
        
        if not res.success:
            print(f"Warning: LP solver failed: {res.message}. Falling back to rule-based priority dispatch.")
            return self._rule_based_fallback(df, initial_soc)
            
        x = res.x
        
        # Build clean schedule output dataframe
        schedule_records = []
        for t in range(T):
            sol_used = max(0.0, x[idx(t, I_SOL)])
            wnd_used = max(0.0, x[idx(t, I_WND)])
            p_ch = max(0.0, x[idx(t, I_PCH)])
            p_dis = max(0.0, x[idx(t, I_PDIS)])
            p_dsl = max(0.0, x[idx(t, I_DSL)])
            p_unm = max(0.0, x[idx(t, I_UNM)])
            p_cur = max(0.0, x[idx(t, I_CUR)])
            e_bat = x[idx(t, I_EBAT)]
            soc = e_bat / E_cap
            
            # Generator fuel consumption in litres
            dsl_fuel = (fuel_a * p_dsl + (fuel_b * P_diesel_max if p_dsl > 1.0 else 0.0)) * dt
            
            schedule_records.append({
                "timestamp": df["timestamp"].iloc[t],
                "predicted_demand_kw": round(float(demand[t]), 2),
                "solar_generation_kw": round(float(solar_avail[t]), 2),
                "wind_generation_kw": round(float(wind_avail[t]), 2),
                "renewable_used_kw": round(float(sol_used + wnd_used), 2),
                "battery_charge_kw": round(float(p_ch), 2),
                "battery_discharge_kw": round(float(p_dis), 2),
                "battery_soc_percent": round(float(soc * 100.0), 2),
                "diesel_generation_kw": round(float(p_dsl), 2),
                "diesel_fuel_litres": round(float(dsl_fuel), 2),
                "curtailed_renewable_kw": round(float(p_cur), 2),
                "unmet_demand_kw": round(float(p_unm), 2)
            })
            
        return pd.DataFrame(schedule_records)

    def _rule_based_fallback(self, df: pd.DataFrame, initial_soc: float = None) -> pd.DataFrame:
        """Physical rule-based dispatch fallback if solver is unavailable."""
        T = len(df)
        dt = 1.0
        demand_col = "pred_modeled_demand_kw" if "pred_modeled_demand_kw" in df.columns else "modeled_demand_kw"
        demand = df[demand_col].values
        solar_avail = df["solar_generation_kw"].values
        wind_avail = df["wind_generation_kw"].values
        
        E_cap = self.bat_cfg["capacity_kwh"]
        P_ch_max = self.bat_cfg["max_charge_power_kw"]
        P_dis_max = self.bat_cfg["max_discharge_power_kw"]
        eta_ch = self.bat_cfg["charge_efficiency"]
        eta_dis = self.bat_cfg["discharge_efficiency"]
        soc_min = self.bat_cfg["min_soc"]
        soc_max = self.bat_cfg["max_soc"]
        soc_curr = self.bat_cfg["initial_soc"] if initial_soc is None else initial_soc
        
        P_diesel_max = self.gen_cfg["total_capacity_kw"]
        fuel_a = self.gen_cfg["fuel_curve_a_l_per_kwh"]
        fuel_b = self.gen_cfg["fuel_curve_b_l_per_kw_rated"]
        
        records = []
        for t in range(T):
            d = demand[t]
            ren = solar_avail[t] + wind_avail[t]
            
            p_ch = 0.0
            p_dis = 0.0
            p_dsl = 0.0
            p_unm = 0.0
            p_cur = 0.0
            ren_used = min(d, ren)
            net_deficit = d - ren_used
            excess_ren = ren - ren_used
            
            if excess_ren > 0:
                # Charge battery
                max_allow_ch = min(P_ch_max, (soc_max - soc_curr) * E_cap / (eta_ch * dt))
                p_ch = min(excess_ren, max_allow_ch)
                p_cur = excess_ren - p_ch
                soc_curr += (p_ch * eta_ch * dt) / E_cap
            elif net_deficit > 0:
                # Discharge battery
                max_allow_dis = min(P_dis_max, (soc_curr - soc_min) * E_cap * eta_dis / dt)
                p_dis = min(net_deficit, max_allow_dis)
                soc_curr -= (p_dis * dt) / (eta_dis * E_cap)
                still_deficit = net_deficit - p_dis
                if still_deficit > 0:
                    p_dsl = min(P_diesel_max, still_deficit)
                    p_unm = still_deficit - p_dsl
                    
            dsl_fuel = (fuel_a * p_dsl + (fuel_b * P_diesel_max if p_dsl > 1.0 else 0.0)) * dt
            records.append({
                "timestamp": df["timestamp"].iloc[t],
                "predicted_demand_kw": round(float(d), 2),
                "solar_generation_kw": round(float(solar_avail[t]), 2),
                "wind_generation_kw": round(float(wind_avail[t]), 2),
                "renewable_used_kw": round(float(ren_used), 2),
                "battery_charge_kw": round(float(p_ch), 2),
                "battery_discharge_kw": round(float(p_dis), 2),
                "battery_soc_percent": round(float(soc_curr * 100.0), 2),
                "diesel_generation_kw": round(float(p_dsl), 2),
                "diesel_fuel_litres": round(float(dsl_fuel), 2),
                "curtailed_renewable_kw": round(float(p_cur), 2),
                "unmet_demand_kw": round(float(p_unm), 2)
            })
        return pd.DataFrame(records)

if __name__ == "__main__":
    from src.renewable.generation_estimator import RenewableEstimator
    test_df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=48, freq="1h"),
        "pred_modeled_demand_kw": [180.0] * 48,
        "solar_generation_kw": [30.0 if 6 <= h <= 18 else 0.0 for h in range(48)],
        "wind_generation_kw": [80.0] * 48
    })
    optimizer = MicrogridOptimizer()
    sched = optimizer.optimize_schedule(test_df)
    print("Test Schedule Head:\n", sched.head(3))
