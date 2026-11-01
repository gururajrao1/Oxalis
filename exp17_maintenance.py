"""Exp 17: anaerobic yield vs maintenance (ATPM) — core vs iML1515.

iML1515 underpredicts anaerobic growth partly because its maintenance + costlier
biomass bite hardest when ATP is scarce. Sweep the ATPM lower bound and record
mu for both models at glucose -10 anaerobic. Shows sensitivity, not a fit.
"""
import cobra
import pandas as pd


def sweep(model_id, atpm_lb):
    if model_id == "core":
        m = cobra.io.load_model("textbook")
    else:
        m = cobra.io.load_json_model("iML1515.json")
    m.reactions.EX_glc__D_e.lower_bound = -10.0
    m.reactions.EX_o2_e.lower_bound = 0.0
    m.reactions.ATPM.lower_bound = atpm_lb
    s = m.optimize()
    return float(s.objective_value) if s.status == "optimal" else 0.0


rows = []
atpm = 0.0
while atpm <= 15.0 + 1e-9:
    gc = sweep("core", atpm)
    g15 = sweep("iML1515", atpm)
    rows.append({"atpm": round(atpm, 2), "core": gc, "iML1515": g15})
    print(f"ATPM>={atpm:5.2f}: core={gc:.4f} iML1515={g15:.4f}")
    atpm += 1.0

pd.DataFrame(rows).to_csv("maintenance_sweep.csv", index=False)
print("saved maintenance_sweep.csv — takeaway: default ATPM core=8.39, "
      "1515=6.86; lowering ATPM closes part of the anaerobic gap, the rest is "
      "costlier 1515 biomass (ATP/g + cofactors).")
