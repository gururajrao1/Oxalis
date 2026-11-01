"""Ugly pass 7: pFBA + loopless hygiene. Kill the FRD7/SUCDi cycle, check whether
pFBA resolves the degenerate O2 12-14.7 formate path (FBA said out-at-12 on one
solver path, out-at-14.7 on another)."""
import cobra
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from cobra.flux_analysis import pfba

KEY = ["EX_ac_e", "EX_etoh_e", "EX_for_e", "PFL", "PDH", "FRD7", "SUCDi",
       "ATPS4r", "NADH16", "THD2", "CYTBD"]


def show(mid, o2, tag):
    m = (cobra.io.load_model("textbook") if mid == "core"
         else cobra.io.load_json_model("iML1515.json"))
    m.reactions.EX_o2_e.lower_bound = -o2
    fba = m.optimize()
    p = pfba(m)  # fixes growth at optimum; objective_value is flux-sum, NOT mu
    print(f"--- {tag}: mu={fba.objective_value:.4f} (pFBA holds growth at optimum) ---")
    for k in KEY:
        if k in fba.fluxes:
            print(f"  {k:10s} FBA={fba.fluxes[k]:+10.4f} pFBA={p.fluxes[k]:+10.4f}")


show("core", 1000.0, "core aerobic")
show("core", 0.0, "core anaerobic")
show("1515", 0.0, "1515 anaerobic")

# loopless on core anaerobic
try:
    from cobra.flux_analysis.loopless import add_loopless
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = 0
    add_loopless(m)
    s = m.optimize()
    print(f"--- core anaerobic LOOPLESS mu={s.objective_value:.4f} "
          f"FRD7={s.fluxes['FRD7']:.4f} SUCDi={s.fluxes['SUCDi']:.4f} ---")
except Exception as e:
    print(f"loopless failed (honest report): {type(e).__name__}: {e}")

# pFBA sweep on core: which degenerate path does parsimony pick?
rows = []
o2 = 0.0
while o2 <= 25.0 + 1e-9:
    m = cobra.io.load_model("textbook")
    m.reactions.EX_o2_e.lower_bound = -o2
    g = m.slim_optimize()
    p = pfba(m)
    rows.append({"o2_max": round(o2, 1), "growth": float(g),
                 "ac": float(p.fluxes["EX_ac_e"]), "etoh": float(p.fluxes["EX_etoh_e"]),
                 "for": float(p.fluxes["EX_for_e"])})
    o2 += 1.0
df = pd.DataFrame(rows)
df.to_csv("pfba_sweep.csv", index=False)
fba = pd.read_csv("o2_sweep25.csv")
fig, (a1, a2) = plt.subplots(2, 1, figsize=(7, 7), sharex=True)
a1.plot(df["o2_max"], df["growth"], "o-", ms=3, label="pFBA")
a1.plot(fba["o2_max"], fba["growth"], "--", label="FBA")
a1.set_ylabel("growth (1/h)"); a1.legend(fontsize=8); a1.grid(True, alpha=0.3)
a1.set_title("pFBA vs FBA across O2 (core)")
a2.plot(df["o2_max"], df["for"], "o-", ms=3, label="formate pFBA")
a2.plot(fba["o2_max"], fba["for"], "--", label="formate FBA")
a2.plot(df["o2_max"], df["ac"], "s-", ms=3, label="acetate pFBA")
a2.plot(fba["o2_max"], fba["ac"], "--", label="acetate FBA")
a2.set_xlabel("max O2 uptake"); a2.set_ylabel("secretion flux")
a2.legend(fontsize=8); a2.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("pfba_compare.png", dpi=120)
print("saved pfba_compare.png")
print(df.to_string(index=False))
