"""Ugly pass 3: plateau (sweep to 25), kink ID (~14.7, validated on ~6.3), FVA anaerobic."""
import cobra
import matplotlib
matplotlib.use("Agg")  # headless: Tk backend breaks on this box + in spawned workers
import matplotlib.pyplot as plt
import pandas as pd
from cobra.flux_analysis import flux_variability_analysis

# ---------- 1. sweep 0..25 ----------
model = cobra.io.load_model("textbook")
rows = []
o2 = 0.0
while o2 <= 25.0 + 1e-9:
    model.reactions.EX_o2_e.lower_bound = -o2
    sol = model.optimize()
    rows.append({"o2_max": round(o2, 2), "growth": float(sol.objective_value),
                 "o2_used": float(sol.fluxes["EX_o2_e"]),
                 "ac": float(sol.fluxes["EX_ac_e"]),
                 "etoh": float(sol.fluxes["EX_etoh_e"]),
                 "for": float(sol.fluxes["EX_for_e"]),
                 "co2": float(sol.fluxes["EX_co2_e"])})
    o2 += 0.5
df = pd.DataFrame(rows)
df.to_csv("o2_sweep25.csv", index=False)
sat = df.loc[df["o2_used"] > -df["o2_max"] + 1e-9]
if len(sat):
    r = sat.iloc[0]
    print(f"O2 stops binding at cap={r['o2_max']}: uptake={r['o2_used']:.2f}, growth={r['growth']:.4f}")
print(df.tail(8).to_string(index=False))

fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
a1.plot(df["o2_max"], df["growth"], marker="o", ms=3)
if len(sat):
    a1.axvline(sat.iloc[0]["o2_max"], color="red", ls="--",
               label=f"O2 saturates ({sat.iloc[0]['o2_max']})")
    a1.legend(fontsize=8)
a1.set_ylabel("growth rate (1/h)")
a1.set_title("growth vs max O2 uptake 0-25 — ugly v1")
a1.grid(True, alpha=0.3)
for c in ["ac", "etoh", "for"]:
    a2.plot(df["o2_max"], df[c], label=c, marker=".", ms=3)
a2.set_xlabel("max O2 uptake (mmol/gDW/h)")
a2.set_ylabel("secretion flux")
a2.legend(fontsize=8)
a2.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("o2_sweep25.png", dpi=120)
print("saved o2_sweep25.png")


# ---------- 2. kink ID: compare flux slopes below vs above a breakpoint ----------
def fluxvec(o2max):
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = -o2max
    return m.optimize().fluxes


def kink_report(lo1, lo2, hi1, hi2, label):
    below = (fluxvec(lo2) - fluxvec(lo1)) / (lo2 - lo1)
    above = (fluxvec(hi2) - fluxvec(hi1)) / (hi2 - hi1)
    rep = pd.DataFrame({"slope_below": below, "slope_above": above})
    rep["delta"] = (rep["slope_above"] - rep["slope_below"]).abs()
    rep = rep.sort_values("delta", ascending=False)
    print(f"--- kink check {label}: top slope-changers ---")
    print(rep.head(12).to_string())
    rep.to_csv(f"kink_{label}.csv")
    return rep


kink_report(5.5, 6.0, 6.5, 7.0, "6p3_known")   # sanity: ethanol switches off
kink_report(14.0, 14.5, 15.0, 15.5, "14p7_unknown")


# ---------- 3. FVA anaerobic at optimal growth ----------
m = cobra.io.load_model("textbook")
m.reactions.EX_o2_e.lower_bound = 0
fva = flux_variability_analysis(m, fraction_of_optimum=1.0, processes=1)
fva.to_csv("fva_anaerobic.csv")
KEY = ["EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_lac__D_e", "EX_succ_e",
       "EX_co2_e", "PFL", "PDH", "PTAr", "ACKr", "ACALD", "ALCD2x",
       "LDH_D", "PPC", "FRD7", "SUCDi", "NADH16", "CYTBD", "ATPS4r"]
KEY = [k for k in KEY if k in fva.index]
sub = fva.loc[KEY].copy()
sub["width"] = sub["maximum"] - sub["minimum"]
print("--- FVA anaerobic @100% optimum: key reactions ---")
print(sub.to_string())
wide = fva.copy()
wide["width"] = wide["maximum"] - wide["minimum"]
print("--- widest FVA ranges overall (top 10) ---")
print(wide.sort_values("width", ascending=False).head(10).to_string())
