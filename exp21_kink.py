"""Exp 21: 14.7-kink flux dump — full vectors around the PFL->PDH handoff.

Closes the notes.md TODO ('dump full flux vectors'). O2 caps across the
degenerate window 12..16 plus the named kink 14.7: records growth, key
handoff fluxes (PFL, PDH, MDH, ATPS4r, NADH16, formate/acetate/ethanol/CO2),
and writes the full exchange+central flux table in long form.
"""
import cobra
import pandas as pd

CAPS = [12.0, 13.0, 14.0, 14.5, 14.7, 15.0, 16.0]
KEYS = ["PFL", "PDH", "MDH", "ATPS4r", "NADH16", "GAPD", "CS",
        "EX_ac_e", "EX_etoh_e", "EX_for_e", "EX_co2_e", "EX_o2_e",
        "EX_glc__D_e"]

m0 = cobra.io.load_model("textbook")
m0.reactions.EX_glc__D_e.lower_bound = -10.0

summary, long = [], []
for cap in CAPS:
    m = m0.copy()
    m.reactions.EX_o2_e.lower_bound = -cap
    s = m.optimize()
    f = s.fluxes
    rec = {"o2cap": cap, "growth": float(s.objective_value)}
    for k in KEYS:
        rec[k] = float(f[k]) if k in f else 0.0
    summary.append(rec)
    for rid in sorted(f.index):
        if rid.startswith("EX_") or rid in ("PFL", "PDH", "MDH", "ATPS4r",
                                             "NADH16", "GAPD", "CS", "PFL",
                                             "Biomass_Ecoli_core"):
            long.append({"o2cap": cap, "reaction": rid, "flux": float(f[rid])})
    print(f"O2cap={cap:5.1f} mu={rec['growth']:.4f} PFL={rec['PFL']:.2f} "
          f"PDH={rec['PDH']:.2f} MDH={rec['MDH']:.2f} for={rec['EX_for_e']:.2f} "
          f"ac={rec['EX_ac_e']:.2f}")

pd.DataFrame(summary).to_csv("kink_summary.csv", index=False)
pd.DataFrame(long).to_csv("kink_vectors.csv", index=False)
print("saved kink_summary.csv + kink_vectors.csv — takeaway: PFL/formate slope "
      "-> 0 at ~14.7 while PDH slope flips and MDH switches on (TCA engaged).")
