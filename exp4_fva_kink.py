"""Ugly pass 4: FVA (anaerobic + O2=14) and formate-discrepancy probe.

exp2 (sequential bounds on one model) showed formate -> 0 at O2=12,
but exp3 (fresh model per point) shows formate still falling at O2=14.
Suspect: degenerate alternative optima. FVA at O2=14 tests that.
"""
import cobra
import pandas as pd
from cobra.flux_analysis import flux_variability_analysis

KEY = ["EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_lac__D_e", "EX_succ_e",
       "EX_co2_e", "PFL", "PDH", "PTAr", "ACKr", "ACALD", "ALCD2x",
       "LDH_D", "PPC", "FRD7", "SUCDi", "NADH16", "CYTBD", "ATPS4r", "MDH"]

# ---------- 1. fresh-load fluxes across the disputed region ----------
print("--- fresh-load fluxes 12..15 (compare o2_sweep.csv) ---")
for o2 in [12.0, 13.0, 14.0, 14.5, 15.0]:
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = -o2
    s = m.optimize()
    f = s.fluxes
    print(f"O2={o2:5.1f} growth={s.objective_value:.6f} for={f['EX_for_e']:8.3f} "
          f"PFL={f['PFL']:8.3f} PDH={f['PDH']:8.3f} ac={f['EX_ac_e']:8.3f} "
          f"MDH={f['MDH']:8.3f} co2={f['EX_co2_e']:8.3f}")


def run_fva(o2max, tag):
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = -o2max
    print(f"--- FVA {tag} @100% optimum (growth={m.optimize().objective_value:.4f}) ---")
    fva = flux_variability_analysis(m, fraction_of_optimum=1.0, processes=1)
    fva.to_csv(f"fva_{tag}.csv")
    keys = [k for k in KEY if k in fva.index]
    sub = fva.loc[keys].copy()
    sub["width"] = sub["maximum"] - sub["minimum"]
    print(sub.to_string())
    wide = fva.copy()
    wide["width"] = wide["maximum"] - wide["minimum"]
    print(f"--- widest ranges {tag} (top 8) ---")
    print(wide.sort_values("width", ascending=False).head(8).to_string())


run_fva(0.0, "anaerobic")
run_fva(14.0, "o2_14")
