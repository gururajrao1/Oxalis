"""Ugly pass 5: repeat exp1+exp2 on genome-scale iML1515, compare vs core model."""
import re

import cobra
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def carbon_count(met):
    try:
        els = met.elements
    except Exception:
        els = None
    if els:
        return int(els.get("C", 0))
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
                rows.append({"reaction": r.id,
                             "formula": met.formula if met is not None else "",
                             "C": carbon_count(met) if met is not None else 0,
                             "flux": fl})
    df = pd.DataFrame(rows).sort_values("flux").reset_index(drop=True)
    print(df.to_string(index=False))
    return float(sol.objective_value), df


def carbon_balance(df, label):
    df = df.copy()
    df["C_flux"] = df["flux"] * df["C"]
    uptake = float(-df.loc[df["C_flux"] < 0, "C_flux"].sum())
    sec = df.loc[df["C_flux"] > 1e-9].copy()
    sec["pct_of_uptake"] = 100 * sec["C_flux"] / uptake
    sec["condition"] = label
    rem = 100 - float(sec["pct_of_uptake"].sum())
    print(f"-- carbon {label}: uptake={uptake:.2f}, secreted={sec['pct_of_uptake'].sum():.1f}%, "
          f"biomass(rem)={rem:.1f}%")
    print(sec[["reaction", "flux", "C", "C_flux", "pct_of_uptake"]].to_string(index=False))
    return uptake, sec, rem


model = cobra.io.load_json_model("iML1515.json")
model.reactions.EX_glc__D_e.lower_bound = -10.0
print("model:", model.id, len(model.reactions), "rxns")

g_aer, df_aer = record(model, "1515 AEROBIC")
df_aer.to_csv("fluxes_1515_aerobic.csv", index=False)
model.reactions.EX_o2_e.lower_bound = 0
g_ana, df_ana = record(model, "1515 ANAEROBIC")
df_ana.to_csv("fluxes_1515_anaerobic.csv", index=False)

_, cb_aer, rem_aer = carbon_balance(df_aer, "aerobic")
_, cb_ana, rem_ana = carbon_balance(df_ana, "anaerobic")
pd.concat([cb_aer, cb_ana]).to_csv("carbon_balance_1515.csv", index=False)

# --- stacked bars (products <1% grouped) ---
NAMES = {"EX_ac_e": "acetate", "EX_for_e": "formate", "EX_etoh_e": "ethanol",
         "EX_lac__D_e": "D-lactate", "EX_lac__L_e": "L-lactate",
         "EX_succ_e": "succinate", "EX_co2_e": "CO2", "EX_pyr_e": "pyruvate"}
pa = dict(zip(cb_aer["reaction"], cb_aer["pct_of_uptake"]))
pb = dict(zip(cb_ana["reaction"], cb_ana["pct_of_uptake"]))
major = [r for r in set(list(pa) + list(pb)) if max(pa.get(r, 0), pb.get(r, 0)) >= 1.0]
minor_a = sum(v for r, v in pa.items() if r not in major)
minor_b = sum(v for r, v in pb.items() if r not in major)
cats = sorted(major) + ["other (<1%)", "biomass (remainder)"]
vals_a = [pa.get(r, 0) for r in sorted(major)] + [minor_a, rem_aer]
vals_b = [pb.get(r, 0) for r in sorted(major)] + [minor_b, rem_ana]
fig, ax = plt.subplots()
b_a = b_b = 0
for name, va, vb in zip(cats, vals_a, vals_b):
    lbl = NAMES.get(name, name)
    if va > 0:
        ax.bar("aerobic", va, bottom=b_a, label=lbl); b_a += va
    if vb > 0:
        ax.bar("anaerobic", vb, bottom=b_b, label=lbl); b_b += vb
ax.set_ylabel("% of carbon taken up")
ax.set_title(f"iML1515 aerobic (mu={g_aer:.3f}) vs anaerobic (mu={g_ana:.3f})")
h, l = ax.get_legend_handles_labels()
ax.legend(dict(zip(l, h)).values(), dict(zip(l, h)).keys(),
          bbox_to_anchor=(1.02, 1), loc="upper left")
fig.tight_layout()
fig.savefig("carbon_fate_1515.png", dpi=120)
print("saved carbon_fate_1515.png")

# --- O2 sweep 0..25 with core overlay ---
TRACK = ["EX_o2_e", "EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_lac__D_e",
         "EX_lac__L_e", "EX_succ_e", "EX_pyr_e", "EX_co2_e"]
rows = []
o2 = 0.0
while o2 <= 25.0 + 1e-9:
    model.reactions.EX_o2_e.lower_bound = -o2
    sol = model.optimize()
    rec = {"o2_max": round(o2, 2), "growth": float(sol.objective_value)}
    for rid in TRACK:
        rec[rid] = float(sol.fluxes[rid]) if rid in sol.fluxes else 0.0
    rows.append(rec)
    o2 += 0.5
df = pd.DataFrame(rows)
df.to_csv("o2_sweep_1515.csv", index=False)
core = pd.read_csv("o2_sweep25.csv")
print("--- 1515 sweep head/tail ---")
print(df[["o2_max", "growth", "EX_o2_e", "EX_ac_e", "EX_etoh_e", "EX_for_e",
          "EX_lac__D_e", "EX_succ_e", "EX_co2_e"]].head(4).to_string(index=False))
print(df.tail(4).to_string(index=False))

fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
a1.plot(df["o2_max"], df["growth"], marker="o", ms=3, label="iML1515")
a1.plot(core["o2_max"], core["growth"], ls="--", label="core (textbook)")
a1.set_ylabel("growth rate (1/h)")
a1.set_title("iML1515 vs core: growth vs max O2 uptake")
a1.legend(fontsize=8); a1.grid(True, alpha=0.3)
for rid in ["EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_lac__D_e", "EX_succ_e"]:
    if df[rid].abs().max() > 1e-9:
        a2.plot(df["o2_max"], df[rid], label=rid, marker=".", ms=3)
a2.set_xlabel("max O2 uptake (mmol/gDW/h)")
a2.set_ylabel("secretion flux")
a2.legend(fontsize=8); a2.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("o2_sweep_1515.png", dpi=120)
print("saved o2_sweep_1515.png")

# --- core vs 1515 comparison ---
c_aer = pd.read_csv("fluxes_aerobic.csv"); c_ana = pd.read_csv("fluxes_anaerobic.csv")
print("--- CORE vs 1515 ---")
print(f"aerobic mu: core=0.8739 1515={g_aer:.4f} | anaerobic mu: core=0.2117 1515={g_ana:.4f}")
print("core anaerobic products:", dict(zip(c_ana['reaction'], c_ana['flux'].round(2))))
print("1515 anaerobic products:",
      {r: round(f, 2) for r, f in zip(df_ana['reaction'], df_ana['flux']) if f > 1e-9})
sat1515 = pd.read_csv("o2_sweep_1515.csv").query("growth>=%.6f" % (0.999 * g_aer)).iloc[0]
print(f"1515 O2 for full aerobic: cap={sat1515['o2_max']}, mu={sat1515['growth']:.4f}")
