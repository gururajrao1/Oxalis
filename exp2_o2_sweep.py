"""Ugly pass 2: sweep max O2 uptake 0 -> 20, record growth + fermentation fluxes.

Prediction on record (user, before plotting): smooth saturation.
"""
import cobra
import matplotlib.pyplot as plt
import pandas as pd

model = cobra.io.load_model("textbook")
TRACK = ["EX_o2_e", "EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_lac__D_e",
         "EX_succ_e", "EX_co2_e", "EX_glc__D_e"]

rows = []
o2 = 0.0
while o2 <= 20.0 + 1e-9:
    model.reactions.EX_o2_e.lower_bound = -o2
    sol = model.optimize()
    rec = {"o2_max": round(o2, 2), "growth": float(sol.objective_value),
           "status": sol.status}
    for rid in TRACK:
        rec[rid] = float(sol.fluxes[rid])
    rows.append(rec)
    o2 += 0.5

df = pd.DataFrame(rows)
df.to_csv("o2_sweep.csv", index=False)
print(df.to_string(index=False))

fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
a1.plot(df["o2_max"], df["growth"], marker="o", ms=3)
a1.set_ylabel("growth rate (1/h)")
a1.set_title("growth vs max O2 uptake — ugly v1 (predicted: smooth saturation)")
a1.grid(True, alpha=0.3)
for rid, ls in [("EX_ac_e", "-"), ("EX_etoh_e", "--"), ("EX_for_e", ":"),
                ("EX_lac__D_e", "-."), ("EX_succ_e", "-")]:
    a2.plot(df["o2_max"], df[rid], label=rid, linestyle=ls, marker=".", ms=3)
a2.set_xlabel("max O2 uptake (mmol/gDW/h)")
a2.set_ylabel("secretion flux (mmol/gDW/h)")
a2.legend(fontsize=8)
a2.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("o2_sweep.png", dpi=120)
print("saved o2_sweep.png")
