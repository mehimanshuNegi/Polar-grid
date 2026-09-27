import os
import json
import numpy as np
import pandas as pd
from scipy.optimize import linprog

def test_formulation():
    # Load config
    with open("config/station_config.json") as f:
        cfg = json.load(f)
    bat_cfg = cfg["battery_storage"]
    gen_cfg = cfg["diesel_generator"]
    penalties = cfg["dispatch_weights"]

    import urllib.request
    url = "http://127.0.0.1:8000/api/schedule?horizon=24&season=live&battery_state=NORMAL&diesel_state=NORMAL"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read().decode())
    df = pd.DataFrame(data["schedule"])

    T = len(df)
    dt = 1.0
    demand = df["predicted_demand_kw"].values
    solar_avail = df["solar_generation_kw"].values
    wind_avail = df["wind_generation_kw"].values

    E_cap = bat_cfg["capacity_kwh"]
    P_ch_max = bat_cfg["max_charge_power_kw"]
    P_dis_max = bat_cfg["max_discharge_power_kw"]
    eta_ch = bat_cfg["charge_efficiency"]
    eta_dis = bat_cfg["discharge_efficiency"]
    soc_min = bat_cfg["min_soc"]
    soc_max = bat_cfg["max_soc"]
    soc_init = 0.50

    fuel_a = gen_cfg["fuel_curve_a_l_per_kwh"]

    for b_state, soc_init in [("NORMAL", 0.50), ("LOW", 0.25), ("CRITICAL", 0.20)]:
        for d_state, P_diesel_max in [("NORMAL", 375.0), ("LIMITED", 250.0), ("CRITICAL", 125.0)]:
            # Formulate LP
            n_vars_per_t = 8
            n_vars = n_vars_per_t * T
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

            c = np.zeros(n_vars)
            max_d = np.max(demand)
            for t in range(T):
                net_d = max(0.0, demand[t] - (solar_avail[t] + wind_avail[t]))
                c[idx(t, I_DSL)] = fuel_a * penalties["diesel_fuel_penalty"] * (1.0 + 0.02 * (net_d / max_d))
                c[idx(t, I_UNM)] = penalties["unmet_demand_penalty"]
                c[idx(t, I_PCH)] = penalties["battery_cycling_penalty"]
                c[idx(t, I_PDIS)] = penalties["battery_cycling_penalty"]
                c[idx(t, I_CUR)] = penalties["curtailment_penalty"]

            n_eq = 3 * T
            A_eq = np.zeros((n_eq, n_vars))
            b_eq = np.zeros(n_eq)
            eq_row = 0
            for t in range(T):
                # 1. Power balance: ren_direct + bat_dis + diesel + unmet = demand
                A_eq[eq_row, idx(t, I_SOL)] = 1.0
                A_eq[eq_row, idx(t, I_WND)] = 1.0
                A_eq[eq_row, idx(t, I_PDIS)] = 1.0
                A_eq[eq_row, idx(t, I_DSL)] = 1.0
                A_eq[eq_row, idx(t, I_UNM)] = 1.0
                b_eq[eq_row] = demand[t]
                eq_row += 1

                # 2. Battery balance: E(t) - E(t-1) - eta_ch * P_ch + (1/eta_dis) * P_dis = 0
                A_eq[eq_row, idx(t, I_EBAT)] = 1.0
                A_eq[eq_row, idx(t, I_PCH)] = -eta_ch * dt
                A_eq[eq_row, idx(t, I_PDIS)] = (1.0 / eta_dis) * dt
                if t == 0:
                    b_eq[eq_row] = soc_init * E_cap
                else:
                    A_eq[eq_row, idx(t-1, I_EBAT)] = -1.0
                    b_eq[eq_row] = 0.0
                eq_row += 1

                # 3. Renewable balance: solar_used + wind_used + P_ch + P_cur = solar_avail + wind_avail
                A_eq[eq_row, idx(t, I_SOL)] = 1.0
                A_row_wnd = idx(t, I_WND)
                A_eq[eq_row, idx(t, I_WND)] = 1.0
                A_eq[eq_row, idx(t, I_PCH)] = 1.0
                A_eq[eq_row, idx(t, I_CUR)] = 1.0
                b_eq[eq_row] = solar_avail[t] + wind_avail[t]
                eq_row += 1

            bounds = []
            for t in range(T):
                bounds.append((0.0, solar_avail[t]))
                bounds.append((0.0, wind_avail[t]))
                bounds.append((0.0, P_ch_max))
                bounds.append((0.0, P_dis_max))
                bounds.append((0.0, P_diesel_max))
                bounds.append((0.0, None))
                bounds.append((0.0, None))
                bounds.append((soc_min * E_cap, soc_max * E_cap))

            res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")
            x = res.x
            print(f"B={b_state:8} (init={soc_init*100:.0f}%) | D={d_state:8} (cap={P_diesel_max:.0f}kW) -> H0_dsl={x[idx(0, I_DSL)]:.1f}kW, H0_soc={x[idx(0, I_EBAT)]/E_cap*100:.1f}%, H0_unmet={x[idx(0, I_UNM)]:.1f}kW")

if __name__ == "__main__":
    test_formulation()
