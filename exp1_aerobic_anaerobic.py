"""Ugly pass 1: aerobic vs anaerobic comparison on textbook (e_coli_core).

Steps:
 1. Solve aerobically, record growth + all non-zero exchanges.
 2. Set EX_o2_e.lower_bound = 0, re-solve, record same.
 3. Carbon balance per condition (% of carbon taken up).
 4. Stacked-bar plot of carbon fate.
"""
import re

import cobra
import matplotlib.pyplot as plt
import pandas as pd


def carbon_count(met):
    """Carbons in a metabolite: parsed elements first, formula regex fallback."""
    try:
        els = met.elements
        if els and "C" in els:
            return int(els["C"])
    except Exception:
        pass
    n = 0  # element-aware fallback: 'C' only counts as its own symbol
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", met.formula or ""):
        if sym == "C":
            n += int(num) if num else 1
    return n


def record(model, label):
    sol = model.optimize()
    print(f"== {label}: status={sol.status} growth={sol.objective_value:.4f}")
    rows = []
    for r in model.reactions:
        if r.id.startswith("EX_"):
            fl = float(sol.fluxes[r.id])
            if abs(fl) > 1e-9:
                mets = list(r.metabolites)
                met = mets[0] if len(mets) == 1 else None
                rows.append({
                    "reaction": r.id,
                    "metabolite": met.id if met is not None else "?",
                    "formula": met.formula if met is not None else "",
                    "C": carbon_count(met) if met is not None else 0,
                    "flux": fl,
                })
    df = pd.DataFrame(rows).sort_values("flux").reset_index(drop=True)
    print(df.to_string(index=False))
    return float(sol.objective_value), df


def carbon_balance(df, label):
    df = df.copy()
    df["C_flux"] = df["flux"] * df["C"]  # <0 uptake, >0 secretion
    uptake = float(-df.loc[df["C_flux"] < 0, "C_flux"].sum())
    sec = df.loc[df["C_flux"] > 1e-9].copy()
    sec["pct_of_uptake"] = 100 * sec["C_flux"] / uptake
    sec["condition"] = label
    rem = 100 - float(sec["pct_of_uptake"].sum())
    print(f"-- carbon {label}: uptake={uptake:.2f} C-mmol/gDW/h, "
          f"secreted={sec['pct_of_uptake'].sum():.1f}%, biomass(remainder)={rem:.1f}%")
    print(sec[["reaction", "flux", "C", "C_flux", "pct_of_uptake"]].to_string(index=False))
    return uptake, sec, rem


model = cobra.io.load_model("textbook")
print("model:", model.id,
      "| EX_o2 bounds:", model.reactions.EX_o2_e.bounds,
      "| EX_glc bounds:", model.reactions.EX_glc__D_e.bounds)

g_aer, df_aer = record(model, "AEROBIC")
df_aer.to_csv("fluxes_aerobic.csv", index=False)

model.reactions.EX_o2_e.lower_bound = 0
g_ana, df_ana = record(model, "ANAEROBIC (EX_o2_e LB=0)")
df_ana.to_csv("fluxes_anaerobic.csv", index=False)

up_aer, cb_aer, rem_aer = carbon_balance(df_aer, "aerobic")
up_ana, cb_ana, rem_ana = carbon_balance(df_ana, "anaerobic")
pd.concat([cb_aer, cb_ana]).to_csv("carbon_balance.csv", index=False)

# --- stacked bars: % of uptake carbon per secreted product + biomass remainder ---
NAMES = {"EX_ac_e": "acetate", "EX_for_e": "formate", "EX_etoh_e": "ethanol",
         "EX_lac__D_e": "lactate", "EX_succ_e": "succinate", "EX_co2_e": "CO2",
         "EX_pyr_e": "pyruvate", "EX_glu__L_e": "glutamate", "EX_glyc_e": "glycerol"}
order, seen = [], set()
for rid in list(cb_aer["reaction"]) + list(cb_ana["reaction"]):
    if rid not in seen:
        seen.add(rid)
        order.append(rid)
order.append("biomass (remainder)")
pa = dict(zip(cb_aer["reaction"], cb_aer["pct_of_uptake"]))
pb = dict(zip(cb_ana["reaction"], cb_ana["pct_of_uptake"]))
vals_a = [pa.get(r, 0) for r in order[:-1]] + [rem_aer]
vals_b = [pb.get(r, 0) for r in order[:-1]] + [rem_ana]

fig, ax = plt.subplots()
b_a, b_b = 0, 0
for name, va, vb in zip(order, vals_a, vals_b):
    lbl = NAMES.get(name, name)
    if va > 0:
        ax.bar("aerobic", va, bottom=b_a, label=lbl)
        b_a += va
    if vb > 0:
        ax.bar("anaerobic", vb, bottom=b_b, label=lbl)
        b_b += vb
ax.set_ylabel("% of carbon taken up")
ax.set_title(f"aerobic (mu={g_aer:.3f}) vs anaerobic (mu={g_ana:.3f}) — ugly v1")
handles, labels = ax.get_legend_handles_labels()
ax.legend(dict(zip(labels, handles)).values(), dict(zip(labels, handles)).keys(),
          bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout()
fig.savefig("carbon_fate.png", dpi=120)
print("saved carbon_fate.png")
