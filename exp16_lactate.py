"""Exp 16: lactate gap — why FBA secretes zero lactate anaerobically.

FBA maximizes growth (ATP). Mixed-acid fermentation (acetate+ethanol+formate)
beats homolactic fermentation on ATP per glucose, so LDH_D stays 0 at the
optimum even though the enzyme exists. This script quantifies the tradeoff:
for each minimum-growth fraction, maximize lactate secretion and record what
growth must be sacrificed. MODEL PREDICTIONS, not regulation.
"""
import cobra
import pandas as pd

m0 = cobra.io.load_model("textbook")
BIO = "Biomass_Ecoli_core"
LDH = "LDH_D"

wt = m0.copy()
wt.reactions.EX_glc__D_e.lower_bound = -10.0
wt.reactions.EX_o2_e.lower_bound = 0.0
wt_g = float(wt.optimize().objective_value)
print(f"anaerobic WT growth: {wt_g:.4f}")

rows = []
for frac in [1.0, 0.9, 0.75, 0.5, 0.25, 0.0]:
    m = m0.copy()
    m.reactions.EX_glc__D_e.lower_bound = -10.0
    m.reactions.EX_o2_e.lower_bound = 0.0
    m.reactions.get_by_id(BIO).lower_bound = frac * wt_g
    m.objective = m.reactions.EX_lac__D_e
    m.objective_direction = "max"
    s = m.optimize()
    f = s.fluxes if s.status == "optimal" else {}
    g = lambda r: float(f.get(r, 0.0))
    rows.append({"min_growth_frac": frac, "growth": g(BIO),
                 "lac": g("EX_lac__D_e"), "ac": g("EX_ac_e"),
                 "etoh": g("EX_etoh_e"), "for": g("EX_for_e"),
                 "succ": g("EX_succ_e"), "ldh": g(LDH), "pfl": g("PFL")})
    print(f"frac>={frac:.2f}: growth={g(BIO):.3f} lac={g('EX_lac__D_e'):.2f} "
          f"ac={g('EX_ac_e'):.2f} etoh={g('EX_etoh_e'):.2f} for={g('EX_for_e'):.2f}")

pd.DataFrame(rows).to_csv("lactate_tradeoff.csv", index=False)
print("saved lactate_tradeoff.csv — takeaway: lactate only appears when growth "
      "is allowed to drop; optimum uses acetate kinase ATP + NADH sink ethanol.")
